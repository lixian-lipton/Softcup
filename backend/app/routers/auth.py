from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User, UserRole
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["认证"])


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, username=user.username, role=user.role.value)


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    username = body.username.strip()
    if username.lower() == "admin":
        raise HTTPException(status_code=400, detail="该用户名不可注册")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=username,
        password_hash=hash_password(body.password),
        role=UserRole.user,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role.value,
        secret=settings.auth_secret,
        expires_hours=settings.auth_token_hours,
    )
    return TokenResponse(access_token=token, user=_user_out(user))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username.strip()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已禁用")
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role.value,
        secret=settings.auth_secret,
        expires_hours=settings.auth_token_hours,
    )
    return TokenResponse(access_token=token, user=_user_out(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return _user_out(user)
