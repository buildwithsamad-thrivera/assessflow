import json
import frappe
from frappe.utils import now_datetime
from assessflow.services import session as guest_session
from assessflow.services.attempt import AttemptError


def _get_display_answer(question_name, payload):
    if not payload: return ""
    try:
        q = frappe.get_doc("Question Bank", question_name)
        if q.question_type in ("Single Choice", "True/False"):
            for opt in (q.options or []):
                if opt.name == payload:
                    return opt.option_text
            return str(payload)
        elif q.question_type == "Multiple Select":
            if not isinstance(payload, list): return str(payload)
            texts = []
            for opt in (q.options or []):
                if opt.name in payload:
                    texts.append(opt.option_text)
            return ", ".join(texts)
        else:
            return str(payload)
    except Exception:
        return str(payload)

def save_answer(question_name, payload, session_token=None, marked_for_review=None):
    attempt = guest_session.require_session(session_token=session_token)
    if attempt.status != "In Progress" or now_datetime() > attempt.deadline: raise AttemptError("Attempt closed.")
    
    if not frappe.db.exists("Assessment Question", {"parent": attempt.assessment, "question": question_name}): frappe.throw("Not authorized.", frappe.PermissionError)

    encoded = json.dumps(payload, separators=(",", ":"), default=str)
    if len(encoded) > 512 * 1024: raise AttemptError("Payload too large (512 KB max).")

    now = now_datetime()
    existing = frappe.db.get_value("Candidate Answer", {"attempt": attempt.name, "question": question_name}, ["name", "submitted_payload"], as_dict=True)
    if existing and existing.submitted_payload: raise AttemptError("Already submitted.")

    display_val = _get_display_answer(question_name, payload)
    values = {"answer_payload": encoded, "saved_at": now, "display_answer": display_val}
    if marked_for_review is not None: values["marked_for_review"] = 1 if marked_for_review else 0

    if existing: frappe.db.set_value("Candidate Answer", existing.name, values)
    else:
        doc = {"doctype":"Candidate Answer","attempt":attempt.name,"question":question_name,**values}
        frappe.get_doc(doc).insert(ignore_permissions=True)

    frappe.db.set_value("Candidate Attempt", attempt.name, "last_activity_at", now, update_modified=False)
    return {"saved": True}

def toggle_mark_for_review(question_name, marked, session_token=None):
    attempt = guest_session.require_session(session_token=session_token)
    if not frappe.db.exists("Assessment Question", {"parent": attempt.assessment, "question": question_name}): frappe.throw("Not authorized.", frappe.PermissionError)
    existing = frappe.db.get_value("Candidate Answer", {"attempt": attempt.name, "question": question_name}, "name")
    if existing: frappe.db.set_value("Candidate Answer", existing, "marked_for_review", 1 if marked else 0)
    else: frappe.get_doc({"doctype":"Candidate Answer","attempt":attempt.name,"question":question_name,"marked_for_review":1 if marked else 0}).insert(ignore_permissions=True)
    return {"ok": True}

def bump_run_count(attempt_name, question_name):
    existing = frappe.db.get_value("Candidate Answer", {"attempt": attempt_name, "question": question_name}, ["name", "run_count"], as_dict=True)
    if existing:
        frappe.db.set_value("Candidate Answer", existing.name, "run_count", int(existing.run_count or 0) + 1)
    else: frappe.get_doc({"doctype":"Candidate Answer","attempt":attempt_name,"question":question_name,"run_count":1}).insert(ignore_permissions=True)

def get_run_count(attempt_name, question_name):
    return int(frappe.db.get_value("Candidate Answer", {"attempt": attempt_name, "question": question_name}, "run_count") or 0)

def freeze_answers(attempt_name):
    for a in frappe.get_all("Candidate Answer", filters={"attempt": attempt_name, "submitted_payload": ["is", "not set"]}, fields=["name", "answer_payload"]):
        frappe.db.set_value("Candidate Answer", a.name, "submitted_payload", a.answer_payload, update_modified=False)
