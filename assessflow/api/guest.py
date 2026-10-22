import json
import frappe
from frappe.rate_limiter import rate_limit
from assessflow.services import answer as answer_service, attempt as attempt_service, code_runner, invitation as invitation_service, session as guest_session

ALLOWED_EVENTS = {"focus_lost","visibility_hidden","visibility_visible","fullscreen_exit","copy_attempt","paste_attempt","cut_attempt","tab_switch","tab_return","window_blur","right_click","mark_for_review","code_run","assessment_start","assessment_submit","shortcut_blocked","warning_shown"}

def _meta(a):
    return {"title":a.assessment_title,"description":a.description or "","instructions":a.instructions or "","duration_minutes":a.duration_minutes,"question_count":len(a.questions or []),"allow_test_run":bool(a.get("allow_test_run")),"max_code_runs":int(a.get("max_code_runs") or 0),"show_test_results":bool(a.get("show_test_results"))}

def _safe_question(q_dict, attempt, assessment):
    out = {
        "name": q_dict.get("name"), "title": q_dict.get("question_title"), "question_type": q_dict.get("question_type"),
        "question_html": q_dict.get("question_html") or "", "marks": q_dict.get("_aq_marks") or q_dict.get("default_marks"),
        "required": bool(q_dict.get("_aq_required"))
    }
    if q_dict.get("question_type") in ("Single Choice","Multiple Select","True/False"): 
        out["options"] = [{"name":o.get("name"),"text":o.get("option_text")} for o in (q_dict.get("options") or [])]
    elif q_dict.get("question_type") == "Numeric": 
        out["tolerance"] = q_dict.get("numeric_tolerance") or 0
    elif q_dict.get("question_type") == "Coding":
        out["language"] = q_dict.get("coding_language") or "python"; out["starter_code"] = q_dict.get("starter_code") or ""; out["coding_function_name"] = q_dict.get("coding_function_name") or "solve"
        public = [{"description":t.get("description"),"input_data":t.get("input_data"),"expected_output":t.get("expected_output"),"marks":t.get("marks")} for t in (q_dict.get("test_cases") or []) if not t.get("is_hidden")]
        out["public_test_cases"] = public; out["hidden_test_count"] = sum(1 for t in (q_dict.get("test_cases") or []) if t.get("is_hidden"))
        out["allow_test_run"] = bool(assessment.get("allow_test_run")) and bool(public)
        out["max_runs"] = int(assessment.get("max_code_runs") or 0); out["runs_used"] = answer_service.get_run_count(attempt.name, q_dict.get("name")); out["show_test_results"] = bool(assessment.get("show_test_results"))
    return out

def _log_event(attempt_name, event_type, metadata=None):
    try:
        doc = frappe.get_doc({"doctype":"Assessment Event","attempt":attempt_name,"event_type":event_type,"metadata":(metadata or "")[:500]})
        doc.insert(ignore_permissions=True)
        doc.submit()
    except Exception:
        frappe.log_error(title=f"event::{event_type}", message=frappe.get_traceback())

@frappe.whitelist(allow_guest=True)
@rate_limit(key="ip", limit=20, seconds=60)
def verify_invitation(token):
    try: inv = invitation_service.verify_token(token)
    except invitation_service.InvitationError: return {"ok": False, "error": "Invalid or expired invitation."}
    a = frappe.get_doc("Assessment", inv.assessment)
    return {"ok": True, "assessment": _meta(a), "candidate_name": inv.candidate_name, "candidate_email": inv.candidate_email}

@frappe.whitelist(allow_guest=True)
@rate_limit(key="ip", limit=10, seconds=60)
def start_assessment(token):
    try: inv = invitation_service.verify_token(token)
    except invitation_service.InvitationError: return {"ok": False, "error": "Invalid or expired invitation."}
    try: attempt, nonce = attempt_service.start_attempt(inv)
    except attempt_service.AttemptError as e: return {"ok": False, "error": str(e)}
    guest_session.set_session_cookie(attempt.name, nonce); a = frappe.get_doc("Assessment", attempt.assessment)
    _log_event(attempt.name, "assessment_start")
    return {"ok": True, "attempt_id": attempt.name, "deadline": attempt.deadline.isoformat(), "assessment": _meta(a), "session_token": guest_session.make_session_token(attempt.name, nonce)}

@frappe.whitelist(allow_guest=True)
@rate_limit(key="ip", limit=120, seconds=60)
def get_attempt_state(session_token=None):
    try: attempt = guest_session.require_session(session_token=session_token)
    except frappe.PermissionError: return {"ok": False, "error": "Not authorized."}
    a = frappe.get_doc("Assessment", attempt.assessment)
    saved, marked = {}, {}
    for r in frappe.get_all("Candidate Answer", filters={"attempt": attempt.name}, fields=["question", "answer_payload", "marked_for_review"]):
        saved[r.question] = r.answer_payload; marked[r.question] = bool(r.marked_for_review)
    
    snapshot = json.loads(attempt.questions_snapshot or "{}")
    sections_out = []
    for sec in snapshot.get("sections", []):
        sections_out.append({
            "name": sec.get("name"),
            "instructions": sec.get("instructions"),
            "questions": [_safe_question(q, attempt, a) for q in sec.get("questions", [])]
        })
    
    return {"ok": True, "attempt_id": attempt.name, "status": attempt.status, "deadline": attempt.deadline.isoformat(), "assessment": _meta(a), "sections": sections_out, "answers": saved, "marked_for_review": marked}

