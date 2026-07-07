import logging

from app.tasks.celery_app import celery_app

log = logging.getLogger("app.tasks.email")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, name="send_verification_email")
def send_verification_email(self, *, email: str, username: str, raw_token: str) -> None:
    """Dev-mode mailer: logs the verification link instead of sending real mail.

    Swapping to real SMTP later only touches this function's body -
    nothing upstream (AuthService, the route) needs to change.
    """
    verify_url = f"http://localhost:8000/api/v1/auth/verify-email?token={raw_token}"
    log.info("verification_email_sent", extra={"to": email, "username": username})
    print(f"[email] To: {email}\nSubject: Verify your account\nVerify here: {verify_url}")
