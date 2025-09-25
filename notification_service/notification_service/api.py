"""API entrypoints"""

from fastapi import APIRouter, Depends, Request

# from .dispatcher import dispatch_email_job
from .config import Settings
from .models import EmailApiInput
from .services import email
from .services.templates import TemplateRepository
from .version import __version__ as version

router = APIRouter()


def get_settings() -> Settings:
    """Get settings instance."""
    return Settings()


def get_template_repo(request: Request) -> TemplateRepository:
    """Get template repo instance stored in app state."""
    return request.app.state.template_repo


@router.get("/")
def root() -> dict[str, str]:
    """Display basic welcome message."""

    return {"message": "Welcome to the notification service API", "version": version}


@router.post("/send-email")
def send_email(
    request: EmailApiInput,
    settings: Settings = Depends(get_settings),
    repo: TemplateRepository = Depends(get_template_repo),
):
    """Send email."""

    if settings.use_redis:
        raise NotImplementedError("Dispatching email jobs is not finished!")
        # dispatch_email_job(**request.model_dump())
    smtp_conn = email.get_smtp_connection(settings.smtp)
    email.send_email(
        settings.sender_email,
        settings.sender_name,
        message_obj=request,
        smtp_conn=smtp_conn,
        template_repo=repo,
    )
