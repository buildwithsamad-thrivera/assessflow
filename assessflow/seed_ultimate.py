import frappe

def run():
    print("Starting cleanup...")
    # Delete all data in correct order to prevent link errors
    for dt in ["Candidate Answer", "Assessment Event", "Candidate Attempt", "Assessment Invitation", "Assessment Question", "Assessment Section", "Assessment", "Question Bank", "Question Option", "Code Test Case"]:
        frappe.db.sql(f"DELETE FROM `tab{dt}`")
    frappe.db.commit()
    print("Database wiped.")

    print("Creating Junior Frappe Developer Assessment...")

    def mk_q(title, qtype, marks, html, opts=None, lang=None, fn=None, starter=None, tests=None, correct_text=None):
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
        return frappe.get_doc(doc).insert(ignore_permissions=True)

    # --- SECTION 1: Python Basics (20 Marks) ---
    p1 = mk_q("PY-1: List Comprehension", "Single Choice", 5, "<p>What is the output of <code>[x*x for x in range(3)]</code>?</p>",
        opts=[{"option_text": "[0, 1, 4]", "is_correct": 1}, {"option_text": "[1, 4, 9]", "is_correct": 0}, {"option_text": "[0, 1, 2]", "is_correct": 0}])
    
    p2 = mk_q("PY-2: String Formatting", "Short Text", 5, "<p>What method is used to format strings in Python 3.6+ using <code>f'...'</code>? (Answer in 1 word)</p>", correct_text="f-string")
    
    p3 = mk_q("PY-3: Sum Evens", "Coding", 10, "<p>Write a function <code>sum_evens(nums)</code> that returns the sum of all even numbers in a list.</p>",
        lang="python", fn="sum_evens", starter="def sum_evens(nums):\n    pass\n",
        tests=[{"input_data": '[[1,2,3,4]]', "expected_output": "6", "is_hidden": 0, "marks": 5}, {"input_data": '[[2,4,6]]', "expected_output": "12", "is_hidden": 1, "marks": 5}])

    # --- SECTION 2: Frappe Framework (20 Marks) ---
    f1 = mk_q("FR-1: Frappe ORM", "Single Choice", 5, "<p>Which method fetches multiple records in Frappe?</p>",
        opts=[{"option_text": "frappe.get_doc", "is_correct": 0}, {"option_text": "frappe.get_all", "is_correct": 1}, {"option_text": "frappe.db.get_value", "is_correct": 0}])
    
    f2 = mk_q("FR-2: Hooks File", "Short Text", 5, "<p>Which file is used to register document events in a Frappe app?</p>", correct_text="hooks.py")
    
    f3 = mk_q("FR-3: Whitelist Decorator", "Single Choice", 5, "<p>Which decorator allows a Python method to be called via API?</p>",
        opts=[{"option_text": "@frappe.whitelist()", "is_correct": 1}, {"option_text": "@frappe.api()", "is_correct": 0}, {"option_text": "@frappe.route()", "is_correct": 0}])
    
    f4 = mk_q("FR-4: DocType Controller", "Short Text", 5, "<p>What is the name of the Python class a DocType inherits from? (Just the class name)</p>", correct_text="Document")

    # --- SECTION 3: Database & SQL (20 Marks) ---
    s1 = mk_q("SQL-1: SQL Joins", "Single Choice", 5, "<p>Which join returns all rows from the left table, and matched rows from the right?</p>",
        opts=[{"option_text": "INNER JOIN", "is_correct": 0}, {"option_text": "LEFT JOIN", "is_correct": 1}, {"option_text": "RIGHT JOIN", "is_correct": 0}])
    
    s2 = mk_q("SQL-2: Primary Keys", "Short Text", 5, "<p>What type of key uniquely identifies a record in a table?</p>", correct_text="Primary Key")
    
    s3 = mk_q("SQL-3: Indexes", "Single Choice", 5, "<p>What is the main benefit of adding an index to a database column?</p>",
        opts=[{"option_text": "Reduces storage space", "is_correct": 0}, {"option_text": "Speeds up read queries", "is_correct": 1}, {"option_text": "Prevents duplicate data", "is_correct": 0}])
    
    s4 = mk_q("SQL-4: Delete vs Truncate", "Multiple Select", 5, "<p>Which statements are true? (Select all)</p>",
        opts=[{"option_text": "DELETE can be rolled back", "is_correct": 1}, {"option_text": "TRUNCATE is faster than DELETE", "is_correct": 1}, {"option_text": "TRUNCATE can have a WHERE clause", "is_correct": 0}])

    # --- SECTION 4: JavaScript (20 Marks) ---
    j1 = mk_q("JS-1: Array Methods", "Single Choice", 5, "<p>Which method adds an element to the end of an array?</p>",
        opts=[{"option_text": "push()", "is_correct": 1}, {"option_text": "pop()", "is_correct": 0}, {"option_text": "shift()", "is_correct": 0}])
    
    j2 = mk_q("JS-2: Strict Equality", "Single Choice", 5, "<p>What does <code>===</code> check compared to <code>==</code>?</p>",
        opts=[{"option_text": "Value only", "is_correct": 0}, {"option_text": "Value and Type", "is_correct": 1}, {"option_text": "Type only", "is_correct": 0}])
    
    j3 = mk_q("JS-3: Reverse String", "Coding", 10, "<p>Write a function <code>reverseStr(str)</code> that reverses a string.</p>",
        lang="javascript", fn="reverseStr", starter="function reverseStr(str) {\n    \n}\nmodule.exports = { reverseStr };\n",
        tests=[{"input_data": '["hello"]', "expected_output": "olleh", "is_hidden": 0, "marks": 5}, {"input_data": '["world"]', "expected_output": "dlrow", "is_hidden": 1, "marks": 5}])

    # --- SECTION 5: CS Fundamentals (20 Marks) ---
    c1 = mk_q("CS-1: Big O", "Single Choice", 5, "<p>What is the time complexity of binary search?</p>",
        opts=[{"option_text": "O(n)", "is_correct": 0}, {"option_text": "O(log n)", "is_correct": 1}, {"option_text": "O(n log n)", "is_correct": 0}])
    
    c2 = mk_q("CS-2: HTTP Status", "Single Choice", 5, "<p>Which HTTP status code means 'Unauthorized'?</p>",
        opts=[{"option_text": "404", "is_correct": 0}, {"option_text": "500", "is_correct": 0}, {"option_text": "401", "is_correct": 1}])
    
    c3 = mk_q("CS-3: OOP Concepts", "Multiple Select", 5, "<p>Which of these are OOP concepts? (Select all)</p>",
        opts=[{"option_text": "Inheritance", "is_correct": 1}, {"option_text": "Polymorphism", "is_correct": 1}, {"option_text": "Compilation", "is_correct": 0}])
    
    c4 = mk_q("CS-4: HTTP Method", "Short Text", 5, "<p>Which HTTP method is used to update an existing resource?</p>", correct_text="PUT")

    assessment = frappe.get_doc({
        "doctype": "Assessment",
        "assessment_title": "Junior Frappe Developer",
        "status": "Published",
        "duration_minutes": 90,
        "pass_percentage": 60,
        "randomize_questions": 0,
        "allow_test_run": 1,
        "max_code_runs": 5,
        "show_test_results": 1,
        "description": "<p>This test evaluates core competencies required for a Junior Frappe Developer role.</p>",
        "instructions": "<ul><li>Do not switch tabs or exit fullscreen.</li><li>You have 90 minutes to complete 20 questions.</li><li>Partial credit is enabled for multiple-select questions.</li></ul>",
        "sections": [
            {"section_name": "Python Basics", "instructions": "Fundamentals of Python programming."},
            {"section_name": "Frappe Framework", "instructions": "Core Frappe concepts and APIs."},
            {"section_name": "Database & SQL", "instructions": "SQL queries and database design."},
            {"section_name": "JavaScript", "instructions": "Frontend scripting and logic."},
            {"section_name": "Computer Science", "instructions": "General CS fundamentals."}
        ],
        "questions": [
            {"question": p1.name, "marks": 5, "required": 1, "section": "Python Basics"},
            {"question": p2.name, "marks": 5, "required": 1, "section": "Python Basics"},
            {"question": p3.name, "marks": 10, "required": 1, "section": "Python Basics"},
            
            {"question": f1.name, "marks": 5, "required": 1, "section": "Frappe Framework"},
            {"question": f2.name, "marks": 5, "required": 1, "section": "Frappe Framework"},
            {"question": f3.name, "marks": 5, "required": 1, "section": "Frappe Framework"},
            {"question": f4.name, "marks": 5, "required": 1, "section": "Frappe Framework"},
            
            {"question": s1.name, "marks": 5, "required": 1, "section": "Database & SQL"},
            {"question": s2.name, "marks": 5, "required": 1, "section": "Database & SQL"},
            {"question": s3.name, "marks": 5, "required": 1, "section": "Database & SQL"},
            {"question": s4.name, "marks": 5, "required": 1, "section": "Database & SQL"},
            
            {"question": j1.name, "marks": 5, "required": 1, "section": "JavaScript"},
            {"question": j2.name, "marks": 5, "required": 1, "section": "JavaScript"},
            {"question": j3.name, "marks": 10, "required": 1, "section": "JavaScript"},
            
            {"question": c1.name, "marks": 5, "required": 1, "section": "Computer Science"},
            {"question": c2.name, "marks": 5, "required": 1, "section": "Computer Science"},
            {"question": c3.name, "marks": 5, "required": 1, "section": "Computer Science"},
            {"question": c4.name, "marks": 5, "required": 1, "section": "Computer Science"}
        ]
    }).insert(ignore_permissions=True)

    print(f"\n✓ Assessment Created: {assessment.name}")
    print(f'\nCreate invite: bench --site thriveraservices.local execute assessflow.api.admin.create_invitation --kwargs \'{{"assessment":"{assessment.name}","candidate_name":"Alice","candidate_email":"alice@example.com"}}\'')
