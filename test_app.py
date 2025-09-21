#!/usr/bin/env python3
"""
Test script for local authentication functionality
Uses SQLite for testing without requiring PostgreSQL
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.blog import Base, AdminUser
from app.core.config_test import test_settings
from app.crud.crud_user import get_user_by_email, create_admin_user
from app.core import security
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create SQLite engine
engine = create_engine(test_settings.DATABASE_URI, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def setup_test_database():
    """Create tables and add test admin user"""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if admin user exists
        admin_email = "admin@entersys.mx"
        user = get_user_by_email(db, email=admin_email)
        
        if not user:
            logger.info(f"Creating admin user: {admin_email}")
            create_admin_user(db, email=admin_email, password="admin123")
            logger.info("Admin user created successfully!")
        else:
            logger.info("Admin user already exists")
    finally:
        db.close()

def test_authentication():
    """Test JWT token creation"""
    logger.info("Testing JWT authentication...")
    
    db = SessionLocal()
    try:
        user = get_user_by_email(db, email="admin@entersys.mx")
        if user:
            # Test password verification
            is_valid = security.verify_password("admin123", user.hashed_password)
            logger.info(f"Password verification: {'✓' if is_valid else '✗'}")
            
            if is_valid:
                # Create access token
                access_token = security.create_access_token(data={"sub": user.email})
                logger.info(f"Access token created: {access_token[:50]}...")
                logger.info("JWT Authentication test: ✓")
                return True
        else:
            logger.error("Admin user not found!")
            return False
    finally:
        db.close()
    
    return False

if __name__ == "__main__":
    logger.info("Starting local authentication tests...")
    setup_test_database()
    test_authentication()
    logger.info("Test completed!")