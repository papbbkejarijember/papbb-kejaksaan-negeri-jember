from typing import Literal

from pydantic import BaseModel, Field


NotificationChannel = Literal["email", "whatsapp"]
NotificationStatus = Literal[
    "simulated", "submitted", "delivered", "opened", "soft_bounce",
    "hard_bounce", "blocked", "invalid", "failed"
]


class NotificationStatusEvent(BaseModel):
    status: NotificationStatus
    provider_event: str | None = None
    at: str
    provider_ts: str | int | float | None = None


class NotificationTestCreate(BaseModel):
    channels: list[NotificationChannel] = Field(min_length=1)
    subject: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=2000)


class Notification(BaseModel):
    id: str
    user_id: str
    channel: NotificationChannel
    subject: str
    message: str
    status: NotificationStatus
    provider: str
    provider_message_id: str | None = None
    event: str | None = None
    error: str | None = None
    status_history: list[NotificationStatusEvent] = Field(default_factory=list)
    updated_at: str | None = None
    created_at: str


class NotificationTestResponse(BaseModel):
    status: str
    notifications: list[Notification]


class NotificationConfig(BaseModel):
    email_mode: Literal["brevo", "mock"]
    whatsapp_mode: Literal["mock"]
    sender_email: str | None = None


class NotificationHistoryResponse(BaseModel):
    status: NotificationStatus
    history: list[NotificationStatusEvent]
