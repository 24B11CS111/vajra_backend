from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.dependencies.auth import get_current_db_user
from app.models.user import User
from app.models.planner import PlannerTask
from app.schemas.planner import TaskCreate, TaskUpdate, TaskResponse, TaskReorder

router = APIRouter()

@router.get("/tasks", response_model=List[TaskResponse])
def get_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    return db.query(PlannerTask).filter(PlannerTask.user_id == current_user.id).order_index_by().all() if hasattr(db.query(PlannerTask), "order_index_by") else db.query(PlannerTask).filter(PlannerTask.user_id == current_user.id).order_by(PlannerTask.order_index.asc(), PlannerTask.created_at.desc()).all()

@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    task = PlannerTask(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        category=data.category,
        priority=data.priority,
        is_completed=data.is_completed,
        order_index=data.order_index,
        due_date=data.due_date,
        subtasks=data.subtasks or []
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@router.get("/tasks/{id}", response_model=TaskResponse)
def get_task(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    task = db.query(PlannerTask).filter(PlannerTask.id == id, PlannerTask.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.put("/tasks/{id}", response_model=TaskResponse)
def update_task(
    id: UUID,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    task = db.query(PlannerTask).filter(PlannerTask.id == id, PlannerTask.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(task, field, val)
        
    db.commit()
    db.refresh(task)
    return task

@router.post("/tasks/{id}/toggle", response_model=TaskResponse)
def toggle_task_completion(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    task = db.query(PlannerTask).filter(PlannerTask.id == id, PlannerTask.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.is_completed = not task.is_completed
    db.commit()
    db.refresh(task)
    return task

@router.delete("/tasks/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    task = db.query(PlannerTask).filter(PlannerTask.id == id, PlannerTask.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return None

@router.post("/tasks/reorder", status_code=status.HTTP_200_OK)
def reorder_tasks(
    data: TaskReorder,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    for idx, task_id in enumerate(data.task_ids):
        db.query(PlannerTask).filter(PlannerTask.id == task_id, PlannerTask.user_id == current_user.id).update({"order_index": idx})
    db.commit()
    return {"status": "ok", "message": "Tasks reordered"}
