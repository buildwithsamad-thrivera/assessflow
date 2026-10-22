import json
import frappe
from frappe.utils import now_datetime, time_diff_in_seconds
from datetime import timedelta
from assessflow.services import attempt as attempt_service, invitation as invitation_service

def _is_admin():
    return bool({"Assessment Administrator", "System Manager"} & set(frappe.get_roles()))

@frappe.whitelist()
def create_invitation(assessment, candidate_name, candidate_email, max_attempts=1):
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    doc, raw = invitation_service.create_invitation(assessment, candidate_name, candidate_email, max_attempts)
    return {"ok": True, "invitation": doc.name, "url": f"{frappe.utils.get_url()}/assessment?token={raw}", "hint": doc.token_hint}

@frappe.whitelist()
def revoke_invitation(invitation, reason=""):
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    invitation_service.revoke(invitation, reason)
    return {"ok": True}

@frappe.whitelist()
def extend_attempt(attempt, new_deadline, reason):
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    attempt_service.extend_deadline(attempt, new_deadline, reason, frappe.session.user)
    return {"ok": True}

@frappe.whitelist()
def get_attempt_events(attempt):
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    return {"ok": True, "events": frappe.get_all("Assessment Event", filters={"attempt": attempt}, fields=["name", "event_type", "occurred_at", "metadata"], order_by="occurred_at asc")}

@frappe.whitelist()
def get_pending_reviews(attempt):
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    answers = frappe.get_all("Candidate Answer", filters={"attempt": attempt, "needs_manual_review": 1}, fields=["name", "question", "submitted_payload"])
    res = []
    for a in answers:
        q = frappe.get_doc("Question Bank", a.question)
        res.append({"name": a.name, "question": a.question, "question_title": q.question_title, "question_type": q.question_type, "marks": q.default_marks, "answer": a.submitted_payload})
    return {"ok": True, "data": res}

@frappe.whitelist()
def submit_manual_grade(answer_name, marks, comment=""):
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    ans = frappe.get_doc("Candidate Answer", answer_name)
    ans.awarded_marks = float(marks)
    ans.is_evaluated = 1
    ans.needs_manual_review = 0
    ans.reviewer_comment = comment
    ans.flags.ignore_permissions = True
    ans.save()
    
    attempt = frappe.get_doc("Candidate Attempt", ans.attempt)
    frappe.get_doc({"doctype":"Assessment Event","attempt":attempt.name,"event_type":"manual_grade","metadata":f"q={ans.question} marks={marks} by={frappe.session.user}"}).insert(ignore_permissions=True)
    
    total = sum([float(a.awarded_marks or 0) for a in frappe.get_all("Candidate Answer", filters={"attempt": attempt.name}, fields=["awarded_marks"])])
    attempt.total_score = total
    attempt.percentage = round((total / attempt.max_score * 100), 2) if attempt.max_score else 0
    
    pending = frappe.db.count("Candidate Answer", {"attempt": attempt.name, "needs_manual_review": 1})
    if pending == 0:
        attempt.status = "Evaluated"
        if frappe.db.get_value("Assessment", attempt.assessment, "show_result_immediately"):
            attempt.result_released = 1
    attempt.flags.ignore_permissions = True
    attempt.flags.ignore_validate_update_after_submit = True
    attempt.save()
    return {"ok": True}

