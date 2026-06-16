from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Note, NoteAccess, User
from app.db.session import get_db
from app.schemas import NoteCreate, NoteOut, NoteShareRequest, NoteUpdate

router = APIRouter()


def _get_note_for_user(db: Session, note_id: str, user_id: str) -> Note | None:
    stmt = select(Note).where(Note.id == note_id)
    note = db.scalar(stmt)
    if not note:
        return None

    if note.owner_id == user_id or note.is_shared:
        return note

    access = db.scalar(select(NoteAccess).where(NoteAccess.note_id == note_id, NoteAccess.user_id == user_id))
    if access:
        return note

    return None


def _can_edit_note(db: Session, note: Note, user_id: str) -> bool:
    if note.owner_id == user_id:
        return True

    access = db.scalar(
        select(NoteAccess).where(
            NoteAccess.note_id == note.id,
            NoteAccess.user_id == user_id,
            NoteAccess.can_edit.is_(True),
        )
    )
    return access is not None


@router.post("", response_model=NoteOut)
def create_note(
    payload: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Note:
    note = Note(title=payload.title, content=payload.content, owner_id=current_user.id, is_shared=payload.is_shared)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("", response_model=list[NoteOut])
def list_notes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Note]:
    access_subq = select(NoteAccess.note_id).where(NoteAccess.user_id == current_user.id)
    stmt = select(Note).where(or_(Note.owner_id == current_user.id, Note.is_shared.is_(True), Note.id.in_(access_subq)))
    return list(db.scalars(stmt.order_by(Note.updated_at.desc())).all())


@router.patch("/{note_id}", response_model=NoteOut)
def update_note(
    note_id: str,
    payload: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Note:
    note = _get_note_for_user(db, note_id, current_user.id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    if not _can_edit_note(db, note, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No edit access")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, key, value)

    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}")
def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    note = db.scalar(select(Note).where(Note.id == note_id))
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    if note.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can delete note")

    db.delete(note)
    db.commit()
    return {"status": "deleted"}


@router.post("/{note_id}/share")
def share_note(
    note_id: str,
    payload: NoteShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    note = db.scalar(select(Note).where(Note.id == note_id))
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    if note.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can share note")

    access = db.scalar(select(NoteAccess).where(and_(NoteAccess.note_id == note_id, NoteAccess.user_id == payload.user_id)))
    if access:
        access.can_edit = payload.can_edit
    else:
        db.add(NoteAccess(note_id=note_id, user_id=payload.user_id, can_edit=payload.can_edit))

    db.commit()
    return {"status": "shared"}
