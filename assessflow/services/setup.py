import frappe
def after_install():
    for role, desc in [("Assessment Administrator","Manage assessments"),("Assessment Author","Create/edit"),("Assessment Reviewer","Grade")]:
        if not frappe.db.exists("Role", role): frappe.get_doc({"doctype":"Role","role_name":role,"description":desc}).insert(ignore_permissions=True)
    frappe.db.commit()
