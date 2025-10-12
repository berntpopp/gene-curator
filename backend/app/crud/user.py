"""
User CRUD operations.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models import UserNew as User, UserRoleNew as UserRole
from app.schemas.auth import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """CRUD operations for User model."""

    def get_by_email(self, db: Session, *, email: str) -> User | None:
        """Get user by email address."""
        return db.query(User).filter(User.email == email).first()

    def create(self, db: Session, *, user_create: UserCreate) -> User:
        """Create a new user with hashed password."""
        db_obj = User(
            email=user_create.email,
            hashed_password=get_password_hash(user_create.password),
            name=user_create.name,
            role=user_create.role,
            institution=user_create.institution,
            orcid_id=user_create.orcid_id,
            expertise_areas=user_create.expertise_areas or [],
            assigned_scopes=user_create.assigned_scopes or [],
            is_active=user_create.is_active,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
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
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
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
    ) -> list[User]:
        """Get users by role."""
        return (
            db.query(User)
            .filter(User.role == role)
            .filter(User.is_active)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search(
        self, db: Session, *, query: str, skip: int = 0, limit: int = 100
    ) -> list[User]:
        """Search users by name or email."""
        search_filter = (
            or_(
                User.name.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%"),
                User.institution.ilike(f"%{query}%"),
            )
            if query
            else True
        )

        return db.query(User).filter(search_filter).offset(skip).limit(limit).all()

    def get_statistics(self, db: Session) -> dict[str, Any]:
        """Get user statistics."""
        total_users = db.query(func.count(User.id)).scalar()
        active_users = (
            db.query(func.count(User.id)).filter(User.is_active).scalar()
        )

        role_counts = {}
        for role in UserRole:
            count = db.query(func.count(User.id)).filter(User.role == role).scalar()
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
    ) -> list[User]:
        """Get users assigned to a specific scope."""
        return (
            db.query(User)
            .filter(User.assigned_scopes.contains([str(scope_id)]))
            .filter(User.is_active)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def assign_to_scope(self, db: Session, *, user_id: str, scope_id: UUID) -> bool:
        """Assign user to a scope."""
        user = self.get(db, id=user_id)
        if not user:
            return False

        scope_id_str = str(scope_id)
        current_scopes = user.assigned_scopes or []

        if scope_id_str not in current_scopes:
            current_scopes.append(scope_id_str)
            user.assigned_scopes = current_scopes
            db.commit()

        return True

    def remove_from_scope(self, db: Session, *, user_id: str, scope_id: UUID) -> bool:
        """Remove user from a scope."""
        user = self.get(db, id=user_id)
        if not user:
            return False

        scope_id_str = str(scope_id)
        current_scopes = user.assigned_scopes or []

        if scope_id_str in current_scopes:
            current_scopes.remove(scope_id_str)
            user.assigned_scopes = current_scopes
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
