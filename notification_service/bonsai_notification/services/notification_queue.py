from redis import Redis
from rq import Queue

# You can configure this via Pydantic settings if needed
redis_conn = Redis()
notification_queue = Queue("notification", connection=redis_conn)


def dispatch_email_job(
    recipient: str,
    subject: str,
    template_name: str,
    context: dict,
    job_id: str | None = None,
    ttl: int | None = None,
    result_ttl: int | None = None,
    retry: int | None = None,
):
    """
    Dispatch an email job to the notification queue.

    Parameters:
    - recipient: Email address of the recipient.
    - subject: Subject line of the email.
    - template_name: Name of the Jinja2 template to use.
    - context: Dictionary of variables to render in the template.
    - job_id: Optional custom job ID.
    - ttl: Time-to-live for the job in seconds.
    - result_ttl: How long to keep the result.
    - retry: Number of retry attempts (if using retry logic).
    """
    return notification_queue.enqueue(
        "email_notification_service.tasks.queue_send_email",
        recipient,
        subject,
        template_name,
        context,
        job_id=job_id,
        ttl=ttl,
        result_ttl=result_ttl,
        retry=retry,
    )
