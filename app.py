"""
Portfólio e vendas — Freelancer.
Backend Flask com PostgreSQL, chat em tempo real e painel admin.
"""

import json
import os
import re
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Garantir que o .env da pasta do projeto seja carregado antes do config
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path, override=True)

from flask import Flask, g, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_socketio import SocketIO, emit, join_room

from config import (
    DATABASE_URL,
    CHAT_SESSION_TIMEOUT_SECONDS,
    ADMIN_PASSWORD, SECRET_KEY,
    ADMIN_EMAIL, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_TLS,
    WEBHOOK_URL, RESEND_API_KEY,
)
from db import get_connection, init_schema

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Em debug, confirma ao iniciar se a conexão com o banco funciona
if __name__ == "__main__" or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    try:
        _conn = get_connection()
        if _conn:
            init_schema(_conn)
            _conn.close()
            print("[PostgreSQL] Conexão OK")
        else:
            print("[PostgreSQL] Falha na conexão")
    except Exception as _e:
        print("[PostgreSQL] Falha:", type(_e).__name__, str(_e)[:120])

def get_db():
    """Retorna conexão PostgreSQL (guardada em g). Fechada automaticamente no teardown."""
    if "db" not in g:
        conn = get_connection()
        if conn:
            init_schema(conn)
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass


def is_valid_email(email: str) -> bool:
    if not email or len(email) > 254:
        return False
    pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    if not pattern.match(email):
        return False
    local, domain = email.rsplit("@", 1)
    return "." in domain and len(domain.split(".")[-1]) >= 2


def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            if request.is_json or request.path.startswith("/api/admin"):
                return jsonify({"error": "Não autorizado"}), 401
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapped


# ---- Arquivos estáticos (logo e favicon) ----
@app.route("/favicon.svg")
def favicon_svg():
    return send_from_directory(app.static_folder, "favicon.svg", mimetype="image/svg+xml")


@app.route("/favicon.png")
def favicon_png():
    return send_from_directory(app.static_folder, "favicon.png", mimetype="image/png")


@app.route("/logo-wordmark.png")
def logo_wordmark():
    return send_from_directory(app.static_folder, "logo-wordmark.png", mimetype="image/png")


# ---- Rotas públicas ----
@app.route("/")
def home():
    return render_template("single.html")


@app.route("/ideias")
def ideias():
    return redirect(url_for("home") + "#ideias")


@app.route("/servicos")
def servicos():
    return redirect(url_for("home") + "#servicos")


@app.route("/contato")
def contato():
    return redirect(url_for("home") + "#contato")


@app.route("/api/contact", methods=["POST"])
def contact():
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        service = (data.get("service") or "").strip()
        message = (data.get("message") or "").strip()

        if not name or len(name) < 2:
            return jsonify({"success": False, "error": "Nome inválido ou muito curto."}), 400
        if not is_valid_email(email):
            return jsonify({"success": False, "error": "E-mail inválido. Insira um e-mail válido."}), 400
        if not message or len(message) < 10:
            return jsonify({"success": False, "error": "Mensagem deve ter pelo menos 10 caracteres."}), 400

        conn = get_db()
        if not conn:
            return jsonify({"success": False, "error": "Serviço temporariamente indisponível. Tente mais tarde."}), 503

        cur = conn.cursor()
        cur.execute(
            "INSERT INTO leads (name, email, service, message, created_at) VALUES (%s, %s, %s, %s, NOW())",
            (name, email, service, message),
        )
        conn.commit()
        cur.close()
        return jsonify({"success": True, "message": "Mensagem enviada com sucesso!"})
    except Exception as e:
        if app.debug:
            import traceback
            traceback.print_exc()
        return jsonify({"success": False, "error": "Erro ao salvar. Tente novamente."}), 500


