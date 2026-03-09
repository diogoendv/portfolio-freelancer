"""Modelo para leads/contatos do formulário."""

from datetime import datetime


def lead_document(name: str, email: str, service: str, message: str) -> dict:
    """Retorna documento pronto para inserção no MongoDB."""
    return {
        "name": name,
        "email": email,
        "service": service,
        "message": message,
        "created_at": datetime.utcnow().isoformat(),
    }