@frappe.whitelist()
def get_attempt_answers(attempt_name):
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    attempt = frappe.get_doc("Candidate Attempt", attempt_name)
    snapshot = json.loads(attempt.questions_snapshot or "{}")
    answers_map = {a.question: a for a in frappe.get_all("Candidate Answer", filters={"attempt": attempt_name}, fields=["*"])}
    
    res = []
    for sec in snapshot.get("sections", []):
        for q in sec.get("questions", []):
            ans = answers_map.get(q.get("name"))
            raw_payload = ans.submitted_payload or ans.answer_payload if ans else None
            display_ans = ""
            if raw_payload:
                try:
                    val = json.loads(raw_payload)
                    q_type = q.get("question_type")
                    if q_type in ("Single Choice", "True/False"):
                        for opt in q.get("options", []):
                            if opt.get("name") == val: display_ans = opt.get("option_text"); break
                        if not display_ans: display_ans = val
                    elif q_type == "Multiple Select":
                        texts = [opt.get("option_text") for opt in q.get("options", []) if opt.get("name") in val]
                        display_ans = ", ".join(texts)
                    else:
                        display_ans = val
                except Exception:
                    display_ans = raw_payload
            res.append({
                "answer_name": ans.name if ans else "",
                "question": q.get("question_title"), "type": q.get("question_type"),
                "max_marks": q.get("_aq_marks") or q.get("default_marks"),
                "awarded": ans.awarded_marks if ans else 0, "answer": display_ans if display_ans else "No Answer",
                "needs_manual": ans.needs_manual_review if ans else 0
            })
    return {"ok": True, "answers": res}

@frappe.whitelist()
def test_question_code(question_name, code):
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    q = frappe.get_doc("Question Bank", question_name)
    if q.question_type != "Coding": return {"ok": False, "error": "Not a coding question."}
    from assessflow.services import code_runner
    results = []
    for tc in (q.test_cases or []):
        try:
            r = code_runner.run_test_case(q.coding_language, code, q.coding_function_name or "solve", tc.input_data or "[]", tc.expected_output or "")
            got = r.stdout.strip().strip('"').strip("'")
            exp = (tc.expected_output or "").strip().strip('"').strip("'")
            passed = (not r.timed_out) and (got == exp)
            results.append({"description": tc.description or "Test Case", "passed": passed, "expected": exp, "got": got, "stderr": r.stderr, "is_hidden": tc.is_hidden})
        except Exception as e:
            results.append({"description": tc.description or "Test Case", "passed": False, "stderr": str(e)})
    return {"ok": True, "results": results}

@frappe.whitelist()
def get_dashboard_data():
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    
    # 1. Core KPIs
    total_assessments = frappe.db.count("Assessment")
    total_attempts = frappe.db.count("Candidate Attempt")
    pending_reviews = frappe.db.count("Candidate Attempt", {"status": "Under Review"})
    
    avg_score_res = frappe.db.sql("SELECT AVG(percentage) FROM `tabCandidate Attempt` WHERE status IN ('Evaluated', 'Under Review')")[0][0]
    avg_score = round(avg_score_res, 1) if avg_score_res else 0.0
    
    # 2. Live Monitor
    live_attempts = frappe.get_all("Candidate Attempt", filters={"status": "In Progress"}, fields=["name", "candidate_name", "assessment", "deadline", "started_at"])
    live_data = []
    now = now_datetime()
    for a in live_attempts:
        secs = time_diff_in_seconds(a.deadline, now) if a.deadline else 0
        if secs > 0:
            live_data.append({"name": a.name, "candidate": a.candidate_name, "assessment": a.assessment, "deadline_ts": a.deadline.timestamp() * 1000})
            
    # 3. Security Events
    recent_events = frappe.get_all("Assessment Event", filters={"event_type": ["in", ["tab_switch", "fullscreen_exit", "copy_attempt", "paste_attempt"]]}, fields=["name", "attempt", "event_type", "occurred_at", "metadata"], order_by="occurred_at desc", limit=8)
        
    # 4. Top Performers & Needs Attention
    top_performers = frappe.get_all("Candidate Attempt", filters={"status": "Evaluated"}, fields=["name", "candidate_name", "percentage"], order_by="percentage desc", limit=5)
    needs_attention = frappe.get_all("Candidate Attempt", filters={"status": "Under Review"}, fields=["name", "candidate_name", "assessment"], limit=5)

    # 5. Chart Data
    trend_labels, trend_attempts, trend_scores = [], [], []
    today = now_datetime().date()
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        trend_labels.append(d.strftime("%b %d"))
        day_attempts = frappe.db.count("Candidate Attempt", {"creation": ["between", [d, d + timedelta(days=1)]]})
        trend_attempts.append(day_attempts)
        day_score = frappe.db.sql("SELECT AVG(percentage) FROM `tabCandidate Attempt` WHERE status='Evaluated' AND DATE(creation)=%s", d)[0][0]
        trend_scores.append(round(day_score, 1) if day_score else 0)

    completed = frappe.db.count("Candidate Attempt", {"status": ["in", ["Evaluated", "Submitted", "Under Review"]]})
    expired = frappe.db.count("Candidate Attempt", {"status": "Expired"})
    active = len(live_data)
    
    return {
        "kpi": {"assessments": total_assessments, "attempts": total_attempts, "pending": pending_reviews, "avg_score": avg_score},
        "live": live_data, "events": recent_events, "top_performers": top_performers, "needs_attention": needs_attention,
        "trend": {"labels": trend_labels, "attempts": trend_attempts, "scores": trend_scores},
        "distribution": [completed, expired, active]
    }

