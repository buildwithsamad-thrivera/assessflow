import json, uuid
import frappe
from frappe.utils import flt
from assessflow.services import code_runner

def grade_attempt(attempt_name):
    lock_key = f"grade_lock::{attempt_name}"; me = str(uuid.uuid4())
    if not frappe.cache().set(lock_key, me, nx=True, ex=120): return
    try: _do_grade(attempt_name)
    finally:
        if frappe.cache().get(lock_key) == me: frappe.cache().delete(lock_key)

def _do_grade(attempt_name):
    if not frappe.db.get_value("Candidate Attempt", attempt_name, "name", for_update=True): return
    attempt = frappe.get_doc("Candidate Attempt", attempt_name)
    if attempt.status not in ("Submitted", "Expired", "Evaluated"): return
    
    assessment = frappe.get_doc("Assessment", attempt.assessment)
    snapshot = json.loads(attempt.questions_snapshot or "{}")
    
    total, max_total, pending_manual = 0.0, 0.0, 0

    all_questions = []
    for sec in snapshot.get("sections", []):
        all_questions.extend(sec.get("questions", []))

    for q_dict in all_questions:
        max_marks = flt(q_dict.get("_aq_marks")) or flt(q_dict.get("default_marks")) or 0
        max_total += max_marks
        q_name = q_dict.get("name")
        
        ans = frappe.db.get_value("Candidate Answer", {"attempt": attempt.name, "question": q_name}, ["name", "submitted_payload", "answer_payload", "awarded_marks", "is_evaluated"], as_dict=True)
        
        # If already manually evaluated, keep the manual score
        if ans and ans.is_evaluated and attempt.status == "Evaluated":
            total += flt(ans.awarded_marks)
            continue

        payload = _decode(ans.submitted_payload or ans.answer_payload) if ans else None
        
        # Pass q_dict instead of q DocType to grader
        try: award, manual, _ = _score_question(q_dict, payload, max_marks)
        except Exception: award, manual = 0.0, True
            
        if manual:
            pending_manual += 1
            if ans: frappe.db.set_value("Candidate Answer", ans.name, "needs_manual_review", 1)
            continue
            
        total += award
        if ans: frappe.db.set_value("Candidate Answer", ans.name, {"awarded_marks": award, "is_evaluated": 1})

    pct = (total / max_total * 100.0) if max_total else 0.0
    attempt.total_score = total; attempt.max_score = max_total; attempt.percentage = round(pct, 2)
    attempt.passed = 1 if pct >= flt(assessment.pass_percentage) else 0
    
    if pending_manual == 0 and attempt.status != "Evaluated":
        attempt.status = "Evaluated"
        if assessment.get("show_result_immediately"): attempt.result_released = 1
    else:
        attempt.status = "Under Review"
        
    attempt.flags.ignore_permissions = True; attempt.save()

def _decode(raw):
    if raw in (None, ""): return None
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except Exception: return raw

def _score_question(q, payload, max_marks):
    qt = q.get("question_type"); neg = flt(q.get("negative_marks") or 0)
    
    if payload is None:
        return 0.0, False, None # Explicit: Blank = 0

    if qt in ("Single Choice", "True/False"):
        correct = [o.get("name") for o in (q.get("options") or []) if o.get("is_correct")]
        return (max_marks if payload in correct else (-neg if neg else 0.0)), False, None
        
    if qt == "Multiple Select":
        selected = set(payload if isinstance(payload, list) else [])
        correct = {o.get("name") for o in (q.get("options") or []) if o.get("is_correct")}
        
        if selected == correct: return max_marks, False, None
        if q.get("allow_partial_credit"):
            # Partial credit logic: + for correct, - for wrong
            ratio = len(selected & correct) / len(correct) if correct else 0
            penalty = len(selected - correct) / len(correct) if correct else 0
            score = (ratio - penalty) * max_marks
            return max(0.0, round(score, 2)), False, None
        
        return (-neg if neg else 0.0), False, None
        
    if qt == "Numeric":
        try: got = float(payload)
        except: return 0.0, False, None
        return (max_marks if abs(got - flt(q.get("correct_numeric") or 0)) <= flt(q.get("numeric_tolerance") or 0) else (-neg if neg else 0.0)), False, None
        
    if qt == "Short Text":
        got, exp = str(payload), q.get("correct_text") or ""
        if not q.get("match_case"): got, exp = got.lower(), exp.lower()
        ok = (got == exp) if q.get("match_exact") else (exp in got)
        return (max_marks if ok else (-neg if neg else 0.0)), False, None
        
    if qt == "Coding":
        # Code runner needs the DocType, not dict. Fetch it.
        q_doc = frappe.get_doc("Question Bank", q.get("name"))
        award, manual, _ = code_runner.grade_coding_question(q_doc, payload); return award, manual, None
        
    return 0.0, True, None
