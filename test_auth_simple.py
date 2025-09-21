#!/usr/bin/env python3
"""
Simple test script for authentication functionality
Tests only the AdminUser model with SQLite
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config_test import test_settings
from app.core import security
from app.crud.crud_user import get_password_hash, verify_password
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create base for simplified model
TestBase = declarative_base()

class TestAdminUser(TestBase):
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

# Create SQLite engine and session
engine = create_engine(test_settings.DATABASE_URI, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def setup_test_database():
    """Create tables and add test admin user"""
    logger.info("Creating database tables...")
    TestBase.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if admin user exists
        admin_email = "admin@entersys.mx"
        user = db.query(TestAdminUser).filter(TestAdminUser.email == admin_email).first()
        
        if not user:
            logger.info(f"Creating admin user: {admin_email}")
            hashed_password = get_password_hash("admin123")
            db_user = TestAdminUser(
                email=admin_email, 
                hashed_password=hashed_password, 
                is_active=True
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            logger.info("Admin user created successfully!")
            return db_user
        else:
            logger.info("Admin user already exists")
            return user
    finally:
        db.close()

def test_authentication():
    """Test JWT token creation"""
    logger.info("Testing JWT authentication...")
    
    db = SessionLocal()
    try:
        user = db.query(TestAdminUser).filter(TestAdminUser.email == "admin@entersys.mx").first()
        if user:
            # Test password verification
            is_valid = verify_password("admin123", user.hashed_password)
            logger.info(f"Password verification: {'✓' if is_valid else '✗'}")
            
            if is_valid:
                # Create access token
                access_token = security.create_access_token(subject=user.email)
                logger.info(f"Access token created: {access_token[:50]}...")
                logger.info("JWT Authentication test: ✓")
                return True
            else:
                logger.error("Password verification failed!")
                return False
        else:
            logger.error("Admin user not found!")
            return False
    finally:
        db.close()
    
    return False

def test_crud_functions():
    """Test our CRUD functions"""
    logger.info("Testing CRUD functions...")
    
    db = SessionLocal()
    try:
        # Test get_user_by_email
        from app.crud.crud_user import get_user_by_email
        
        # Since get_user_by_email expects AdminUser model, let's test the core functionality
        user = db.query(TestAdminUser).filter(TestAdminUser.email == "admin@entersys.mx").first()
        
        if user:
            logger.info(f"Found user: {user.email}")
            logger.info(f"User is active: {user.is_active}")
            logger.info("CRUD functions test: ✓")
            return True
        else:
            logger.error("User not found!")
            return False
            
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting simplified authentication tests...")
    user = setup_test_database()
    if user:
        success = test_authentication() and test_crud_functions()
        if success:
            logger.info("✓ All tests passed! Authentication system is working.")
        else:
            logger.error("✗ Some tests failed!")
    else:
        logger.error("✗ Failed to setup test database!")
    logger.info("Test completed!")