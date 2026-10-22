import frappe

def run():
    # Cleanup previous runs
    for a in frappe.get_all("Assessment", {"assessment_title": "Comprehensive Developer Assessment"}):
        frappe.delete_doc("Assessment", a.name, force=True)
    for q in frappe.get_all("Question Bank", {"question_title": ["like", "COMP-%"]}):
        frappe.delete_doc("Question Bank", q.name, force=True)

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
        if correct_text: doc["correct_text"] = correct_text
        if correct_num is not None: doc["correct_numeric"] = correct_num
        if tol is not None: doc["numeric_tolerance"] = tol
        return frappe.get_doc(doc).insert(ignore_permissions=True)

    # SECTION 1: Python
    py_q1 = mk_q("COMP-PY1: Python Dictionaries", "Single Choice", 5,
        "<p>What is the output of <code>len({'a': 1, 'b': 2})</code>?</p>",
        opts=[{"option_text": "1", "is_correct": 0}, {"option_text": "2", "is_correct": 1}, {"option_text": "Error", "is_correct": 0}]
    )
    py_q2 = mk_q("COMP-PY2: Sum Even Numbers", "Coding", 15,
        "<p>Write a function <code>sum_evens(nums)</code> that returns the sum of all even numbers in a list.</p>",
        lang="python", fn="sum_evens",
        starter="def sum_evens(nums):\n    # your code here\n    pass\n",
        tests=[
            {"description": "Standard list", "input_data": '[[1, 2, 3, 4, 5]]', "expected_output": "6", "is_hidden": 0, "marks": 5},
            {"description": "All evens", "input_data": '[[2, 4, 6]]', "expected_output": "12", "is_hidden": 0, "marks": 5},
            {"description": "No evens", "input_data": '[[1, 3, 5]]', "expected_output": "0", "is_hidden": 1, "marks": 5}
        ]
    )

    # SECTION 2: JavaScript
    js_q1 = mk_q("COMP-JS1: Array Methods", "Single Choice", 5,
        "<p>Which method removes the last element from an array?</p>",
        opts=[{"option_text": "push()", "is_correct": 0}, {"option_text": "pop()", "is_correct": 1}, {"option_text": "shift()", "is_correct": 0}, {"option_text": "unshift()", "is_correct": 0}]
    )
    js_q2 = mk_q("COMP-JS2: String Reverser", "Coding", 15,
        "<p>Write a function <code>reverseStr(str)</code> that reverses a string without using the built-in <code>.reverse()</code> method.</p>",
        lang="javascript", fn="reverseStr",
        starter="function reverseStr(str) {\n    // your code here\n}\nmodule.exports = { reverseStr };\n",
        tests=[
            {"description": "Basic word", "input_data": '["hello"]', "expected_output": "olleh", "is_hidden": 0, "marks": 5},
            {"description": "Sentence", "input_data": '["hello world"]', "expected_output": "dlrow olleh", "is_hidden": 0, "marks": 5},
            {"description": "Palindrome", "input_data": '["racecar"]', "expected_output": "racecar", "is_hidden": 1, "marks": 5}
        ]
    )

    # SECTION 3: HTML
    html_q1 = mk_q("COMP-HTML1: Semantic Tags", "Single Choice", 5,
        "<p>Which HTML tag is used to define an internal stylesheet?</p>",
        opts=[{"option_text": "&lt;script&gt;", "is_correct": 0}, {"option_text": "&lt;css&gt;", "is_correct": 0}, {"option_text": "&lt;style&gt;", "is_correct": 1}, {"option_text": "&lt;link&gt;", "is_correct": 0}]
    )
    html_q2 = mk_q("COMP-HTML2: Build a Login Form", "Coding", 15,
        "<p>Write the HTML for a login form. It must contain an <code>&lt;input&gt;</code> with type <code>email</code> and an <code>&lt;input&gt;</code> with type <code>password</code>.</p>",
        lang="html",
        starter="<!-- Write your HTML here -->\n<form>\n\n</form>",
        tests=[
            {"description": "Has email input", "input_data": '{"selector": "input[type=\\"email\\"]", "text": ""}', "expected_output": "true", "is_hidden": 0, "marks": 5},
            {"description": "Has password input", "input_data": '{"selector": "input[type=\\"password\\"]", "text": ""}', "expected_output": "true", "is_hidden": 0, "marks": 5},
            {"description": "Has form tag", "input_data": '{"selector": "form", "text": ""}', "expected_output": "true", "is_hidden": 1, "marks": 5}
        ]
    )

    # SECTION 4: Frappe Basic
    fr_q1 = mk_q("COMP-FR1: Frappe ORM", "Single Choice", 10,
        "<p>Which of the following is the correct way to fetch all records from a DocType in Frappe?</p>",
        opts=[{"option_text": "frappe.db.get('DocType')", "is_correct": 0}, {"option_text": "frappe.get_all('DocType')", "is_correct": 1}, {"option_text": "frappe.get_doc('DocType')", "is_correct": 0}, {"option_text": "frappe.db.fetch('DocType')", "is_correct": 0}]
    )
    fr_q2 = mk_q("COMP-FR2: Frappe Hooks", "Short Text", 10,
        "<p>What is the name of the Python file where you register document events in a Frappe app?</p>",
        correct_text="hooks.py"
    )

    # SECTION 5: CS Basic
    cs_q1 = mk_q("COMP-CS1: Big O Notation", "Single Choice", 10,
        "<p>What is the time complexity of binary search?</p>",
        opts=[{"option_text": "O(n)", "is_correct": 0}, {"option_text": "O(n log n)", "is_correct": 0}, {"option_text": "O(log n)", "is_correct": 1}, {"option_text": "O(1)", "is_correct": 0}]
    )
    cs_q2 = mk_q("COMP-CS2: Database Normalization", "Multiple Select", 10,
        "<p>Which of the following are normal forms in database design? (Select all that apply)</p>",
        opts=[
            {"option_text": "First Normal Form (1NF)", "is_correct": 1},
            {"option_text": "Second Normal Form (2NF)", "is_correct": 1},
            {"option_text": "Third Normal Form (3NF)", "is_correct": 1},
            {"option_text": "Fourth Normal Form (4NF)", "is_correct": 1}
        ]
    )
    frappe.db.set_value("Question Bank", cs_q2.name, "allow_partial_credit", 1)

    assessment = frappe.get_doc({
        "doctype": "Assessment",
        "assessment_title": "Comprehensive Developer Assessment",
        "status": "Published",
        "duration_minutes": 120,
        "pass_percentage": 60,
        "randomize_questions": 1,
        "allow_test_run": 1,
        "max_code_runs": 5,
        "show_test_results": 1,
        "description": "<p>This assessment covers Python, JavaScript, HTML, Frappe Framework, and Computer Science fundamentals.</p>",
        "instructions": "<ul><li>Do not switch tabs or exit fullscreen.</li><li>You have 5 code runs per coding question.</li><li>Partial credit is enabled for multiple-select questions.</li></ul>",
        "sections": [
            {"section_name": "Python", "instructions": "Answer the Python questions."},
            {"section_name": "JavaScript", "instructions": "Answer the JavaScript questions."},
            {"section_name": "HTML", "instructions": "Build the required HTML structures."},
            {"section_name": "Frappe Basic", "instructions": "Test your knowledge of Frappe."},
            {"section_name": "CS Basic", "instructions": "Computer Science fundamentals."}
        ],
        "questions": [
            {"question": py_q1.name, "marks": 5, "required": 1, "section": "Python"},
            {"question": py_q2.name, "marks": 15, "required": 1, "section": "Python"},
            {"question": js_q1.name, "marks": 5, "required": 1, "section": "JavaScript"},
            {"question": js_q2.name, "marks": 15, "required": 1, "section": "JavaScript"},
            {"question": html_q1.name, "marks": 5, "required": 1, "section": "HTML"},
            {"question": html_q2.name, "marks": 15, "required": 1, "section": "HTML"},
            {"question": fr_q1.name, "marks": 10, "required": 1, "section": "Frappe Basic"},
            {"question": fr_q2.name, "marks": 10, "required": 1, "section": "Frappe Basic"},
            {"question": cs_q1.name, "marks": 10, "required": 1, "section": "CS Basic"},
            {"question": cs_q2.name, "marks": 10, "required": 1, "section": "CS Basic"}
        ]
    }).insert(ignore_permissions=True)

    print(f"\n✓ Comprehensive Assessment Created: {assessment.name}")
    print(f'\nCreate invite: bench --site thriveraservices.local execute assessflow.api.admin.create_invitation --kwargs \'{{"assessment":"{assessment.name}","candidate_name":"Alice","candidate_email":"alice@example.com"}}\'')
