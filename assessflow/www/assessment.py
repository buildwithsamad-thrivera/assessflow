import frappe
def get_context(context):
    context.no_cache = 1; context.token = frappe.form_dict.get("token", "")
    try: context.csrf_token = frappe.sessions.get_csrf_token() or ""
    except Exception: context.csrf_token = ""
    return context
