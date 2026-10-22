import frappe
def execute():
    if not frappe.db.has_column("Assessment", "questions"): return
    # Move flat questions into a default "General" section
    assessments = frappe.get_all("Assessment", filters={"questions": ["is", "set"]}, pluck="name")
    for name in assessments:
        try:
            doc = frappe.get_doc("Assessment", name)
            if doc.get("questions") and not doc.get("sections"):
                doc.append("sections", {"section_name": "General", "questions": doc.questions})
                doc.questions = []
                doc.flags.ignore_permissions = True
                doc.save()
                frappe.db.commit()
        except Exception:
            frappe.log_error(title=f"section_migration_{name}", message=frappe.get_traceback())
