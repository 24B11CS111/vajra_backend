from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.db.session import get_db
from app.dependencies.auth import get_current_db_user
from app.models.user import User
from app.models.calendar import CalendarEventModel
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate, CalendarEventResponse

router = APIRouter()

@router.get("/events", response_model=List[CalendarEventResponse])
def get_events(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    event_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    query = db.query(CalendarEventModel).filter(CalendarEventModel.user_id == current_user.id)
    if start_date:
        query = query.filter(CalendarEventModel.start_time >= start_date)
    if end_date:
        query = query.filter(CalendarEventModel.start_time <= end_date)
    if event_type:
        query = query.filter(CalendarEventModel.event_type == event_type)
    return query.order_by(CalendarEventModel.start_time.asc()).all()

@router.post("/events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    data: CalendarEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    event = CalendarEventModel(
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        event_type=data.event_type,
        start_time=data.start_time,
        end_time=data.end_time,
        is_all_day=data.is_all_day,
        location=data.location,
        color=data.color,
        status=data.status,
        related_id=data.related_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

@router.get("/events/{id}", response_model=CalendarEventResponse)
def get_event(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    event = db.query(CalendarEventModel).filter(CalendarEventModel.id == id, CalendarEventModel.user_id == current_user.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.put("/events/{id}", response_model=CalendarEventResponse)
def update_event(
    id: UUID,
    data: CalendarEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    event = db.query(CalendarEventModel).filter(CalendarEventModel.id == id, CalendarEventModel.user_id == current_user.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(event, field, val)
        
    db.commit()
    db.refresh(event)
    return event

@router.delete("/events/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user),
):
    event = db.query(CalendarEventModel).filter(CalendarEventModel.id == id, CalendarEventModel.user_id == current_user.id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()
    return None
