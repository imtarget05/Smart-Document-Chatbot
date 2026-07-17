from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RoutingContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    task_type: str | None = None
    document_count: int = Field(default=0, ge=0)
    page_count: int = Field(default=0, ge=0)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    has_image: bool = False
    attachments: list[str | dict[str, Any]] = Field(default_factory=list)
    request_id: str | None = None


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[dict[str, Any]] = ""
    images: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str | None = None
    messages: list[ChatMessage] = Field(min_length=1)
    stream: bool = False
    options: dict[str, Any] = Field(default_factory=dict)
    routing: RoutingContext = Field(default_factory=RoutingContext)


class RouteDecision(BaseModel):
    provider: Literal["local", "openrouter", "nvidia"]
    model: str
    reason: str
    task_type: str
    escalated: bool = False

