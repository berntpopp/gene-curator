#!/usr/bin/env python3
"""
Script to create a default admin user for development.
"""

import os
import sys

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import get_db
from app.crud.user import user_crud
from app.schemas.auth import UserCreate


def create_default_user():
    """Create default admin user for development."""

    # Get database session
    db = next(get_db())

    try:
        # Default user credentials
        default_email = "admin@gene-curator.dev"
        default_password = "admin123"
        default_name = "Default Admin"

        # Check if user already exists
        existing_user = user_crud.get_by_email(db, email=default_email)
        if existing_user:
            print(f"✅ User {default_email} already exists")
            print(f"   ID: {existing_user.id}")
            print(f"   Role: {existing_user.role}")
            print(f"   Active: {existing_user.is_active}")
            return existing_user

        # Create user data
        user_data = UserCreate(
            email=default_email,
            password=default_password,
            name=default_name,
            role="admin",  # Use string value directly
            is_active=True,
        )

        # Create user
        user = user_crud.create(db, user_create=user_data)

        print("🎉 Default admin user created successfully!")
        print(f"   Email: {user.email}")
        print(f"   Password: {default_password}")
        print(f"   Name: {user.name}")
        print(f"   Role: {user.role}")
        print(f"   ID: {user.id}")
        print()
        print("💡 You can now login with these credentials:")
        print("   POST /api/v1/auth/login")
        print(f'   {{"email": "{default_email}", "password": "{default_password}"}}')

        return user

    except Exception as e:
        print(f"❌ Error creating default user: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_additional_test_users():
    """Create additional test users for different roles."""

    db = next(get_db())

    try:
        # Test users to create
        test_users = [
            {
                "email": "curator@gene-curator.dev",
                "password": "curator123",
                "name": "Test Curator",
                "role": "curator",
            },
            {
                "email": "viewer@gene-curator.dev",
                "password": "viewer123",
                "name": "Test Viewer",
                "role": "viewer",
            },
        ]

        created_users = []

        for user_info in test_users:
            # Check if user already exists
            existing_user = user_crud.get_by_email(db, email=user_info["email"])
            if existing_user:
                print(f"✅ User {user_info['email']} already exists")
                created_users.append(existing_user)
                continue

            # Create user data
            user_data = UserCreate(
                email=user_info["email"],
                password=user_info["password"],
                name=user_info["name"],
                role=user_info["role"],
                is_active=True,
            )

            # Create user
            user = user_crud.create(db, user_create=user_data)
            created_users.append(user)

            print(f"✅ Created {user.role} user: {user.email}")

        return created_users

    except Exception as e:
        print(f"❌ Error creating test users: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Creating default users for Gene Curator...")
    print()

    # Create default admin user
    create_default_user()
    print()

    # Create additional test users
    print("Creating additional test users...")
    create_additional_test_users()
    print()

    print("✅ All default users created successfully!")
    print()
    print("🔐 Authentication endpoints available at:")
    print("   - POST /api/v1/auth/login")
    print("   - POST /api/v1/auth/register")
    print("   - GET /api/v1/auth/me")
    print("   - POST /api/v1/auth/refresh")
    print("   - POST /api/v1/auth/logout")
