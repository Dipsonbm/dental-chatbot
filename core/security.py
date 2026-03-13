"""
core/security.py
Widget key validation and request origin checking.
"""

from fastapi import HTTPException, Request
from core.clinic_store import get_clinic_by_widget_key


def resolve_clinic(widget_key: str) -> dict:
    """
    Look up clinic by widget_key.
    Raises 403 if not found or inactive.
    """
    clinic = get_clinic_by_widget_key(widget_key)
    if not clinic:
        raise HTTPException(status_code=403, detail="Invalid or inactive widget key.")
    return clinic


def check_origin(request: Request, clinic: dict) -> None:
    """
    Validate that the request Origin header matches the clinic's allowed_domain.
    Raises 403 if the origin doesn't match.

    Allows requests with no Origin header only in local development
    (localhost or 127.0.0.1).
    """
    origin = request.headers.get("origin", "")
    allowed = clinic.get("allowed_domain", "").lower().strip()

    # Strip protocol from origin for comparison
    origin_host = (
        origin.replace("https://", "").replace("http://", "").split("/")[0].lower()
    )

    # Allow localhost and file:// pages (origin="null") for local testing
    if origin_host in ("", "null", "localhost", "127.0.0.1") or origin_host.startswith("localhost:"):
        return

    if not allowed:
        raise HTTPException(status_code=403, detail="Clinic has no allowed domain configured.")

    # Strip www. for a looser match
    origin_bare = origin_host.removeprefix("www.")
    allowed_bare = allowed.removeprefix("www.")

    if origin_bare != allowed_bare:
        raise HTTPException(
            status_code=403,
            detail=f"Request origin '{origin}' is not allowed for this widget.",
        )
