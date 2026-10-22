import frappe
AUTHOR = {"System Manager", "Assessment Administrator", "Assessment Author"}
REVIEWER = {"System Manager", "Assessment Administrator", "Assessment Reviewer"}
def _roles(): return set() if frappe.session.user == "Guest" else set(frappe.get_roles())
def invitation_has_permission(doc=None, ptype=None, user=None, debug=False): return bool(_roles() & AUTHOR)
def attempt_has_permission(doc=None, ptype=None, user=None, debug=False): return bool(_roles() & REVIEWER)
def answer_has_permission(doc=None, ptype=None, user=None, debug=False): return bool(_roles() & REVIEWER)
def question_has_permission(doc=None, ptype=None, user=None, debug=False): return bool(_roles() & AUTHOR)