def _client_ip():
    """IP do cliente (considera X-Forwarded-For em proxy)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return (request.remote_addr or "")[:45]


@app.route("/api/track", methods=["POST"])
def track():
    """Registra evento de engajamento (page_view ou click) para relatórios."""
    data = request.get_json() or {}
    event_type = (data.get("type") or "page_view").strip()
    if event_type not in ("page_view", "click"):
        event_type = "page_view"
    page = (data.get("page") or request.referrer or "/")[:500]
    element = (data.get("element") or "")[:200]
    session_id = (data.get("session_id") or "")[:100]
    ip = _client_ip()

    conn = get_db()
    if conn:
        try:
            cur = conn.cursor()
            try:
                cur.execute(
                    "INSERT INTO events (type, page, element, session_id, ip, created_at) VALUES (%s, %s, %s, %s, %s, NOW())",
                    (event_type, page, element, session_id, ip or None),
                )
            except Exception:
                cur.execute(
                    "INSERT INTO events (type, page, element, session_id, created_at) VALUES (%s, %s, %s, %s, NOW())",
                    (event_type, page, element, session_id),
                )
            conn.commit()
            cur.close()
        except Exception:
            pass
    return jsonify({"ok": True})


# Ideias padrão (slug usado na URL da página de exemplo)
DEFAULT_IDEAS = [
    {"title": "Landing SaaS", "category": "SaaS", "description": "Landing page moderna para produto SaaS.", "slug": "landing-saas"},
    {"title": "E-commerce Minimalista", "category": "E-commerce", "description": "Loja virtual com foco em experiência e conversão.", "slug": "ecommerce-minimalista"},
    {"title": "Portfólio Criativo", "category": "Portfólio", "description": "Site de portfólio com animações e grid assimétrico.", "slug": "portfolio-criativo"},
    {"title": "Blog Pessoal", "category": "Blog", "description": "Blog limpo com lista de posts e página de artigo.", "slug": "blog-pessoal"},
    {"title": "Site Institucional", "category": "Corporativo", "description": "Página de empresa com sobre, serviços e contato.", "slug": "site-institucional"},
    {"title": "Landing de Serviço", "category": "SaaS", "description": "Uma página para divulgar um serviço e captar leads.", "slug": "landing-servico"},
    {"title": "Cardápio Digital", "category": "E-commerce", "description": "Cardápio online para restaurante ou delivery.", "slug": "cardapio-digital"},
    {"title": "Página de Evento", "category": "Corporativo", "description": "Site simples para divulgar um evento e inscrições.", "slug": "pagina-evento"},
    {"title": "Portfólio Fotográfico", "category": "Portfólio", "description": "Galeria em grid para fotógrafo ou artista.", "slug": "portfolio-fotografico"},
    {"title": "Página de Captura", "category": "SaaS", "description": "Landing focada em e-mail e CTA único.", "slug": "pagina-captura"},
]
IDEAS_BY_SLUG = {d["slug"]: d for d in DEFAULT_IDEAS}

# Template de exemplo por slug (cada ideia tem uma página de prévia desenvolvida)
EXEMPLO_TEMPLATES = {
    "landing-saas": "exemplos/landing_saas.html",
    "ecommerce-minimalista": "exemplos/ecommerce_minimalista.html",
    "portfolio-criativo": "exemplos/portfolio_criativo.html",
    "blog-pessoal": "exemplos/blog_pessoal.html",
    "site-institucional": "exemplos/site_institucional.html",
    "landing-servico": "exemplos/landing_servico.html",
    "cardapio-digital": "exemplos/cardapio_digital.html",
    "pagina-evento": "exemplos/pagina_evento.html",
    "portfolio-fotografico": "exemplos/portfolio_fotografico.html",
    "pagina-captura": "exemplos/pagina_captura.html",
}


@app.route("/api/ideas")
def api_ideas():
    conn = get_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT title, category, description FROM ideas LIMIT 50")
            rows = cur.fetchall()
            cur.close()
            if rows:
                return jsonify([{"title": r[0], "category": r[1], "description": r[2]} for r in rows])
        except Exception:
            pass
    default_ideas = [dict(d) for d in DEFAULT_IDEAS]
    for idea in default_ideas:
        idea["url"] = url_for("exemplo_ideia", slug=idea["slug"])
    return jsonify(default_ideas)


@app.route("/exemplo/<slug>")
def exemplo_ideia(slug):
    """Página de exemplo para uma ideia (conceito de site) — prévia desenvolvida para o cliente."""
    idea = IDEAS_BY_SLUG.get(slug)
    if not idea:
        return redirect(url_for("home") + "#ideias")
    template = EXEMPLO_TEMPLATES.get(slug)
    if template:
        return render_template(template, idea=idea)
    return render_template("exemplo_ideia.html", idea=idea)


# ---- Admin: login e painel ----
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        data = request.get_json() or request.form
        password = (data.get("password") or "").strip()
        if password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            if request.is_json:
                return jsonify({"success": True})
            return redirect(url_for("admin_dashboard"))
        if request.is_json:
            return jsonify({"success": False, "error": "Senha incorreta"}), 401
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template("admin.html")


@app.route("/api/admin/leads")
@admin_required
def api_admin_leads():
    conn = get_db()
    if not conn:
        return jsonify([])
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, service, message, created_at FROM leads ORDER BY created_at DESC LIMIT 500")
        rows = cur.fetchall()
        cur.close()
        return jsonify([
            {"id": r[0], "name": r[1], "email": r[2], "service": r[3], "message": r[4], "created_at": r[5].isoformat() if r[5] else None}
            for r in rows
        ])
    except Exception:
        return jsonify([])


def _geo_for_ip(ip):
    """Retorna cidade, país para um IP (ip-api.com, sem chave). Ignora IPs privados."""
    if not ip or ip.startswith("127.") or ip == "::1" or ip.startswith("192.168.") or ip.startswith("10."):
        return None
    try:
        req = Request("http://ip-api.com/json/" + ip, headers={"User-Agent": "PortfolioAdmin/1.0"})
        with urlopen(req, timeout=2) as r:
            data = json.loads(r.read().decode())
            if data.get("status") == "success":
                city = data.get("city") or ""
                country = data.get("country") or ""
                return ", ".join(filter(None, [city, country])) or None
    except (URLError, HTTPError, ValueError, OSError):
        pass
    return None


@app.route("/api/admin/stats")
@admin_required
def api_admin_stats():
    conn = get_db()
    if not conn:
        return jsonify({
            "page_views": 0, "clicks": 0, "leads_count": 0,
            "chart": [], "visitors": []
        })
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM events WHERE type = %s", ("page_view",))
        page_views = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM events WHERE type = %s", ("click",))
        clicks = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM leads")
        leads_count = cur.fetchone()[0]

        # Últimos 7 dias: page_views, clicks e leads por dia (para gráficos)
        chart = []
        for i in range(6, -1, -1):
            d = (datetime.utcnow() - timedelta(days=i)).date()
            cur.execute(
                "SELECT COUNT(*) FROM events WHERE type = %s AND created_at::date = %s",
                ("page_view", d),
            )
            pv = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM events WHERE type = %s AND created_at::date = %s",
                ("click", d),
            )
            cl = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM leads WHERE created_at::date = %s",
                (d,),
            )
            leads = cur.fetchone()[0]
            chart.append({"date": d.isoformat(), "page_views": pv, "clicks": cl, "leads": leads})

        # Visitantes por IP (últimos eventos com IP), com localização
        visitors = []
        try:
            cur.execute(
                """SELECT ip, MAX(created_at) AS last_seen
                   FROM events WHERE ip IS NOT NULL AND ip != '' GROUP BY ip ORDER BY last_seen DESC LIMIT 25"""
            )
            rows = cur.fetchall()
            for ip, last_seen in rows:
                location = _geo_for_ip(ip)
                visitors.append({
                    "ip": ip,
                    "location": location or "—",
                    "last_seen": last_seen.isoformat()[:19] if last_seen else None,
                })
        except Exception:
            pass

        cur.close()
        return jsonify({
            "page_views": page_views,
            "clicks": clicks,
            "leads_count": leads_count,
            "chart": chart,
            "visitors": visitors,
        })
    except Exception:
        return jsonify({
            "page_views": 0, "clicks": 0, "leads_count": 0,
            "chart": [], "visitors": []
        })


@app.route("/api/admin/conversations")
@admin_required
def api_admin_conversations():
    conn = get_db()
    if not conn:
        return jsonify([])
    try:
        cur = conn.cursor()
        cur.execute("SELECT session_id, internal_code, created_at, updated_at FROM chat_sessions ORDER BY updated_at DESC NULLS LAST LIMIT 100")
        sessions = cur.fetchall()
        out = []
        for s in sessions:
            sid = s[0] or ""
            cur.execute("SELECT COUNT(*) FROM chat_messages WHERE session_id = %s", (sid,))
            count = cur.fetchone()[0]
            out.append({
                "session_id": sid,
                "internal_code": s[1] or (sid[:12] if sid else ""),
                "created_at": s[2].isoformat() if s[2] else None,
                "updated_at": s[3].isoformat() if s[3] else None,
                "message_count": count,
            })
        cur.close()
        return jsonify(out)
    except Exception:
        return jsonify([])


@app.route("/api/admin/messages/<session_id>")
@admin_required
def api_admin_messages(session_id):
    conn = get_db()
    if not conn:
        return jsonify([])
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, session_id, sender, message, created_at FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC", (session_id,))
        rows = cur.fetchall()
        cur.close()
        return jsonify([
            {"id": r[0], "session_id": r[1], "sender": r[2], "message": r[3], "created_at": r[4].isoformat() if r[4] else None}
            for r in rows
        ])
    except Exception:
        return jsonify([])


@app.route("/api/admin/chat-export")
@admin_required
def api_admin_chat_export():
    """Exporta todas as conversas para relatório (código da conversa + mensagens)."""
    conn = get_db()
    if not conn:
        return jsonify([])
    try:
        cur = conn.cursor()
        cur.execute("SELECT session_id, internal_code, created_at, updated_at FROM chat_sessions ORDER BY updated_at DESC NULLS LAST")
        sessions = cur.fetchall()
        out = []
        for s in sessions:
            sid = s[0] or ""
            cur.execute("SELECT sender, message, created_at FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC", (sid,))
            msgs = cur.fetchall()
            out.append({
                "session_id": sid,
                "internal_code": s[1] or (sid[:12] if sid else ""),
                "created_at": s[2].isoformat() if s[2] else None,
                "updated_at": s[3].isoformat() if s[3] else None,
                "messages": [{"sender": m[0], "message": m[1], "created_at": m[2].isoformat() if m[2] else None} for m in msgs],
            })
        cur.close()
        return jsonify(out)
    except Exception:
        return jsonify([])


@app.route("/api/admin/chat-archive/<session_id>", methods=["POST"])
@admin_required
def api_admin_chat_archive(session_id):
    """Finaliza manualmente uma conversa: arquiva em relatórios e remove das ativas."""
    session_id = (session_id or "")[:64]
    if not session_id:
        return jsonify({"success": False, "error": "Session inválida"}), 400
    conn = get_db()
    if not conn:
        return jsonify({"success": False, "error": "Banco indisponível"}), 503
    try:
        archive_conversation(conn, session_id)
        return jsonify({"success": True, "message": "Conversa finalizada e enviada para relatórios."})
    except Exception:
        return jsonify({"success": False, "error": "Erro ao finalizar"}), 500


def _get_internal_code(conn, session_id):
    if not conn or not session_id:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT internal_code FROM chat_sessions WHERE session_id = %s", (session_id,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    except Exception:
        return None


@app.route("/api/admin/chat-archived")
@admin_required
def api_admin_chat_archived():
    """Lista conversas finalizadas (arquivadas) para relatórios e aferição futura."""
    conn = get_db()
    if not conn:
        return jsonify([])
    try:
        cur = conn.cursor()
        cur.execute("SELECT internal_code, session_id, created_at, updated_at, closed_at, message_count, messages FROM chat_archived ORDER BY closed_at DESC NULLS LAST LIMIT 200")
        rows = cur.fetchall()
        cur.close()
        out = []
        for r in rows:
            msgs = r[6] if r[6] is not None else []
            if isinstance(msgs, str):
                try:
                    msgs = json.loads(msgs)
                except Exception:
                    msgs = []
            out.append({
                "internal_code": r[0],
                "session_id": r[1],
                "created_at": r[2].isoformat() if r[2] else None,
                "closed_at": r[4].isoformat() if r[4] else None,
                "message_count": r[5] or 0,
                "messages": msgs,
            })
        return jsonify(out)
    except Exception:
        return jsonify([])


# ---- SocketIO: chat em tempo real ----
def _parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def _generate_internal_code():
    return "CONV-" + datetime.utcnow().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()


def ensure_chat_session(conn, session_id):
    if not conn:
        return
    now = datetime.utcnow()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_sessions (session_id, updated_at) VALUES (%s, %s) ON CONFLICT (session_id) DO UPDATE SET updated_at = EXCLUDED.updated_at",
            (session_id, now),
        )
        cur.execute("SELECT created_at, internal_code FROM chat_sessions WHERE session_id = %s", (session_id,))
        row = cur.fetchone()
        if row and row[0] is None:
            cur.execute(
                "UPDATE chat_sessions SET created_at = %s, internal_code = %s WHERE session_id = %s AND created_at IS NULL",
                (now, _generate_internal_code(), session_id),
            )
        conn.commit()
        cur.close()
    except Exception:
        conn.rollback()


def archive_conversation(conn, session_id):
    """Copia a conversa para relatórios (chat_archived) e remove da sessão ativa."""
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("SELECT internal_code, created_at, updated_at FROM chat_sessions WHERE session_id = %s", (session_id,))
        doc = cur.fetchone()
        if not doc:
            cur.close()
            return
        internal_code = doc[0] or ("CONV-" + session_id[:8])
        cur.execute("SELECT sender, message, created_at FROM chat_messages WHERE session_id = %s ORDER BY created_at ASC", (session_id,))
        msgs = cur.fetchall()
        messages_json = json.dumps([
            {"sender": m[0], "message": m[1], "created_at": m[2].isoformat() if m[2] else None}
            for m in msgs
        ])
        cur.execute(
            "INSERT INTO chat_archived (internal_code, session_id, created_at, updated_at, closed_at, message_count, messages) VALUES (%s, %s, %s, %s, NOW(), %s, %s::jsonb)",
            (internal_code, session_id, doc[1], doc[2], len(msgs), messages_json),
        )
        cur.execute("DELETE FROM chat_messages WHERE session_id = %s", (session_id,))
        cur.execute("DELETE FROM chat_sessions WHERE session_id = %s", (session_id,))
        conn.commit()
        cur.close()
    except Exception:
        conn.rollback()


@socketio.on("connect")
def on_connect():
    pass


@socketio.on("visitor_join")
def on_visitor_join(data):
    conn = get_db()
    own_conn = False
    if not conn:
        conn = get_connection()
        own_conn = True
    client_sid = (data.get("session_id") or "").strip()[:64]
    sid = client_sid
    if conn and client_sid:
        try:
            cur = conn.cursor()
            cur.execute("SELECT updated_at FROM chat_sessions WHERE session_id = %s", (client_sid,))
            row = cur.fetchone()
            cur.close()
            if row and row[0]:
                updated_dt = row[0]
                now_utc = datetime.utcnow()
                if updated_dt.tzinfo:
                    from datetime import timezone
                    updated_dt = updated_dt.astimezone(timezone.utc).replace(tzinfo=None)
                if (now_utc - updated_dt).total_seconds() >= CHAT_SESSION_TIMEOUT_SECONDS:
                    archive_conversation(conn, client_sid)
                    sid = str(uuid.uuid4())
        except Exception:
            pass
    if not sid:
        sid = str(uuid.uuid4())
    room = f"visitor_{sid}"
    join_room(room)
    if conn:
        ensure_chat_session(conn, sid)
    if own_conn and conn:
        try:
            conn.close()
        except Exception:
            pass
    emit("visitor_joined", {"session_id": sid})
    emit("session_id", {"session_id": sid})


def notify_admin_first_message_only(session_id: str, first_message: str, internal_code: str = None):
    """Envia apenas 1 e-mail: na primeira mensagem da conversa, com identificação interna e aviso."""
    import json
    from urllib.request import Request, urlopen

    ident = (internal_code or session_id)[:80]
    text_body = (
        f"Código interno da conversa: {ident}\n\n"
        "Você tem uma mensagem a ser respondida.\n\n"
        f"Primeira mensagem do cliente: {first_message[:500]}\n\n"
        "Acesse o painel admin para responder."
    )

    # Gmail (SMTP)
    if SMTP_HOST and SMTP_USER and SMTP_PASSWORD and ADMIN_EMAIL:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            msg = MIMEMultipart()
            msg["Subject"] = "[Portfólio] Você tem uma mensagem a ser respondida"
            msg["From"] = SMTP_USER
            msg["To"] = ADMIN_EMAIL
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
                if SMTP_USE_TLS:
                    s.starttls()
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.sendmail(SMTP_USER, ADMIN_EMAIL, msg.as_string())
        except Exception:
            pass

    payload = {
        "event": "chat_first_message",
        "session_id": session_id,
        "message": first_message,
        "text": text_body,
        "value1": "Mensagem a ser respondida",
        "value2": first_message[:200],
        "value3": internal_code or session_id,
    }

    if WEBHOOK_URL:
        try:
            req = Request(
                WEBHOOK_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urlopen(req, timeout=10)
        except Exception:
            pass

    if RESEND_API_KEY and ADMIN_EMAIL:
        try:
            body = {
                "from": "Chat Portfólio <onboarding@resend.dev>",
                "to": [ADMIN_EMAIL],
                "subject": "[Portfólio] Você tem uma mensagem a ser respondida",
                "text": text_body,
            }
            req = Request(
                "https://api.resend.com/emails",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                },
                method="POST",
            )
            urlopen(req, timeout=10)
        except Exception:
            pass


@socketio.on("visitor_message")
def on_visitor_message(data):
    session_id = (data.get("session_id") or "")[:64]
    text = (data.get("message") or "").strip()[:2000]
    if not session_id or not text:
        return
    conn = get_db()
    own_conn = False
    if not conn:
        conn = get_connection()
        own_conn = True
    now = datetime.utcnow()
    now_iso = now.isoformat()
    is_first_message = False
    internal_code = _get_internal_code(conn, session_id)
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO chat_messages (session_id, sender, message, created_at) VALUES (%s, %s, %s, %s)",
                (session_id, "visitor", text, now),
            )
            cur.execute("UPDATE chat_sessions SET updated_at = %s WHERE session_id = %s", (now, session_id))
            cur.execute("SELECT COUNT(*) FROM chat_messages WHERE session_id = %s AND sender = %s", (session_id, "visitor"))
            is_first_message = cur.fetchone()[0] == 1
            conn.commit()
            ensure_chat_session(conn, session_id)
            cur.close()
        except Exception:
            conn.rollback()
    if is_first_message:
        notify_admin_first_message_only(session_id, text, internal_code=internal_code)
    if not internal_code and conn:
        internal_code = _get_internal_code(conn, session_id)
    if own_conn and conn:
        try:
            conn.close()
        except Exception:
            pass
    payload = {"sender": "visitor", "message": text, "created_at": now_iso, "session_id": session_id, "internal_code": internal_code}
    emit("new_message", payload, room="admin_broadcast")


@socketio.on("admin_join")
def on_admin_join(data):
    join_room("admin_broadcast")


@socketio.on("admin_join_session")
def on_admin_join_session(data):
    session_id = (data.get("session_id") or "")[:64]
    if session_id:
        join_room(f"session_{session_id}")


@socketio.on("admin_message")
def on_admin_message(data):
    session_id = (data.get("session_id") or "")[:64]
    text = (data.get("message") or "").strip()[:2000]
    if not session_id or not text:
        return
    conn = get_db()
    own_conn = False
    if not conn:
        conn = get_connection()
        own_conn = True
    if conn:
        try:
            now = datetime.utcnow()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO chat_messages (session_id, sender, message, created_at) VALUES (%s, %s, %s, %s)",
                (session_id, "admin", text, now),
            )
            cur.execute("UPDATE chat_sessions SET updated_at = %s WHERE session_id = %s", (now, session_id))
            conn.commit()
            cur.close()
        except Exception:
            conn.rollback()
    if own_conn and conn:
        try:
            conn.close()
        except Exception:
            pass
    emit("new_message", {"sender": "admin", "message": text, "created_at": datetime.utcnow().isoformat()}, room=f"visitor_{session_id}")


if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000)
