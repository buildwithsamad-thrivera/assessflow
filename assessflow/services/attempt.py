import json, random
import frappe
from frappe.utils import add_to_date, now_datetime
from assessflow.services import session as guest_session

ALLOWED_TRANSITIONS = {"In Progress": {"Submitted", "Expired", "Cancelled"}, "Submitted": {"Under Review", "Evaluated", "Cancelled"}, "Expired": {"Under Review", "Evaluated", "Cancelled"}, "Under Review": {"Evaluated", "Cancelled"}}
class AttemptError(frappe.ValidationError): pass

def _assert_transition(current, target):
    if current == target: return
    if target not in ALLOWED_TRANSITIONS.get(current, set()): raise AttemptError(f"Illegal transition {current} -> {target}.")

def on_attempt_validate(doc, method=None):
    if doc.is_new():
        if not doc.deadline: frappe.throw("Attempt must be created with a deadline.")
        return
    old = doc.get_doc_before_save()
    if old and old.status != doc.status: _assert_transition(old.status, doc.status)

def on_attempt_updated(doc, method=None):
    if doc.has_value_changed("status") and doc.status in ("Submitted", "Expired"):
        frappe.enqueue("assessflow.services.grading.grade_attempt", queue="long", attempt_name=doc.name, job_id=f"grade::{doc.name}")

def _build_snapshot(assessment):
    sections_map = {sec.section_name: {"name": sec.section_name, "instructions": sec.instructions, "questions": []} for sec in (assessment.sections or [])}
    if not sections_map:
        sections_map["General"] = {"name": "General", "instructions": "", "questions": []}

    aqs = list(assessment.questions or [])
    if assessment.get("randomize_questions"):
        random.shuffle(aqs)

    for aq in aqs:
        q = frappe.get_doc("Question Bank", aq.question)
        q_dict = q.as_dict()
        q_dict["_aq_marks"] = aq.marks
        q_dict["_aq_required"] = aq.required
        
        sec_name = aq.get("section") or "General"
        if sec_name not in sections_map:
            sections_map[sec_name] = {"name": sec_name, "instructions": "", "questions": []}
        sections_map[sec_name]["questions"].append(q_dict)

    # Filter out empty sections
    final_sections = [v for k, v in sections_map.items() if v["questions"]]
    return frappe.as_json({"sections": final_sections})

def start_attempt(invitation):
    inv = frappe.db.get_value("Assessment Invitation", invitation.name, ["name","status","max_attempts","assessment","candidate_email","candidate_name"], as_dict=True, for_update=True)
    if not inv or inv.status in ("Revoked", "Used"): raise AttemptError("Invitation no longer valid.")

    existing = frappe.get_all("Candidate Attempt", filters={"invitation": invitation.name, "status": "In Progress"}, fields=["name"], limit=1)
    if existing:
        attempt = frappe.get_doc("Candidate Attempt", existing[0].name)
        nonce = guest_session.new_nonce(); attempt.session_nonce = nonce
        attempt.flags.ignore_permissions = True; attempt.save()
        return attempt, nonce

    completed = frappe.db.count("Candidate Attempt", {"invitation": invitation.name, "status": ["in", ["Submitted", "Evaluated", "Under Review", "Expired"]]})
    if completed >= (inv.max_attempts or 1): raise AttemptError("Attempt limit reached.")

    assessment = frappe.get_doc("Assessment", inv.assessment)
    if assessment.status != "Published": raise AttemptError("Assessment not open.")

    now = now_datetime(); nonce = guest_session.new_nonce()
    snapshot_json = _build_snapshot(assessment)
    
    attempt = frappe.get_doc({
        "doctype": "Candidate Attempt", "assessment": inv.assessment, "invitation": invitation.name,
        "status": "In Progress", "attempt_number": completed+1, "started_at": now,
        "deadline": add_to_date(now, minutes=assessment.duration_minutes), "session_nonce": nonce,
        "candidate_name": inv.candidate_name, "candidate_email": inv.candidate_email,
        "questions_snapshot": snapshot_json
    })
    attempt.flags.ignore_permissions = True; attempt.insert()
    return attempt, nonce

def extend_deadline(name, new_deadline, reason, user):
    attempt = frappe.get_doc("Candidate Attempt", name)
    if attempt.status != "In Progress": raise AttemptError("Only In-Progress attempts can be extended.")
    attempt.deadline = new_deadline
    attempt.flags.ignore_permissions = True; attempt.save()
    frappe.get_doc({"doctype":"Assessment Event","attempt":attempt.name,"event_type":"deadline_extended","metadata":f"by={user} reason={reason}"}).insert(ignore_permissions=True)

def submit_attempt(name):
    locked = frappe.db.get_value("Candidate Attempt", name, "name", for_update=True)
    if not locked: 
        raise AttemptError("Attempt not found.")
    attempt = frappe.get_doc("Candidate Attempt", name)
    
    if attempt.status in ("Submitted", "Expired"): 
        return {"status": attempt.status, "idempotent": True}
    if attempt.status != "In Progress": 
        raise AttemptError(f"Cannot submit from {attempt.status}.")
    
    now = now_datetime()
    target = "Expired" if now > attempt.deadline else "Submitted"
    attempt.status = target
    attempt.submitted_at = now
    attempt.session_nonce = ""
    attempt.flags.ignore_permissions = True
    attempt.submit()

    # Clear old 0-marks data and grade synchronously to avoid worker crashes
    frappe.db.sql("UPDATE `tabCandidate Answer` SET is_evaluated=0, awarded_marks=0, needs_manual_review=0 WHERE attempt=%s", name)
    
    from assessflow.services.grading import grade_attempt
    grade_attempt(name)
    
    frappe.db.commit()
    return {"status": target, "idempotent": False}

def expire_stale_attempts():
    stale = frappe.get_all("Candidate Attempt", filters={"status": "In Progress", "deadline": ["<", now_datetime()]}, pluck="name", limit=500)
    for name in stale:
        try:
            a = frappe.get_doc("Candidate Attempt", name)
            if a.status != "In Progress": continue
            a.status = "Expired"
            a.submitted_at = now_datetime()
            a.session_nonce = ""
            a.flags.ignore_permissions = True
            a.submit()
        except Exception:
            frappe.log_error(title=f"expire:{name}", message=frappe.get_traceback())
