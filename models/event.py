"""Modelo para eventos de engajamento (page_view, click)."""

from datetime import datetime


def event_document(event_type: str, page: str = "", element: str = "", session_id: str = "") -> dict:
    return {
        "type": event_type,
        "page": page,
        "element": element,
        "session_id": session_id,
        "created_at": datetime.utcnow().isoformat(),
    }
