from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User, WorkLog, WorklogPermission
from app.db.session import get_db
from app.schemas import WorklogCreate, WorklogOut, WorklogPermissionCreate, WorklogUpdate

router = APIRouter()


def _can_edit_user_logs(db: Session, actor_id: str, target_user_id: str) -> bool:
    if actor_id == target_user_id:
        return True

    perm = db.scalar(
        select(WorklogPermission).where(
            WorklogPermission.owner_id == target_user_id,
            WorklogPermission.editor_id == actor_id,
            WorklogPermission.can_edit.is_(True),
        )
    )
    return perm is not None


@router.post("/permissions")
def grant_worklog_permission(
    payload: WorklogPermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    perm = db.scalar(
        select(WorklogPermission).where(
            WorklogPermission.owner_id == current_user.id,
            WorklogPermission.editor_id == payload.editor_id,
        )
    )
    if perm:
        perm.can_edit = payload.can_edit
    else:
        perm = WorklogPermission(owner_id=current_user.id, editor_id=payload.editor_id, can_edit=payload.can_edit)
        db.add(perm)

    db.commit()
    return {"status": "ok"}


@router.post("", response_model=WorklogOut)
def create_worklog(
    payload: WorklogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkLog:
    if not _can_edit_user_logs(db, current_user.id, payload.user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission for this user")

    worklog = WorkLog(
        user_id=payload.user_id,
        task_id=payload.task_id,
        work_date=payload.work_date,
        hours=payload.hours,
        details=payload.details,
        created_by=current_user.id,
    )
    db.add(worklog)
    db.commit()
    db.refresh(worklog)
    return worklog


@router.patch("/{worklog_id}", response_model=WorklogOut)
def update_worklog(
    worklog_id: str,
    payload: WorklogUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkLog:
    worklog = db.scalar(select(WorkLog).where(WorkLog.id == worklog_id))
    if not worklog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worklog not found")

    if not _can_edit_user_logs(db, current_user.id, worklog.user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission for this user")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(worklog, key, value)

    db.commit()
    db.refresh(worklog)
    return worklog


@router.delete("/{worklog_id}")
def delete_worklog(
    worklog_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    worklog = db.scalar(select(WorkLog).where(WorkLog.id == worklog_id))
    if not worklog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worklog not found")

    if not _can_edit_user_logs(db, current_user.id, worklog.user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission for this user")

    db.delete(worklog)
    db.commit()
    return {"status": "deleted"}


@router.get("/week", response_model=list[WorklogOut])
def list_week(
    week_start: str = Query(..., description="ISO date, example: 2026-06-15"),
    user_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkLog]:
    from datetime import date

    start = date.fromisoformat(week_start)
    end = start + timedelta(days=6)
    target_user = user_id or current_user.id

    if not _can_edit_user_logs(db, current_user.id, target_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission for this user")

    stmt = select(WorkLog).where(
        and_(WorkLog.user_id == target_user, WorkLog.work_date >= start, WorkLog.work_date <= end)
    )
    return list(db.scalars(stmt.order_by(WorkLog.work_date.asc())).all())
