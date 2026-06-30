from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from ..db.database import get_db
from ..auth.auth_service import authenticate_user, get_password_hash
from ..auth.jwt_handler import create_access_token, create_refresh_token, verify_token
from ..auth.permissions import get_current_user_token, update_permission_cache
from ..models.user import User
from ..models.role import Role

router = APIRouter()

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str = ""
    organization: str = ""

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    role_name = user.roles[0].name if user.roles else "User"
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "name": user.full_name or user.username.split('@')[0].capitalize(),
            "role": role_name
        }
    }

@router.post("/register")
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if username or email already exists
    stmt = select(User).where((User.username == request.username) | (User.email == request.email))
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )

    # Link default Administrator role
    stmt = select(Role).where(Role.name == "Administrator").options(selectinload(Role.permissions))
    res = await db.execute(stmt)
    admin_role = res.scalars().first()

    # Hash password and create User
    hashed_pw = get_password_hash(request.password)
    new_user = User(
        username=request.username,
        email=request.email,
        hashed_password=hashed_pw,
        full_name=request.full_name,
        is_active=True,
        roles=[admin_role] if admin_role else []
    )
    db.add(new_user)
    await db.commit()

    if admin_role:
        # Load permissions into cache
        perms = set()
        for perm in admin_role.permissions:
            perms.add(perm.name)
        update_permission_cache(new_user.id, list(perms))

    # Generate JWT
    access_token = create_access_token(data={"sub": str(new_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(new_user.id)})
    
    role_name = admin_role.name if admin_role else "User"
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
            "name": new_user.full_name or new_user.username.split('@')[0].capitalize(),
            "role": role_name
        }
    }

@router.get("/me")
async def get_me(token_payload: dict = Depends(get_current_user_token), db: AsyncSession = Depends(get_db)):
    user_id_str = token_payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user_id = int(user_id_str)
    
    stmt = select(User).where(User.id == user_id).options(
        selectinload(User.roles).selectinload(Role.permissions)
    )
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Sync permissions cache in case of server restart
    perms = set()
    for role in user.roles:
        for perm in role.permissions:
            perms.add(perm.name)
    update_permission_cache(user.id, list(perms))
    
    role_name = user.roles[0].name if user.roles else "User"
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "name": user.full_name or user.username.split('@')[0].capitalize(),
        "role": role_name
    }

@router.post("/refresh")
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = verify_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user_id = int(user_id_str)
    
    stmt = select(User).where(User.id == user_id).options(
        selectinload(User.roles).selectinload(Role.permissions)
    )
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    # Sync permissions cache
    perms = set()
    for role in user.roles:
        for perm in role.permissions:
            perms.add(perm.name)
    update_permission_cache(user.id, list(perms))
    
    role_name = user.roles[0].name if user.roles else "User"
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "name": user.full_name or user.username.split('@')[0].capitalize(),
            "role": role_name
        }
    }
