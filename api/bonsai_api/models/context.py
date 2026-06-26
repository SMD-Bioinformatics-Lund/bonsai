from typing import Any
    
from bonsai_libs.api_client.audit_log.models import Actor
from pydantic import BaseModel, Field


class ApiRequestContext(BaseModel):
    """The context of a Bonsai API call."""

    actor: Actor
    metadata: dict[str, Any] = Field()
