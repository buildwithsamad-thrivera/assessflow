frappe.ui.form.on('Assessment Invitation', {
    refresh: function(frm) {
        // Your highly professional condition:
        if (frm.doc.status === 'Active' && frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Resend Invitation Email'), function() {
                frappe.confirm('This will generate a NEW secure link and invalidate the old one. Send?', () => {
                    frappe.call({
                        method: 'assessflow.api.admin.resend_invitation',
                        args: { invitation_name: frm.doc.name },
                        freeze: true,
                        freeze_message: "Sending Email...",
                        callback: function(r) {
                            if (r.message && r.message.ok) {
                                frappe.show_alert({message: 'Email sent successfully!', indicator: 'green'});
                                frm.reload_doc();
                            }
                        }
                    });
                });
            }).addClass('btn-primary');
        }
    }
});
