import frappe

def run():
    for a in frappe.get_all("Assessment", {"assessment_title": "Demo Quiz"}): frappe.delete_doc("Assessment", a.name, force=True)
    for q in frappe.get_all("Question Bank", {"question_title": ["like", "Demo%"]}): frappe.delete_doc("Question Bank", q.name, force=True)

    mcq = frappe.get_doc({"doctype":"Question Bank","question_title":"Demo: What is 2+2?","question_type":"Single Choice","question_html":"<p>What is 2+2?</p>","default_marks":1,"options":[{"option_text":"3","is_correct":0},{"option_text":"4","is_correct":1},{"option_text":"5","is_correct":0}]}).insert(ignore_permissions=True)
    
    coding = frappe.get_doc({
        "doctype":"Question Bank","question_title":"Demo: Reverse a String","question_type":"Coding",
        "question_html":"<p>Implement <code>reverse_string(s)</code> that takes a string and returns it reversed.</p>",
        "default_marks":5,"coding_language":"python","coding_function_name":"reverse_string",
        "starter_code":"def reverse_string(s):\n    # your code here\n    pass\n",
        "test_cases":[
            {"description": "hello", "input_data": '["hello"]', "expected_output": "olleh", "is_hidden": 0, "marks": 2},
            {"description": "hidden abc", "input_data": '["abc"]', "expected_output": "cba", "is_hidden": 1, "marks": 3},
        ],
    }).insert(ignore_permissions=True)

    assessment = frappe.get_doc({
        "doctype":"Assessment","assessment_title":"Demo Quiz","status":"Published","duration_minutes":20,"pass_percentage":50,
        "description":"<p>Demo assessment covering MCQ + coding.</p>","instructions":"<ul><li>Ensure you write the function exactly as requested.</li><li>The timer does not pause.</li></ul>",
        "questions":[{"question":mcq.name,"marks":1,"required":1},{"question":coding.name,"marks":5,"required":1}],
    }).insert(ignore_permissions=True)

    print(f"\n✓ Demo created: {assessment.name}")
    print(f'\nCreate invite: bench --site thriveraservices.local execute assessflow.api.admin.create_invitation --kwargs \'{{"assessment":"{assessment.name}","candidate_name":"Alice","candidate_email":"alice@example.com"}}\'')
