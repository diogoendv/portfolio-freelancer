"""Configurações da aplicação."""

import os
from pathlib import Path

# Carrega variáveis do arquivo .env (na raiz do projeto). override=True para que .env prevaleça sobre variáveis de ambiente já definidas.
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path, override=True)

# PostgreSQL — ex: postgresql://usuario:senha@localhost:5432/portfolio_db
DATABASE_URL = (os.environ.get("DATABASE_URL") or "postgresql://localhost:5432/portfolio_db").strip()
CHAT_SESSION_TIMEOUT_SECONDS = 3600  # 1 hora sem atividade = conversa encerrada

# Senha do admin — somente a definida no .env (sem fallback)
ADMIN_PASSWORD = (os.environ.get("ADMIN_PASSWORD") or "").strip()
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

# Notificação quando chega mensagem no chat (pode usar mais de uma opção)
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")  # e-mail que recebe o aviso (usado no Gmail e na Resend)

# Opção 1 — Gmail (grátis): use SMTP do Gmail com Senha de app
SMTP_HOST = os.environ.get("SMTP_HOST", "")  # ex: smtp.gmail.com
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")  # ex: seu@gmail.com
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")  # Senha de app do Google (16 caracteres)
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "1").strip().lower() in ("1", "true", "yes")

# Opção 2 — Webhook: POST para URL (ex.: Zapier). Defina WEBHOOK_URL.
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").strip()
# Opção 3 — Resend.com (API): RESEND_API_KEY + ADMIN_EMAIL
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
