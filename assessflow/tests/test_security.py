import hashlib, frappe
from frappe.tests.utils import FrappeTestCase
from assessflow.services import invitation as inv_service

class TestInvitationSecurity(FrappeTestCase):
    def setUp(self): frappe.set_user("Administrator")
    def _mk_a(self):
        return frappe.get_doc({"doctype":"Assessment","assessment_title":"SecTest","status":"Published","duration_minutes":30}).insert(ignore_permissions=True).name

    def test_raw_token_not_persisted(self):
        a = self._mk_a(); doc, raw = inv_service.create_invitation(a, "T", "t@example.com")
        s = frappe.db.get_value("Assessment Invitation", doc.name, ["token", "token_hash", "token_hint"], as_dict=True)
        self.assertEqual(s.token, ""); self.assertEqual(s.token_hash, hashlib.sha256(raw.encode()).hexdigest())

    def test_wrong_token_rejected(self):
        a = self._mk_a(); inv_service.create_invitation(a, "T", "t@example.com")
        with self.assertRaises(inv_service.InvitationError): inv_service.verify_token("garbage")