@frappe.whitelist(allow_guest=True)
@rate_limit(key="ip", limit=60, seconds=60)
def save_answer(question, payload=None, session_token=None, marked_for_review=None):
    try: return {"ok": True, **answer_service.save_answer(question, payload, session_token=session_token, marked_for_review=marked_for_review)}
    except frappe.PermissionError: return {"ok": False, "error": "Not authorized."}
    except attempt_service.AttemptError as e: return {"ok": False, "error": str(e)}

@frappe.whitelist(allow_guest=True)
def toggle_mark_for_review(question, marked=0, session_token=None):
    try: return {"ok": True, **answer_service.toggle_mark_for_review(question, bool(int(marked)), session_token=session_token)}
    except frappe.PermissionError: return {"ok": False, "error": "Not authorized."}
    except attempt_service.AttemptError as e: return {"ok": False, "error": str(e)}

@frappe.whitelist(allow_guest=True)
@rate_limit(key="ip", limit=30, seconds=60)
def run_code(question, code=None, session_token=None):
    try: attempt = guest_session.require_session(session_token=session_token)
    except frappe.PermissionError: return {"ok": False, "error": "Not authorized."}
    if attempt.status != "In Progress": return {"ok": False, "error": "Attempt is closed."}
    from frappe.utils import now_datetime
    if now_datetime() > attempt.deadline: return {"ok": False, "error": "Deadline passed."}
    
    snapshot = json.loads(attempt.questions_snapshot or "{}")
    q_dict = None
    for sec in snapshot.get("sections", []):
        for q in sec.get("questions", []):
            if q.get("name") == question:
                q_dict = q
                break
        if q_dict: break
        
    if not q_dict: return {"ok": False, "error": "Not authorized."}
    
    assessment = frappe.get_doc("Assessment", attempt.assessment)
    if not assessment.get("allow_test_run"): return {"ok": False, "error": "Disabled for this assessment."}
    max_runs = int(assessment.get("max_code_runs") or 0); used = answer_service.get_run_count(attempt.name, question)
    if max_runs > 0 and used >= max_runs: return {"ok": False, "error": f"Run limit reached ({max_runs})."}
    
    if q_dict.get("question_type") != "Coding": return {"ok": False, "error": "Not a coding question."}
    
    answer_service.bump_run_count(attempt.name, question)
    # We must fetch the live question doc for the runner
    q_doc = frappe.get_doc("Question Bank", question)
    result = code_runner.run_public_tests(q_doc, code or "")
    _log_event(attempt.name, "code_run", f"q={question} passed={result.get('summary',{}).get('passed',0)}/{result.get('summary',{}).get('total',0)}" if result.get("ok") else f"err={result.get('error','')}")
    
    if not result.get("ok"): return {"ok": False, "error": result.get("error", "Runner failed.")}
    if not assessment.get("show_test_results"): return {"ok": True, "summary": result["summary"], "message": "Code executed."}
    return {"ok": True, "tests": result["tests"], "summary": result["summary"]}

@frappe.whitelist(allow_guest=True)
@rate_limit(key="ip", limit=10, seconds=60)
def submit_attempt(session_token=None):
    try: attempt = guest_session.require_session(session_token=session_token)
    except frappe.PermissionError: return {"ok": False, "error": "Not authorized."}
    try:
        answer_service.freeze_answers(attempt.name)
        r = attempt_service.submit_attempt(attempt.name)
        _log_event(attempt.name, "assessment_submit", f"status={r['status']}")
        
        # Fetch the updated attempt to check result release
        updated = frappe.get_doc("Candidate Attempt", attempt.name)
        show_res = updated.result_released and updated.status == "Evaluated"
        score = updated.percentage if show_res else None
        
    except attempt_service.AttemptError as e: return {"ok": False, "error": str(e)}
    return {"ok": True, "status": r["status"], "idempotent": r.get("idempotent", False), "show_result": show_res, "score": score}

@frappe.whitelist(allow_guest=True)
@rate_limit(key="ip", limit=60, seconds=60)
def log_event(event_type, metadata="", session_token=None):
    if event_type not in ALLOWED_EVENTS: return {"ok": False}
    try: attempt = guest_session.require_session(session_token=session_token)
    except frappe.PermissionError: return {"ok": False}
    _log_event(attempt.name, event_type, metadata or "")
    return {"ok": True}
