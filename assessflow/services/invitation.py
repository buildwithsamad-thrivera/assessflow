import hashlib, secrets
import frappe
from frappe.utils import now_datetime

class InvitationError(frappe.ValidationError): pass
def _hash(raw): return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def on_invitation_before_insert(doc, method=None):
    raw = secrets.token_urlsafe(32)
    doc.token = raw; doc.token_hash = _hash(raw); doc.token_hint = raw[-4:]

def on_invitation_validate(doc, method=None):
    if doc.token and not doc.token_hash: doc.token_hash = _hash(doc.token); doc.token_hint = doc.token[-4:]
    if not doc.token_hash: frappe.throw("Invitation must have a token hash.")
    if not doc.is_new() and doc.token: doc.token = ""

def create_invitation(assessment, candidate_name, candidate_email, max_attempts=1):
    a = frappe.get_doc("Assessment", assessment)
    if a.status != "Published": frappe.throw("Assessment must be Published.")
    doc = frappe.get_doc({"doctype":"Assessment Invitation","assessment":assessment,"candidate_name":candidate_name,"candidate_email":candidate_email,"max_attempts":max_attempts})
    doc.insert(); raw = doc.token; doc.token = ""; doc.save()
    return doc, raw

def verify_token(raw):
    if not raw or not isinstance(raw, str) or len(raw) > 128: raise InvitationError("Invalid.")
    inv = frappe.db.get_value("Assessment Invitation", {"token_hash": _hash(raw)}, ["name", "status", "valid_until", "docstatus"], as_dict=True)
    if not inv or inv.status in ("Revoked", "Used", "Expired"): raise InvitationError("Invalid or expired.")
    if inv.docstatus != 1: raise InvitationError("In Draft or cancelled.")
    if inv.valid_until and inv.valid_until < now_datetime(): raise InvitationError("Expired.")
    return frappe.get_doc("Assessment Invitation", inv.name)



def regenerate_token(doc):
    import secrets
    raw = secrets.token_urlsafe(32)
    doc.token = raw
    doc.token_hash = _hash(raw)
    doc.token_hint = raw[-4:]
    doc.flags.ignore_permissions = True
    doc.save()
    return raw
