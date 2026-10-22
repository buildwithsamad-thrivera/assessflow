import frappe

def execute():
    assessments = frappe.get_all("Assessment", pluck="name")
    for name in assessments:
        try:
            doc = frappe.get_doc("Assessment", name)
            if not doc.sections:
                continue
            
            # If there are questions but no section assigned, assign to the first section
            changed = False
            default_sec = doc.sections[0].section_name if doc.sections else "General"
            for q in doc.questions:
                if not q.get("section"):
                    q.section = default_sec
                    changed = True
            
            if changed:
                doc.flags.ignore_permissions = True
                doc.save()
        except Exception:
            frappe.log_error(title=f"fix_sections_schema_{name}", message=frappe.get_traceback())
