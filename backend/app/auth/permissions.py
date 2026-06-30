from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from .jwt_handler import verify_token
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from ..db.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# In-memory cache to map user_id -> List[str] permissions
_permission_cache: Dict[int, List[str]] = {}

def update_permission_cache(user_id: int, permissions: List[str]):
    _permission_cache[user_id] = permissions

async def get_current_user_token(token: str = Depends(oauth2_scheme)) -> dict:
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

class RequiresPermission:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    async def __call__(self, token_payload: dict = Depends(get_current_user_token), db: AsyncSession = Depends(get_db)):
        user_id_str = token_payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        user_id = int(user_id_str)
        # Check cache
        user_perms = _permission_cache.get(user_id)
        if user_perms is None:
            # Cache miss (e.g. server restarted or cold start)
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from ..models.user import User
            from ..models.role import Role
            
            stmt = select(User).where(User.id == user_id).options(
                selectinload(User.roles).selectinload(Role.permissions)
            )
            result = await db.execute(stmt)
            user = result.scalars().first()
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            
            # Extract and update cache
            perms = set()
            for role in user.roles:
                for perm in role.permissions:
                    perms.add(perm.name)
            user_perms = list(perms)
            _permission_cache[user_id] = user_perms
            
        if self.required_permission not in user_perms:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return user_id
