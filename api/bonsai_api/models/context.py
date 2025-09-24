from typing import Any
from pydantic import BaseModel, Field

from api_client.audit_log.models import Actor


class ApiRequestContext(BaseModel):
    """The context of a Bonsai API call."""

    actor: Actor
    metadata: dict[str, Any] = Field()


