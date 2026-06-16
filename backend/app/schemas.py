from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.db.models import ChatInviteStatus, ChatRole, TaskStatus


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_active: bool

    model_config = {"from_attributes": True}


class ChatCreateGroup(BaseModel):
    name: str
    member_ids: list[str]


class PrivateChatCreate(BaseModel):
    other_user_id: str


class ChatOut(BaseModel):
    id: str
    name: str | None
    is_group: bool
    display_name: str
    member_ids: list[str]
    member_names: list[str]
    membership_status: str
    pending_invite_id: str | None = None


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    reply_to_message_id: str | None = None


class MessageUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class MessageOut(BaseModel):
    id: str
    chat_id: str
    sender_id: str
    sender_name: str
    content: str
    created_at: datetime
    reply_to_message_id: str | None = None
    reply_to_preview: str | None = None
    reply_to_sender_name: str | None = None
    is_edited: bool = False
    is_deleted: bool = False

    model_config = {"from_attributes": True}


class ChatInviteActionOut(BaseModel):
    status: ChatInviteStatus


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    assignee_id: str | None = None
    is_shared: bool = False
    planned_hours: float | None = None
    due_date: date | None = None
    extra: dict[str, Any] | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee_id: str | None = None
    is_shared: bool | None = None
    planned_hours: float | None = None
    actual_hours: float | None = None
    due_date: date | None = None
    status: TaskStatus | None = None
    extra: dict[str, Any] | None = None


class TaskOut(BaseModel):
    id: str
    title: str
    description: str | None
    created_by: str
    assignee_id: str | None
    is_shared: bool
    planned_hours: float | None
    actual_hours: float | None
    due_date: date | None
    status: TaskStatus
    extra: dict[str, Any] | None

    model_config = {"from_attributes": True}


class WorklogCreate(BaseModel):
    user_id: str
    task_id: str | None = None
    work_date: date
    hours: float = Field(gt=0, le=24)
    details: str | None = None


class WorklogUpdate(BaseModel):
    task_id: str | None = None
    work_date: date | None = None
    hours: float | None = Field(default=None, gt=0, le=24)
    details: str | None = None


class WorklogOut(BaseModel):
    id: str
    user_id: str
    task_id: str | None
    work_date: date
    hours: float
    details: str | None
    created_by: str

    model_config = {"from_attributes": True}


class WorklogPermissionCreate(BaseModel):
    editor_id: str
    can_edit: bool = True


class NoteCreate(BaseModel):
    title: str
    content: str
    is_shared: bool = False


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    is_shared: bool | None = None


class NoteOut(BaseModel):
    id: str
    title: str
    content: str
    owner_id: str
    is_shared: bool

    model_config = {"from_attributes": True}


class NoteShareRequest(BaseModel):
    user_id: str
    can_edit: bool = False


class ChatMemberOut(BaseModel):
    user_id: str
    role: ChatRole

    model_config = {"from_attributes": True}
