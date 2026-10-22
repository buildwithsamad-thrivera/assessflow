import frappe

def run():
    print("Cleaning up old 'Master Test' data...")
    for a in frappe.get_all("Assessment", {"assessment_title": "Master Test - All Question Types"}):
        frappe.delete_doc("Assessment", a.name, force=True)
    for q in frappe.get_all("Question Bank", {"question_title": ["like", "MASTER-%"]}):
        frappe.delete_doc("Question Bank", q.name, force=True)

    print("Creating questions...")

    def mk_q(title, qtype, marks, html, opts=None, lang=None, fn=None, starter=None, tests=None, correct_text=None, correct_num=None, tol=None):
        doc = {
            "doctype": "Question Bank", "question_title": title, "question_type": qtype,
            "question_html": html, "default_marks": marks,
        }
        if opts: doc["options"] = opts
        if lang: doc["coding_language"] = lang
        if fn: doc["coding_function_name"] = fn
        if starter: doc["starter_code"] = starter
        if tests: doc["test_cases"] = tests
        if correct_text is not None: doc["correct_text"] = correct_text
        if correct_num is not None: doc["correct_numeric"] = correct_num
        if tol is not None: doc["numeric_tolerance"] = tol
        
        q_doc = frappe.get_doc(doc)
        q_doc.insert(ignore_permissions=True)
        q_doc.submit() # Submit to lock it
        return q_doc

    # --- SECTION 1: General Knowledge ---
    q1 = mk_q("MASTER-1: Single Choice", "Single Choice", 5, "<p>What is the capital of France?</p>",
        opts=[{"option_text": "London", "is_correct": 0}, {"option_text": "Paris", "is_correct": 1}, {"option_text": "Berlin", "is_correct": 0}])
    
    q2 = mk_q("MASTER-2: Multiple Select", "Multiple Select", 5, "<p>Which of the following are programming languages? (Select all)</p>",
        opts=[{"option_text": "Python", "is_correct": 1}, {"option_text": "HTML", "is_correct": 0}, {"option_text": "C++", "is_correct": 1}, {"option_text": "HTTP", "is_correct": 0}])
    frappe.db.set_value("Question Bank", q2.name, "allow_partial_credit", 1)

    q3 = mk_q("MASTER-3: True/False", "True/False", 5, "<p>HTTP is a stateless protocol.</p>",
        opts=[{"option_text": "True", "is_correct": 1}, {"option_text": "False", "is_correct": 0}])

    # --- SECTION 2: Advanced Inputs ---
    q4 = mk_q("MASTER-4: Short Text", "Short Text", 5, "<p>What does HTML stand for? (No abbreviations, exact match required)</p>",
        correct_text="HyperText Markup Language")
    frappe.db.set_value("Question Bank", q4.name, "match_exact", 1)
    frappe.db.set_value("Question Bank", q4.name, "match_case", 0)

    q5 = mk_q("MASTER-5: Long Text", "Long Text", 10, "<p>Explain the difference between a List and a Tuple in Python. (This will be manually graded).</p>")

    q6 = mk_q("MASTER-6: Numeric", "Numeric", 5, "<p>What is the square root of 144? (Tolerance: 0.1)</p>",
        correct_num=12.0, tol=0.1)

    # --- SECTION 3: Coding Challenges ---
    q7 = mk_q("MASTER-7: Python Code", "Coding", 10, "<p>Write a function <code>multiply(a, b)</code> that returns the product of two numbers.</p>",
        lang="python", fn="multiply", starter="def multiply(a, b):\n    pass\n",
        tests=[{"description": "2x3", "input_data": '[2, 3]', "expected_output": "6", "is_hidden": 0, "marks": 5},
               {"description": "10x10", "input_data": '[10, 10]', "expected_output": "100", "is_hidden": 1, "marks": 5}])

    q8 = mk_q("MASTER-8: JS Code", "Coding", 10, "<p>Write a function <code>toUpper(str)</code> that returns the string in uppercase.</p>",
        lang="javascript", fn="toUpper", starter="function toUpper(str) {\n    \n}\nmodule.exports = { toUpper };\n",
        tests=[{"description": "hello", "input_data": '["hello"]', "expected_output": "HELLO", "is_hidden": 0, "marks": 5},
               {"description": "world", "input_data": '["world"]', "expected_output": "WORLD", "is_hidden": 1, "marks": 5}])

    q9 = mk_q("MASTER-9: HTML Code", "Coding", 10, "<p>Create a button element containing the text 'Submit'.</p>",
        lang="html", starter="<!-- Write your HTML here -->\n",
        tests=[{"description": "Button exists", "input_data": '{"selector": "button", "text": "Submit"}', "expected_output": "true", "is_hidden": 0, "marks": 10}])

    print("Creating assessment...")
    assessment = frappe.get_doc({
        "doctype": "Assessment",
        "assessment_title": "Master Test - All Question Types",
        "status": "Published",
        "duration_minutes": 60,
        "pass_percentage": 50,
        "randomize_questions": 0,
        "allow_test_run": 1,
        "max_code_runs": 3,
        "show_test_results": 1,
        "description": "<p>This is a master test containing every single question type supported by the platform.</p>",
        "instructions": "<ul><li>Do not switch tabs.</li><li>You have 60 minutes.</li><li>Long text answers are manually graded.</li></ul>",
        "sections": [
            {"section_name": "General Knowledge", "instructions": "Basic multiple choice and true/false."},
            {"section_name": "Advanced Inputs", "instructions": "Text, Numeric, and manual grading."},
            {"section_name": "Coding Challenges", "instructions": "Write code in Python, JS, and HTML."}
        ],
        "questions": [
            {"question": q1.name, "marks": 5, "required": 1, "section": "General Knowledge"},
            {"question": q2.name, "marks": 5, "required": 1, "section": "General Knowledge"},
            {"question": q3.name, "marks": 5, "required": 1, "section": "General Knowledge"},
            
            {"question": q4.name, "marks": 5, "required": 1, "section": "Advanced Inputs"},
            {"question": q5.name, "marks": 10, "required": 0, "section": "Advanced Inputs"},
            {"question": q6.name, "marks": 5, "required": 1, "section": "Advanced Inputs"},
            
            {"question": q7.name, "marks": 10, "required": 1, "section": "Coding Challenges"},
            {"question": q8.name, "marks": 10, "required": 1, "section": "Coding Challenges"},
            {"question": q9.name, "marks": 10, "required": 1, "section": "Coding Challenges"}
        ]
    })
    assessment.insert(ignore_permissions=True)
    assessment.submit()

    print(f"\n✓ Master Test Created: {assessment.name}")
    print(f'\nCreate invite: bench --site thriveraservices.local execute assessflow.api.admin.create_invitation --kwargs \'{{"assessment":"{assessment.name}","candidate_name":"Alice","candidate_email":"alice@example.com"}}\'')
