app_name = "assessflow"
app_title = "Assess Flow"
app_publisher = "Abdus Samad"
app_description = "Production assessment platform"
app_email = "samadmalik04@gmail.com"
app_license = "mit"

after_install = "assessflow.services.setup.after_install"

doc_events = {
    "Assessment Invitation": {
        "before_insert": "assessflow.services.invitation.on_invitation_before_insert",
        "validate": "assessflow.services.invitation.on_invitation_validate",
    },
    "Candidate Attempt": {
        "validate": "assessflow.services.attempt.on_attempt_validate",
        "on_update": "assessflow.services.attempt.on_attempt_updated",
    },
}

scheduler_events = {
    "cron": {
        "*/5 * * * *": ["assessflow.services.attempt.expire_stale_attempts"],
    },
}

has_permission = {
    "Assessment Invitation": "assessflow.services.permissions.invitation_has_permission",
    "Candidate Attempt": "assessflow.services.permissions.attempt_has_permission",
    "Candidate Answer": "assessflow.services.permissions.answer_has_permission",
    "Question Bank": "assessflow.services.permissions.question_has_permission",
}
