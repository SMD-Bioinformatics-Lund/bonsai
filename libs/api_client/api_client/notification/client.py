"""API interface for the notification service."""

import logging
from http import HTTPStatus
from api_client.core.base import BaseClient
from api_client.core.exceptions import HTTPException
from .models import EmailCreate

LOG = logging.getLogger(__name__)

class NotificationClient(BaseClient):
    """Send emails to notify users of evets."""

    def send_email(self, email: EmailCreate) -> bool:
        """Send an email."""

        payload = email.model_dump(mode="json")
        try:
            self.post("/send-email", payload=payload, expected_status=HTTPStatus.OK)
        except HTTPException as exc:
            LOG.error("Something went wrong when sending an email; %s", exc, extra={"payload": payload})
