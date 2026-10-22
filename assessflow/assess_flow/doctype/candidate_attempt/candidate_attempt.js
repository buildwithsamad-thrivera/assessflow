frappe.ui.form.on('Candidate Attempt', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1) {

            // Re-run Auto Evaluation Button
            frm.add_custom_button(__('Re-run Auto Evaluation'), function() {
                frappe.confirm('Are you sure you want to re-run automatic evaluation? This will overwrite existing auto-graded marks and recalculate the total score.', () => {
                    frappe.call({
                        method: 'assessflow.api.admin.rerun_auto_evaluation',
                        args: { attempt_name: frm.doc.name },
                        freeze: true,
                        freeze_message: "Re-evaluating...",
                        callback: function(r) {
                            if (r.message && r.message.ok) {
                                frappe.show_alert({
                                    message: `Evaluation complete. New Score: ${r.message.new_score} (${r.message.new_percentage}%)`,
                                    indicator: 'green'
                                });
                                frm.reload_doc();
                            }
                        }
                    });
                });
            }).addClass('btn-warning');

            
            // Email Result Button
            frm.add_custom_button(__('Email Result to Candidate'), function() {
                frappe.call({
                    method: 'assessflow.api.admin.send_result_email',
                    args: { attempt_name: frm.doc.name },
                    freeze: true,
                    freeze_message: "Sending Email...",
                    callback: function(r) {
                        if (r.message && r.message.ok) {
                            frappe.show_alert({message: 'Result email sent!', indicator: 'green'});
                        }
                    }
                });
            }).addClass('btn-success');

            // Review & Regrade Button
            frm.add_custom_button(__('Review & Regrade'), function() {
                frappe.call({
                    method: 'assessflow.api.admin.get_attempt_answers',
                    args: { attempt_name: frm.doc.name },
                    callback: function(r) {
                        if (!r.message || !r.message.ok) return;
                        
                        let d = new frappe.ui.Dialog({
                            title: 'Review & Regrade Submission',
                            size: 'large',
                            fields: [{ fieldtype: 'HTML', fieldname: 'answers_area' }],
                            primary_action_label: 'Save Grades',
                            primary_action: function() {
                                let grades = {};
                                d.$wrapper.find('.af-mark-input').each(function() {
                                    let ans_name = $(this).data('ans');
                                    if (ans_name) grades[ans_name] = $(this).val();
                                });
                                
                                frappe.call({
                                    method: 'assessflow.api.admin.submit_batch_manual_grades',
                                    args: { attempt_name: frm.doc.name, grades: JSON.stringify(grades) },
                                    callback: function(res) {
                                        if (res.message && res.message.ok) {
                                            frappe.show_alert({message: `Grades saved. New Score: ${res.message.new_score} (${res.message.new_percentage}%)`, indicator: 'green'});
                                            d.hide();
                                            frm.reload_doc();
                                        }
                                    }
                                });
                            }
                        });
                        
                        let html = '<div style="display:flex;flex-direction:column;gap:16px;">';
                        r.message.answers.forEach((a, i) => {
                            let badge = a.needs_manual ? '<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:4px;font-size:11px;margin-left:8px;font-weight:bold;">Needs Review</span>' : '';
                            
                            html += `<div style="border:1px solid #e2e8f0;border-radius:8px;padding:16px;background:#fff;">
                                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
                                    <div>
                                        <h5 style="margin:0 0 4px;font-size:14px;">Q${i+1}. ${a.question} ${badge}</h5>
                                        <div style="font-size:12px;color:#64748b;">${a.type} | Max Marks: ${a.max_marks}</div>
                                    </div>
                                    <div style="display:flex;align-items:center;gap:8px;">
                                        <label style="font-size:12px;font-weight:bold;color:#64748b;">Awarded:</label>
                                        <input type="number" step="0.5" min="0" max="${a.max_marks}" 
                                               class="form-control af-mark-input" 
                                               style="width:80px;" 
                                               data-ans="${a.answer_name}" 
                                               value="${a.awarded}">
                                    </div>
                                </div>
                                <div style="background:#f8fafc;padding:12px;border-radius:6px;font-family:monospace;font-size:13px;white-space:pre-wrap;border:1px solid #e2e8f0;color:#1e293b;">${frappe.utils.escape_html(a.answer)}</div>
                            </div>`;
                        });
                        html += '</div>';
                        
                        d.fields_dict.answers_area.$wrapper.html(html);
                        d.show();
                    }
                });
            }).addClass('btn-primary');
        }
    }
});