@frappe.whitelist()
def force_submit_attempt(attempt_name):
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    try:
        from assessflow.services import answer as answer_service, attempt as attempt_service
        answer_service.freeze_answers(attempt_name)
        res = attempt_service.submit_attempt(attempt_name)
        return {"ok": True, "status": res["status"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}



@frappe.whitelist()
def submit_batch_manual_grades(attempt_name, grades):
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    import json
    grades_dict = json.loads(grades)
    
    attempt = frappe.get_doc("Candidate Attempt", attempt_name)
    max_score = attempt.max_score or 1
    
    total = 0.0
    for ans_name, marks in grades_dict.items():
        if not ans_name: continue
        try:
            ans = frappe.get_doc("Candidate Answer", ans_name)
            ans.awarded_marks = float(marks)
            ans.is_evaluated = 1
            ans.needs_manual_review = 0
            ans.flags.ignore_permissions = True
            ans.save()
        except Exception:
            pass
            
    # Recalculate totals
    all_ans = frappe.get_all("Candidate Answer", filters={"attempt": attempt_name}, fields=["awarded_marks"])
    total = sum([float(a.awarded_marks or 0) for a in all_ans])
    
    attempt.total_score = total
    attempt.percentage = round((total / (max_score or 1) * 100), 2)
    
    pass_pct = frappe.db.get_value("Assessment", attempt.assessment, "pass_percentage") or 40
    attempt.passed = 1 if attempt.percentage >= pass_pct else 0
    attempt.status = "Evaluated"
    
    if frappe.db.get_value("Assessment", attempt.assessment, "show_result_immediately"):
        attempt.result_released = 1
        
    attempt.flags.ignore_permissions = True
    attempt.flags.ignore_validate_update_after_submit = True
    attempt.save()
    
    frappe.get_doc({"doctype":"Assessment Event","attempt":attempt.name,"event_type":"manual_regrade","metadata":f"by={frappe.session.user}"}).insert(ignore_permissions=True)
    
    return {"ok": True, "new_score": attempt.total_score, "new_percentage": attempt.percentage}



@frappe.whitelist()
def send_invitation_email(invitation_name, raw_token):
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    inv = frappe.get_doc("Assessment Invitation", invitation_name)
    a = frappe.get_doc("Assessment", inv.assessment)
    
    link = f"{frappe.utils.get_url()}/assessment?token={raw_token}"
    
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
        <h2 style="color: #1e293b; text-align: center;">Assessment Invitation</h2>
        <p style="color: #475569; font-size: 16px;">Hello <strong>{inv.candidate_name}</strong>,</p>
        <p style="color: #475569; font-size: 16px;">You have been invited to take the following assessment:</p>
        <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; margin: 20px 0; border: 1px solid #e2e8f0;">
            <h3 style="margin: 0; color: #2563eb;">{a.assessment_title}</h3>
            <p style="margin: 5px 0 0; color: #64748b;">Duration: {a.duration_minutes} minutes</p>
        </div>
        <p style="color: #475569; font-size: 16px;">Please click the button below to begin. Note that the timer starts immediately upon opening the link.</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{link}" style="background-color: #2563eb; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; display: inline-block;">Start Assessment</a>
        </div>
        <p style="color: #94a3b8; font-size: 12px; text-align: center; margin-top: 40px;">This is an automated message. Please do not reply.</p>
    </div>
    """
    
    frappe.sendmail(
        recipients=[inv.candidate_email],
        subject=f"Invitation: {a.assessment_title}",
        message=html,
        now=True
    )
    return {"ok": True}

@frappe.whitelist()
def resend_invitation(invitation_name):
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    from assessflow.services import invitation as invitation_service
    
    # Generate new token securely
    inv = frappe.get_doc("Assessment Invitation", invitation_name)
    raw = invitation_service.regenerate_token(inv)
    
    # Send email
    send_invitation_email(invitation_name, raw)
    return {"ok": True}

@frappe.whitelist()
def send_result_email(attempt_name):
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    attempt = frappe.get_doc("Candidate Attempt", attempt_name)
    a = frappe.get_doc("Assessment", attempt.assessment)
    
    if attempt.status == "Evaluated":
        score_html = f"""
        <div style="text-align: center; margin: 20px 0;">
            <span style="font-size: 48px; font-weight: bold; color: {'#16a34a' if attempt.passed else '#dc2626'};">{attempt.percentage}%</span>
            <p style="color: #64748b; margin-top: 5px;">{attempt.total_score} out of {attempt.max_score} marks</p>
            <p style="font-weight: bold; font-size: 18px; color: {'#16a34a' if attempt.passed else '#dc2626'};">{'PASSED' if attempt.passed else 'NOT PASSED'}</p>
        </div>
        """
        subject = f"Result: {a.assessment_title}"
    else:
        score_html = """<p style="color: #ea580c; font-weight: bold; padding: 15px; background: #fffbeb; border-radius: 8px;">Your submission is currently under review. You will receive another email once grading is complete.</p>"""
        subject = f"Submission Received: {a.assessment_title}"
        
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
        <h2 style="color: #1e293b; text-align: center;">Assessment Result</h2>
        <p style="color: #475569; font-size: 16px;">Hello <strong>{attempt.candidate_name}</strong>,</p>
        <p style="color: #475569; font-size: 16px;">Here is the update for your recent assessment: <strong>{a.assessment_title}</strong>.</p>
        {score_html}
        <p style="color: #475569; font-size: 16px; text-align: center; margin-top: 30px;">Thank you for participating.</p>
    </div>
    """
    
    frappe.sendmail(
        recipients=[attempt.candidate_email],
        subject=subject,
        message=html,
        now=True
    )
    return {"ok": True}



@frappe.whitelist()
def rerun_auto_evaluation(attempt_name):
    if not _is_admin(): frappe.throw("Not permitted.", frappe.PermissionError)
    
    attempt = frappe.get_doc("Candidate Attempt", attempt_name)
    if attempt.status not in ("Submitted", "Expired", "Under Review", "Evaluated"):
        frappe.throw("Only submitted attempts can be re-evaluated.")
        
    # Clear old evaluation flags so the engine grades everything fresh
    frappe.db.sql("""
        UPDATE `tabCandidate Answer` 
        SET is_evaluated=0, awarded_marks=0, needs_manual_review=0 
        WHERE attempt=%s
    """, attempt_name)
    
    # Call grading engine synchronously
    from assessflow.services.grading import grade_attempt
    grade_attempt(attempt_name)
    
    frappe.db.commit()
    
    updated_attempt = frappe.get_doc("Candidate Attempt", attempt_name)
    return {
        "ok": True, 
        "new_score": updated_attempt.total_score, 
        "new_percentage": updated_attempt.percentage,
        "status": updated_attempt.status
    }
