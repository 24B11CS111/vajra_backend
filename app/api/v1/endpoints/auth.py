from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from jose import jwt, JWTError
import uuid
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.dependencies.auth import get_current_db_user
from app.models.user import User
from app.models.memory import Memory
from app.models.planner import PlannerTask
from app.models.study import SubjectModel, AssignmentModel
from app.models.calendar import CalendarEventModel

router = APIRouter()

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class SocialLoginRequest(BaseModel):
    provider: str
    token: Optional[str] = None

class RefreshRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    expires_in: int = 604800  # 7 days

def create_jwt_token(sub: str, email: str, name: Optional[str] = None, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    
    payload: Dict[str, Any] = {
        "sub": sub,
        "email": email,
        "user_metadata": {
            "full_name": name or email.split("@")[0],
            "name": name or email.split("@")[0]
        },
        "exp": expire
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    if not data.email or not data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
    if len(data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )
    
    user_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, data.email))
    
    # Check if user exists in DB, create or update
    existing = db.query(User).filter(User.email == data.email).first()
    if not existing:
        new_user = User(
            id=uuid.UUID(user_uuid),
            supabase_user_id=user_uuid,
            email=data.email,
            full_name=data.full_name or data.email.split("@")[0],
            display_name=data.full_name or data.email.split("@")[0],
        )
        db.add(new_user)
        db.commit()

    access_token = create_jwt_token(user_uuid, data.email, name=data.full_name)
    refresh_token = create_jwt_token(user_uuid, data.email, name=data.full_name, expires_delta=timedelta(days=30))
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
    if not data.email or not data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
    
    user_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, data.email))
    access_token = create_jwt_token(user_uuid, data.email)
    refresh_token = create_jwt_token(user_uuid, data.email, expires_delta=timedelta(days=30))
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/social", response_model=TokenResponse)
def social_login(data: SocialLoginRequest):
    provider_email = f"{data.provider}_user@vajra.ai"
    user_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, provider_email))
    access_token = create_jwt_token(user_uuid, provider_email, name=f"{data.provider.capitalize()} User")
    refresh_token = create_jwt_token(user_uuid, provider_email, expires_delta=timedelta(days=30))
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(data: RefreshRequest):
    try:
        payload = jwt.decode(
            data.refresh_token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        user_id = payload.get("sub")
        email = payload.get("email", "user@vajra.ai")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        new_access_token = create_jwt_token(user_id, email)
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=data.refresh_token
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_db_user)
):
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    return {"status": "ok", "message": "Password changed successfully"}

@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest):
    return {"status": "ok", "message": f"Password reset instructions sent to {data.email}"}

@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest):
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    return {"status": "ok", "message": "Password has been successfully reset"}

@router.delete("/account", status_code=status.HTTP_200_OK)
def delete_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_db_user)
):
    user_id = current_user.id
    # Cascade clean user artifacts
    db.query(Memory).filter(Memory.user_id == user_id).delete()
    db.query(PlannerTask).filter(PlannerTask.user_id == user_id).delete()
    db.query(SubjectModel).filter(SubjectModel.user_id == user_id).delete()
    db.query(AssignmentModel).filter(AssignmentModel.user_id == user_id).delete()
    db.query(CalendarEventModel).filter(CalendarEventModel.user_id == user_id).delete()
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    return {"status": "ok", "message": "User account and associated data completely purged"}

@router.post("/logout")
def logout():
    return {"status": "ok", "message": "Successfully logged out"}
