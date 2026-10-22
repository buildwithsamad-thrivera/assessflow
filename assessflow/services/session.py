import secrets
from datetime import datetime, timedelta, timezone
import frappe

COOKIE_NAME = "af_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7

def new_nonce(): return secrets.token_urlsafe(24)
def make_session_token(attempt_id, nonce): return f"{attempt_id}:{nonce}"
def _jar(): return frappe.local.cookie_manager.cookies if hasattr(frappe.local.cookie_manager, "cookies") else frappe.request.cookies
def _is_https():
    req = getattr(frappe.local, "request", None)
    return bool(req and getattr(req, "is_secure", False))

def set_session_cookie(attempt_id, nonce):
    try:
        frappe.local.cookie_manager.set_cookie(COOKIE_NAME, make_session_token(attempt_id, nonce),
            expires=datetime.now(timezone.utc) + timedelta(seconds=COOKIE_MAX_AGE), httponly=True, secure=_is_https(), samesite="Lax")
    except Exception: pass

def read_session_cookie():
    raw = _jar().get(COOKIE_NAME)
    if not raw or ":" not in raw: return None
    return tuple(raw.split(":", 1))

def require_session(session_token=None, attempt_id_hint=None):
    parsed = None
    if session_token and isinstance(session_token, str) and ":" in session_token:
        a, n = session_token.split(":", 1)
        if a and n: parsed = (a, n)
    if parsed is None: parsed = read_session_cookie()
    if parsed is None: frappe.throw("Not authorized", frappe.PermissionError)
    
    cookie_attempt, nonce = parsed
    if attempt_id_hint and attempt_id_hint != cookie_attempt: frappe.throw("Not authorized", frappe.PermissionError)
    
    row = frappe.db.get_value("Candidate Attempt", cookie_attempt, ["name","session_nonce","status","deadline","assessment","invitation"], as_dict=True)
    if not row or not secrets.compare_digest(row.session_nonce or "", nonce): frappe.throw("Not authorized", frappe.PermissionError)
    return frappe.get_doc("Candidate Attempt", row.name)
