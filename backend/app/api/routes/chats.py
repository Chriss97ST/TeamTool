from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Chat, ChatInvite, ChatInviteStatus, ChatMember, ChatRole, Message, MessageState, User
from app.db.session import get_db
from app.schemas import (
    ChatCreateGroup,
    ChatInviteActionOut,
    ChatOut,
    MessageCreate,
    MessageOut,
    MessageUpdate,
    PrivateChatCreate,
)

router = APIRouter()


def _get_member(db: Session, chat_id: str, user_id: str) -> ChatMember | None:
    return db.scalar(select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id))


def _require_active_member(db: Session, chat_id: str, user_id: str) -> ChatMember:
    member = _get_member(db, chat_id, user_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this chat")
    return member


def _get_pending_invite(db: Session, chat_id: str, user_id: str) -> ChatInvite | None:
    return db.scalar(
        select(ChatInvite).where(
            ChatInvite.chat_id == chat_id,
            ChatInvite.user_id == user_id,
            ChatInvite.status == ChatInviteStatus.pending,
        )
    )


def _serialize_chat(db: Session, chat: Chat, current_user_id: str) -> ChatOut:
    members = list(
        db.scalars(
            select(User)
            .join(ChatMember, ChatMember.user_id == User.id)
            .where(ChatMember.chat_id == chat.id)
            .order_by(User.full_name.asc())
        ).all()
    )
    member_ids = [member.id for member in members]
    member_names = [member.full_name for member in members]
    pending_invite = _get_pending_invite(db, chat.id, current_user_id)
    is_member = current_user_id in member_ids

    if chat.is_group:
        display_name = chat.name or ", ".join(member_names)
    else:
        other_member = next((member for member in members if member.id != current_user_id), None)
        display_name = other_member.full_name if other_member else "Privatchat"

    return ChatOut(
        id=chat.id,
        name=chat.name,
        is_group=chat.is_group,
        display_name=display_name,
        member_ids=member_ids,
        member_names=member_names,
        membership_status="active" if is_member else "pending",
        pending_invite_id=pending_invite.id if pending_invite else None,
    )


def _serialize_message(db: Session, message: Message) -> MessageOut:
    sender = db.scalar(select(User).where(User.id == message.sender_id))
    state = db.scalar(select(MessageState).where(MessageState.message_id == message.id))

    reply_to_message_id = state.reply_to_message_id if state else None
    reply_to_preview = None
    reply_to_sender_name = None
    if reply_to_message_id:
        reply_message = db.scalar(select(Message).where(Message.id == reply_to_message_id))
        reply_state = db.scalar(select(MessageState).where(MessageState.message_id == reply_to_message_id))
        if reply_message:
            reply_sender = db.scalar(select(User).where(User.id == reply_message.sender_id))
            reply_to_sender_name = reply_sender.full_name if reply_sender else reply_message.sender_id
            if reply_state and reply_state.is_deleted:
                reply_to_preview = "Nachricht geloescht"
            else:
                reply_content = reply_state.edited_content if reply_state and reply_state.edited_content else reply_message.content
                reply_to_preview = reply_content[:120]

    is_deleted = bool(state and state.is_deleted)
    content = "Nachricht geloescht" if is_deleted else (state.edited_content if state and state.edited_content else message.content)

    return MessageOut(
        id=message.id,
        chat_id=message.chat_id,
        sender_id=message.sender_id,
        sender_name=sender.full_name if sender else message.sender_id,
        content=content,
        created_at=message.created_at,
        reply_to_message_id=reply_to_message_id,
        reply_to_preview=reply_to_preview,
        reply_to_sender_name=reply_to_sender_name,
        is_edited=bool(state and state.edited_content and not state.is_deleted),
        is_deleted=is_deleted,
    )


def _find_existing_private_chat(db: Session, current_user_id: str, other_user_id: str) -> Chat | None:
    stmt = (
        select(Chat)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(Chat.is_group.is_(False), ChatMember.user_id.in_([current_user_id, other_user_id]))
        .group_by(Chat.id)
        .having(func.count(ChatMember.user_id) == 2)
    )
    return db.scalar(stmt)


def _touch_chat(db: Session, chat_id: str) -> None:
    chat = db.scalar(select(Chat).where(Chat.id == chat_id))
    if chat:
        chat.updated_at = datetime.now(timezone.utc)


@router.post("/private", response_model=ChatOut)
def create_private_chat(
    payload: PrivateChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatOut:
    if payload.other_user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create private chat with self")

    other = db.scalar(select(User).where(User.id == payload.other_user_id))
    if not other:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    existing_chat = _find_existing_private_chat(db, current_user.id, other.id)
    if existing_chat:
        return _serialize_chat(db, existing_chat, current_user.id)

    chat = Chat(is_group=False)
    db.add(chat)
    db.flush()
    db.add_all(
        [
            ChatMember(chat_id=chat.id, user_id=current_user.id, role=ChatRole.member),
            ChatMember(chat_id=chat.id, user_id=other.id, role=ChatRole.member),
        ]
    )
    db.commit()
    db.refresh(chat)
    return _serialize_chat(db, chat, current_user.id)


@router.post("/groups", response_model=ChatOut)
def create_group_chat(
    payload: ChatCreateGroup,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatOut:
    invited_user_ids = list(set(payload.member_ids) - {current_user.id})
    unique_users = invited_user_ids + [current_user.id]
    users_count = db.query(User).filter(User.id.in_(unique_users)).count()
    if users_count != len(unique_users):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more users do not exist")

    chat = Chat(name=payload.name, is_group=True)
    db.add(chat)
    db.flush()
    db.add(ChatMember(chat_id=chat.id, user_id=current_user.id, role=ChatRole.admin))
    for user_id in invited_user_ids:
        db.add(ChatInvite(chat_id=chat.id, user_id=user_id, invited_by=current_user.id, status=ChatInviteStatus.pending))
    db.commit()
    db.refresh(chat)
    return _serialize_chat(db, chat, current_user.id)


@router.get("", response_model=list[ChatOut])
def list_my_chats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[ChatOut]:
    active_stmt = (
        select(Chat)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(ChatMember.user_id == current_user.id)
        .order_by(Chat.updated_at.desc())
    )
    pending_stmt = (
        select(Chat)
        .join(ChatInvite, ChatInvite.chat_id == Chat.id)
        .where(ChatInvite.user_id == current_user.id, ChatInvite.status == ChatInviteStatus.pending)
        .order_by(Chat.updated_at.desc())
    )
    chats = {chat.id: chat for chat in [*list(db.scalars(active_stmt).all()), *list(db.scalars(pending_stmt).all())]}
    return [_serialize_chat(db, chat, current_user.id) for chat in chats.values()]


@router.post("/invites/{invite_id}/accept", response_model=ChatInviteActionOut)
def accept_group_invite(
    invite_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatInviteActionOut:
    invite = db.scalar(select(ChatInvite).where(ChatInvite.id == invite_id, ChatInvite.user_id == current_user.id))
    if not invite or invite.status != ChatInviteStatus.pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending invite not found")

    if not _get_member(db, invite.chat_id, current_user.id):
        db.add(ChatMember(chat_id=invite.chat_id, user_id=current_user.id, role=ChatRole.member))
    invite.status = ChatInviteStatus.accepted
    _touch_chat(db, invite.chat_id)
    db.commit()
    return ChatInviteActionOut(status=invite.status)


@router.post("/invites/{invite_id}/decline", response_model=ChatInviteActionOut)
def decline_group_invite(
    invite_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatInviteActionOut:
    invite = db.scalar(select(ChatInvite).where(ChatInvite.id == invite_id, ChatInvite.user_id == current_user.id))
    if not invite or invite.status != ChatInviteStatus.pending:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending invite not found")

    invite.status = ChatInviteStatus.declined
    db.commit()
    return ChatInviteActionOut(status=invite.status)


@router.delete("/{chat_id}")
def delete_private_chat(
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    chat = db.scalar(select(Chat).where(Chat.id == chat_id))
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    if chat.is_group:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use leave for group chats")

    db.delete(_require_active_member(db, chat_id, current_user.id))
    db.flush()
    if db.query(ChatMember).filter(ChatMember.chat_id == chat_id).count() == 0:
        db.delete(chat)
    db.commit()
    return {"status": "deleted"}


@router.post("/{chat_id}/leave")
def leave_group_chat(
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    chat = db.scalar(select(Chat).where(Chat.id == chat_id))
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    if not chat.is_group:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Private chats can be deleted instead")

    member = _get_member(db, chat_id, current_user.id)
    invite = _get_pending_invite(db, chat_id, current_user.id)
    if member:
        db.delete(member)
    elif invite:
        invite.status = ChatInviteStatus.declined
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

    if db.query(ChatMember).filter(ChatMember.chat_id == chat_id).count() == 0:
        db.delete(chat)
    db.commit()
    return {"status": "left"}


@router.post("/{chat_id}/messages", response_model=MessageOut)
def create_message(
    chat_id: str,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageOut:
    _require_active_member(db, chat_id, current_user.id)
    if payload.reply_to_message_id and not db.scalar(
        select(Message).where(Message.id == payload.reply_to_message_id, Message.chat_id == chat_id)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reply target not found")

    message = Message(chat_id=chat_id, sender_id=current_user.id, content=payload.content)
    db.add(message)
    db.flush()
    if payload.reply_to_message_id:
        db.add(MessageState(message_id=message.id, reply_to_message_id=payload.reply_to_message_id))
    _touch_chat(db, chat_id)
    db.commit()
    db.refresh(message)
    return _serialize_message(db, message)


@router.patch("/messages/{message_id}", response_model=MessageOut)
def update_message(
    message_id: str,
    payload: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageOut:
    message = db.scalar(select(Message).where(Message.id == message_id))
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    _require_active_member(db, message.chat_id, current_user.id)
    if message.sender_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only own messages can be edited")

    state = db.scalar(select(MessageState).where(MessageState.message_id == message_id))
    if not state:
        state = MessageState(message_id=message_id)
        db.add(state)
    if state.is_deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deleted messages cannot be edited")
    state.edited_content = payload.content
    _touch_chat(db, message.chat_id)
    db.commit()
    return _serialize_message(db, message)


@router.delete("/messages/{message_id}")
def delete_message(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    message = db.scalar(select(Message).where(Message.id == message_id))
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    _require_active_member(db, message.chat_id, current_user.id)
    if message.sender_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only own messages can be deleted")

    state = db.scalar(select(MessageState).where(MessageState.message_id == message_id))
    if not state:
        state = MessageState(message_id=message_id)
        db.add(state)
    state.is_deleted = True
    state.edited_content = None
    db.commit()
    return {"status": "deleted"}


@router.get("/{chat_id}/messages", response_model=list[MessageOut])
def list_messages(
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageOut]:
    _require_active_member(db, chat_id, current_user.id)
    messages = list(db.scalars(select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc())).all())
    return [_serialize_message(db, message) for message in messages]
