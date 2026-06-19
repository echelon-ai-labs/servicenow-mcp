"""Small shared helpers for ServiceNow REST calls."""

import requests


def error_detail(exc: requests.RequestException) -> str:
    """Extract a useful message from a ServiceNow error response, if present.

    ServiceNow returns errors as ``{"error": {"message": ..., "detail": ...}}``.
    ``str(exception)`` only shows the HTTP status line (e.g. "403 Client Error:
    Forbidden"), hiding the real reason — e.g. "Operation against file ... was
    aborted by Business Rule 'Change Model: Check State Transition'". Surfacing
    that detail is what makes failed operations debuggable.
    """
    resp = getattr(exc, "response", None)
    if resp is None:
        return str(exc)
    detail = ""
    try:
        err = resp.json().get("error", {})
        detail = " - ".join(str(p).strip() for p in (err.get("message"), err.get("detail")) if p)
    except ValueError:
        detail = (resp.text or "").strip()[:300]

    message = f"HTTP {resp.status_code}"
    if detail:
        message += f": {detail}"
    if resp.status_code == 401 or (resp.status_code == 403 and not detail):
        message += " (check credentials and that the account has the required role and ACLs)"
    return message
