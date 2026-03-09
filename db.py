"""Conexão PostgreSQL e inicialização do schema."""
import os
from pathlib import Path

# Garantir .env carregado antes do config (mesmo quando db é importado cedo)
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path, override=True)

from config import DATABASE_URL

def get_connection():
    """Retorna uma conexão com o PostgreSQL. Fechar após uso (conn.close())."""
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    except Exception as e:
        import os
        if os.environ.get("FLASK_DEBUG") or os.environ.get("DEBUG"):
            import traceback
            traceback.print_exc()
        return None


def init_schema(conn):
    """Cria as tabelas se não existirem."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            cur = conn.cursor()
            cur.execute(f.read())
            conn.commit()
            cur.close()
