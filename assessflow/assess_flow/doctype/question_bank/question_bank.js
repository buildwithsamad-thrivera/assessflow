frappe.ui.form.on('Question Bank', {
    refresh: function(frm) {
        if (frm.doc.question_type === 'Coding') {
            frm.add_custom_button(__('Test Code'), function() {
                let d = new frappe.ui.Dialog({
                    title: 'Test Code Execution',
                    size: 'large',
                    fields: [
                        { fieldtype: 'Code', fieldname: 'candidate_code', label: 'Your Code', options: frm.doc.coding_language === 'javascript' ? 'JavaScript' : (frm.doc.coding_language === 'html' ? 'HTML' : 'Python'), default: frm.doc.starter_code || '' },
                        { fieldtype: 'HTML', fieldname: 'results_area', label: 'Results' }
                    ],
                    primary_action_label: 'Run Test Cases',
                    primary_action: function() {
                        let code = d.get_value('candidate_code');
                        d.fields_dict.results_area.$wrapper.html('<div style="padding:20px;text-align:center;">Running...</div>');
                        frappe.call({
                            method: 'assessflow.api.admin.test_question_code',
                            args: { question_name: frm.doc.name, code: code },
                            callback: function(r) {
                                if (!r.message || !r.message.ok) {
                                    d.fields_dict.results_area.$wrapper.html(`<div style="color:red">${r.message.error || 'Error'}</div>`);
                                    return;
                                }
                                let html = '<div style="margin-top:15px">';
                                r.message.results.forEach((t, i) => {
                                    let color = t.passed ? '#16a34a' : '#dc2626';
                                    let icon = t.passed ? '✓' : '✗';
                                    let badge = t.is_hidden ? '<span style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:11px;margin-left:8px">Hidden</span>' : '';
                                    html += `<div style="border:1px solid #e2e8f0;border-radius:8px;padding:12px;margin-bottom:10px;">
                                        <div style="font-weight:bold;color:${color};margin-bottom:6px;">${icon} ${t.description} ${badge}</div>`;
                                    if (!t.passed) {
                                        html += `<div style="background:#fef2f2;padding:8px;border-radius:4px;font-family:monospace;font-size:12px;">
                                            <div><strong>Expected:</strong> ${t.expected || ''}</div>
                                            <div><strong>Got:</strong> ${t.got || ''}</div>
                                            <div style="color:red"><strong>Error:</strong> ${t.stderr || ''}</div>
                                        </div>`;
                                    }
                                    html += `</div>`;
                                });
                                html += '</div>';
                                d.fields_dict.results_area.$wrapper.html(html);
                            }
                        });
                    }
                });
                d.show();
            }).addClass('btn-primary');
        }
    }
});
