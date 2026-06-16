from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Chat, ChatMember, ChatRole, Message, User
from app.db.session import get_db
from app.schemas import ChatCreateGroup, ChatOut, MessageCreate, MessageOut, PrivateChatCreate

router = APIRouter()


def _is_member(db: Session, chat_id: str, user_id: str) -> bool:
    member = db.scalar(select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id))
    return member is not None


@router.post("/private", response_model=ChatOut)
def create_private_chat(
    payload: PrivateChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Chat:
    if payload.other_user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create private chat with self")

    other = db.scalar(select(User).where(User.id == payload.other_user_id))
    if not other:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

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
    return chat


@router.post("/groups", response_model=ChatOut)
def create_group_chat(
    payload: ChatCreateGroup,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Chat:
    unique_members = list(set(payload.member_ids + [current_user.id]))

    users_count = db.query(User).filter(User.id.in_(unique_members)).count()
    if users_count != len(unique_members):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more users do not exist")

    chat = Chat(name=payload.name, is_group=True)
    db.add(chat)
    db.flush()

    for user_id in unique_members:
        role = ChatRole.admin if user_id == current_user.id else ChatRole.member
        db.add(ChatMember(chat_id=chat.id, user_id=user_id, role=role))

    db.commit()
    db.refresh(chat)
    return chat


@router.get("", response_model=list[ChatOut])
def list_my_chats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Chat]:
    stmt = (
        select(Chat)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(ChatMember.user_id == current_user.id)
        .order_by(Chat.updated_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.post("/{chat_id}/messages", response_model=MessageOut)
def create_message(
    chat_id: str,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Message:
    if not _is_member(db, chat_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this chat")

    message = Message(chat_id=chat_id, sender_id=current_user.id, content=payload.content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get("/{chat_id}/messages", response_model=list[MessageOut])
def list_messages(
    chat_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Message]:
    if not _is_member(db, chat_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this chat")

    stmt = select(Message).where(Message.chat_id == chat_id).order_by(Message.created_at.asc())
    return list(db.scalars(stmt).all())
