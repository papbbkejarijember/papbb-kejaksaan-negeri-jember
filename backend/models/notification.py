from typing import Literal

from pydantic import BaseModel, Field


NotificationChannel = Literal["email", "whatsapp"]


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
    status: Literal["simulated", "submitted", "failed"]
    provider: str
    provider_message_id: str | None = None
    event: str | None = None
    error: str | None = None
    created_at: str


class NotificationTestResponse(BaseModel):
    status: str
    notifications: list[Notification]


class NotificationConfig(BaseModel):
    email_mode: Literal["brevo", "mock"]
    whatsapp_mode: Literal["mock"]
    sender_email: str | None = None
