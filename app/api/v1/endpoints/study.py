from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.dependencies.auth import get_current_db_user
from app.models.user import User
from app.models.study import SubjectModel, AssignmentModel
from app.schemas.study import (
    SubjectCreate, SubjectUpdate, SubjectResponse,
    AssignmentCreate, AssignmentUpdate, AssignmentResponse,
)

router = APIRouter()

# --- SUBJECTS CRUD ---

@router.get("/subjects", response_model=List[SubjectResponse])
def get_subjects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    return db.query(SubjectModel).filter(SubjectModel.user_id == current_user.id).order_by(SubjectModel.name.asc()).all()

@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(
    data: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    subject = SubjectModel(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        color=data.color,
        priority=data.priority,
        exam_date=data.exam_date,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject

@router.get("/subjects/{id}", response_model=SubjectResponse)
def get_subject(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    subject = db.query(SubjectModel).filter(SubjectModel.id == id, SubjectModel.user_id == current_user.id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject

@router.put("/subjects/{id}", response_model=SubjectResponse)
def update_subject(
    id: UUID,
    data: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    subject = db.query(SubjectModel).filter(SubjectModel.id == id, SubjectModel.user_id == current_user.id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(subject, field, val)
        
    db.commit()
    db.refresh(subject)
    return subject

@router.delete("/subjects/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    subject = db.query(SubjectModel).filter(SubjectModel.id == id, SubjectModel.user_id == current_user.id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    db.delete(subject)
    db.commit()
    return None

# --- ASSIGNMENTS CRUD ---

@router.get("/assignments", response_model=List[AssignmentResponse])
def get_assignments(
    subject_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    query = db.query(AssignmentModel).filter(AssignmentModel.user_id == current_user.id)
    if subject_id:
        query = query.filter(AssignmentModel.subject_id == subject_id)
    if status_filter:
        query = query.filter(AssignmentModel.status == status_filter)
    return query.order_by(AssignmentModel.due_date.asc().nulls_last(), AssignmentModel.created_at.desc()).all()

@router.post("/assignments", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    data: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    # Resolve subject name if subject_id provided
    subj_name = data.subject_name
    if data.subject_id:
        subj = db.query(SubjectModel).filter(SubjectModel.id == data.subject_id, SubjectModel.user_id == current_user.id).first()
        if subj:
            subj_name = subj.name

    assignment = AssignmentModel(
        user_id=current_user.id,
        subject_id=data.subject_id,
        subject_name=subj_name,
        title=data.title,
        description=data.description,
        due_date=data.due_date,
        due_time=data.due_time,
        priority=data.priority,
        status=data.status,
        attachment_url=data.attachment_url,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment

@router.get("/assignments/{id}", response_model=AssignmentResponse)
def get_assignment(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    assignment = db.query(AssignmentModel).filter(AssignmentModel.id == id, AssignmentModel.user_id == current_user.id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment

@router.put("/assignments/{id}", response_model=AssignmentResponse)
def update_assignment(
    id: UUID,
    data: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    assignment = db.query(AssignmentModel).filter(AssignmentModel.id == id, AssignmentModel.user_id == current_user.id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    update_data = data.model_dump(exclude_unset=True)
    if "subject_id" in update_data and update_data["subject_id"]:
        subj = db.query(SubjectModel).filter(SubjectModel.id == update_data["subject_id"], SubjectModel.user_id == current_user.id).first()
        if subj:
            update_data["subject_name"] = subj.name

    for field, val in update_data.items():
        setattr(assignment, field, val)
        
    db.commit()
    db.refresh(assignment)
    return assignment

@router.post("/assignments/{id}/toggle", response_model=AssignmentResponse)
def toggle_assignment_status(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    assignment = db.query(AssignmentModel).filter(AssignmentModel.id == id, AssignmentModel.user_id == current_user.id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    if assignment.status == "COMPLETED":
        assignment.status = "NOT_STARTED"
    else:
        assignment.status = "COMPLETED"
        
    db.commit()
    db.refresh(assignment)
    return assignment

@router.delete("/assignments/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    assignment = db.query(AssignmentModel).filter(AssignmentModel.id == id, AssignmentModel.user_id == current_user.id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(assignment)
    db.commit()
    return None
