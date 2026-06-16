from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Task, User
from app.db.session import get_db
from app.schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter()


@router.post("", response_model=TaskOut)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    task = Task(
        title=payload.title,
        description=payload.description,
        created_by=current_user.id,
        assignee_id=payload.assignee_id,
        is_shared=payload.is_shared,
        planned_hours=payload.planned_hours,
        due_date=payload.due_date,
        extra=payload.extra,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Task]:
    stmt = select(Task).where(
        or_(
            Task.created_by == current_user.id,
            Task.assignee_id == current_user.id,
            Task.is_shared.is_(True),
        )
    )
    return list(db.scalars(stmt.order_by(Task.created_at.desc())).all())


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    task = db.scalar(select(Task).where(Task.id == task_id))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if current_user.id not in [task.created_by, task.assignee_id]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No edit access")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task
