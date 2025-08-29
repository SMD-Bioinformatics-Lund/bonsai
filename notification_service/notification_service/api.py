"""API entrypoints"""

from fastapi import APIRouter

from . import sender
from .config import settings
# from .dispatcher import dispatch_email_job
from .models import EmailApiInput
from .version import __version__ as version

router = APIRouter()


@router.get("/")
def root() -> dict[str, str]:
    """Display basic welcome message."""

    return {"message": "Welcome to the notification service API", "version": version}


@router.post("/send-email")
def send_email(request: EmailApiInput):
    """Send email."""

    if settings.use_redis:
        raise NotImplementedError("Dispatching email jobs is not finished!")
        # dispatch_email_job(**request.model_dump())
    sender.send_email(
        settings.sender_email, settings.sender_name, message_obj=request
    )
