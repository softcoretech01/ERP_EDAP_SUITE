from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..models.user import User
from ..models.role import Role
from .permissions import update_permission_cache

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt_sha256", "bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    stmt = select(User).where(User.username == username).options(
        selectinload(User.roles).selectinload(Role.permissions)
    )
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    
    # Load permissions into cache
    perms = set()
    for role in user.roles:
        for perm in role.permissions:
            perms.add(perm.name)
            
    update_permission_cache(user.id, list(perms))
    
    return user
