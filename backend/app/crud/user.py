"""
User CRUD operations.
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models import UserNew as User, UserRoleNew as UserRole
from app.schemas.auth import UserCreate, UserUpdate

logger = get_logger(__name__)


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """CRUD operations for User model."""

    def get_by_email(self, db: Session, *, email: str) -> User | None:
        """Get user by email address."""
        stmt = select(User).where(User.email == email)
        return db.execute(stmt).scalars().first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """Create a new user with hashed password."""
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            name=obj_in.name,
            role=obj_in.role,
            institution=obj_in.institution,
            orcid_id=obj_in.orcid_id,
            expertise_areas=obj_in.expertise_areas or [],
            assigned_scopes=obj_in.assigned_scopes or [],
            is_active=obj_in.is_active,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_user(
        self, db: Session, *, user_id: str, user_update: UserUpdate
    ) -> User | None:
        """Update user data."""
        db_obj = self.get(db, id=user_id)
        if not db_obj:
            return None

        update_data = user_update.model_dump(exclude_unset=True)

        # Handle password update separately
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(
                update_data.pop("password")
            )

        for key, value in update_data.items():
            setattr(db_obj, key, value)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_password(self, db: Session, *, user_id: str, new_password: str) -> bool:
        """Update user password."""
        db_obj = self.get(db, id=user_id)
        if not db_obj:
            return False

        db_obj.hashed_password = get_password_hash(new_password)
        db.commit()
        return True

    def authenticate(self, db: Session, *, email: str, password: str) -> User | None:
        """Authenticate user by email and password."""
        logger.debug("Attempting to authenticate user", email=email)

        user = self.get_by_email(db, email=email)
        if not user:
            logger.warning("User not found in database", email=email)
            return None

        logger.debug(
            "User found, verifying password",
            email=email,
            user_id=str(user.id),
            has_hashed_password=bool(user.hashed_password),
            hashed_password_length=len(user.hashed_password)
            if user.hashed_password
            else 0,
        )

        password_valid = verify_password(password, user.hashed_password)

        if not password_valid:
            logger.warning(
                "Password verification failed",
                email=email,
                user_id=str(user.id),
            )
            return None

        logger.info(
            "User authenticated successfully",
            email=email,
            user_id=str(user.id),
            role=user.role.value,
        )
        return user

    def is_active(self, user: User) -> bool:
        """Check if user is active."""
        return user.is_active

    def is_admin(self, user: User) -> bool:
        """Check if user has admin role."""
        return user.role == UserRole.ADMIN

    def has_role(self, user: User, role: UserRole) -> bool:
        """Check if user has specific role."""
        return user.role == role

    def has_any_role(self, user: User, roles: list[UserRole]) -> bool:
        """Check if user has any of the specified roles."""
        return user.role in roles

    def get_by_role(
        self, db: Session, *, role: UserRole, skip: int = 0, limit: int = 100
    ) -> Sequence[User]:
        """Get users by role."""
        stmt = (
            select(User)
            .where(User.role == role)
            .where(User.is_active)
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def search(
        self, db: Session, *, query: str, skip: int = 0, limit: int = 100
    ) -> Sequence[User]:
        """Search users by name or email."""
        stmt = select(User)

        if query:
            search_filter = or_(
                User.name.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%"),
                User.institution.ilike(f"%{query}%"),
            )
            stmt = stmt.where(search_filter)

        stmt = stmt.offset(skip).limit(limit)
        return db.execute(stmt).scalars().all()

    def get_statistics(self, db: Session) -> dict[str, Any]:
        """Get user statistics."""
        total_users = db.execute(select(func.count(User.id))).scalar() or 0
        active_users = db.execute(
            select(func.count(User.id)).where(User.is_active)
        ).scalar() or 0

        role_counts: dict[str, int] = {}
        for role in UserRole:
            count = db.execute(
                select(func.count(User.id)).where(User.role == role)
            ).scalar() or 0
            role_counts[role.value] = count

        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "role_distribution": role_counts,
        }

    def get_user_activity(self, db: Session, *, user_id: str) -> dict[str, Any]:
        """Get user activity summary."""
        user = self.get(db, id=user_id)
        if not user:
            return {}

        # This would be expanded with actual activity tracking
        return {
            "user_id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user.role.value,
            "last_login": user.last_login,
            "assigned_scopes": len(user.assigned_scopes) if user.assigned_scopes else 0,
            "expertise_areas": len(user.expertise_areas) if user.expertise_areas else 0,
            "is_active": user.is_active,
        }

    def get_users_by_scope(
        self, db: Session, *, scope_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[User]:
        """Get users assigned to a specific scope."""
        stmt = (
            select(User)
            .where(User.assigned_scopes.contains([str(scope_id)]))
            .where(User.is_active)
            .offset(skip)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def assign_to_scope(self, db: Session, *, user_id: str, scope_id: UUID) -> bool:
        """Assign user to a scope."""
        user = self.get(db, id=user_id)
        if not user:
            return False

        scope_id_str = str(scope_id)
        current_scopes: list[str] = [str(s) for s in (user.assigned_scopes or [])]

        if scope_id_str not in current_scopes:
            current_scopes.append(scope_id_str)
            user.assigned_scopes = [UUID(s) for s in current_scopes]
            db.commit()

        return True

    def remove_from_scope(self, db: Session, *, user_id: str, scope_id: UUID) -> bool:
        """Remove user from a scope."""
        user = self.get(db, id=user_id)
        if not user:
            return False

        scope_id_str = str(scope_id)
        current_scopes: list[str] = [str(s) for s in (user.assigned_scopes or [])]

        if scope_id_str in current_scopes:
            current_scopes.remove(scope_id_str)
            user.assigned_scopes = [UUID(s) for s in current_scopes]
            db.commit()

        return True

    def update_last_login(self, db: Session, user_id: str) -> bool:
        """Update user's last login timestamp."""
        user = self.get(db, id=user_id)
        if not user:
            return False

        from datetime import datetime

        user.last_login = datetime.now()
        db.commit()
        return True


# Create instance
user_crud = CRUDUser(User)
