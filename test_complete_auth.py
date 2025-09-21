#!/usr/bin/env python3
"""
Complete test for authentication system
Tests JWT token validation and Google OAuth readiness
"""

import sys
import os
import json
import requests
from jose import jwt, JWTError
sys.path.append(os.path.dirname(__file__))

from app.core.config_test import test_settings
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_jwt_complete_flow():
    """Test complete JWT authentication flow"""
    logger.info("=== Testing JWT Complete Flow ===")
    
    base_url = "http://localhost:8000"
    
    # Test 1: Get access token
    logger.info("1. Testing JWT token generation...")
    auth_data = {
        "username": "admin@entersys.mx",
        "password": "admin123"
    }
    
    response = requests.post(
        f"{base_url}/api/v1/auth/token",
        data=auth_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data["access_token"]
        logger.info(f"✓ Token generated successfully: {access_token[:50]}...")
        
        # Test 2: Validate token structure
        logger.info("2. Testing JWT token validation...")
        try:
            # Decode token without verification first to see the payload
            unverified_payload = jwt.get_unverified_claims(access_token)
            logger.info(f"✓ Token payload: {unverified_payload}")
            
            # Verify token with secret
            payload = jwt.decode(
                access_token, 
                test_settings.SECRET_KEY, 
                algorithms=[test_settings.ALGORITHM]
            )
            logger.info(f"✓ Token verified successfully")
            logger.info(f"  - Subject: {payload.get('sub')}")
            logger.info(f"  - Expires: {payload.get('exp')}")
            
            return True
            
        except JWTError as e:
            logger.error(f"✗ Token validation failed: {e}")
            return False
            
    else:
        logger.error(f"✗ Authentication failed: {response.status_code} - {response.text}")
        return False

def test_google_oauth_endpoints():
    """Test Google OAuth endpoints availability"""
    logger.info("=== Testing Google OAuth Endpoints ===")
    
    base_url = "http://localhost:8000"
    
    # Test 1: Google login redirect
    logger.info("1. Testing Google OAuth redirect...")
    try:
        response = requests.get(
            f"{base_url}/api/v1/login/google",
            allow_redirects=False
        )
        
        if response.status_code == 302:
            redirect_url = response.headers.get('Location', '')
            if 'accounts.google.com' in redirect_url:
                logger.info("✓ Google OAuth redirect working correctly")
                logger.info(f"  - Redirects to: {redirect_url[:100]}...")
                return True
            else:
                logger.error(f"✗ Unexpected redirect URL: {redirect_url}")
                return False
        else:
            logger.error(f"✗ Expected 302 redirect, got {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Google OAuth test failed: {e}")
        return False

def test_error_handling():
    """Test error handling"""
    logger.info("=== Testing Error Handling ===")
    
    base_url = "http://localhost:8000"
    
    # Test 1: Wrong credentials
    logger.info("1. Testing wrong credentials...")
    auth_data = {
        "username": "admin@entersys.mx",
        "password": "wrongpassword"
    }
    
    response = requests.post(
        f"{base_url}/api/v1/auth/token",
        data=auth_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 401:
        error_data = response.json()
        logger.info(f"✓ Wrong credentials properly rejected: {error_data['detail']}")
        
        # Test 2: Non-existent user
        logger.info("2. Testing non-existent user...")
        auth_data["username"] = "nonexistent@entersys.mx"
        
        response = requests.post(
            f"{base_url}/api/v1/auth/token",
            data=auth_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 401:
            logger.info("✓ Non-existent user properly rejected")
            return True
        else:
            logger.error(f"✗ Expected 401 for non-existent user, got {response.status_code}")
            return False
    else:
        logger.error(f"✗ Expected 401 for wrong credentials, got {response.status_code}")
        return False

def test_api_documentation():
    """Test API documentation endpoints"""
    logger.info("=== Testing API Documentation ===")
    
    base_url = "http://localhost:8000"
    
    # Test OpenAPI schema
    logger.info("1. Testing OpenAPI schema...")
    response = requests.get(f"{base_url}/openapi.json")
    
    if response.status_code == 200:
        schema = response.json()
        logger.info(f"✓ OpenAPI schema available")
        logger.info(f"  - API Title: {schema.get('info', {}).get('title', 'N/A')}")
        logger.info(f"  - API Version: {schema.get('info', {}).get('version', 'N/A')}")
        
        # Check if our endpoints are documented
        paths = schema.get('paths', {})
        expected_paths = ['/api/v1/auth/token', '/api/v1/login/google', '/api/v1/auth/google']
        
        for path in expected_paths:
            if path in paths:
                logger.info(f"  - ✓ {path} documented")
            else:
                logger.info(f"  - ✗ {path} missing from docs")
        
        return True
    else:
        logger.error(f"✗ OpenAPI schema not available: {response.status_code}")
        return False

if __name__ == "__main__":
    logger.info("Starting complete authentication system tests...")
    logger.info(f"Testing against server: http://localhost:8000")
    
    results = []
    results.append(("JWT Complete Flow", test_jwt_complete_flow()))
    results.append(("Google OAuth Endpoints", test_google_oauth_endpoints()))
    results.append(("Error Handling", test_error_handling()))
    results.append(("API Documentation", test_api_documentation()))
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("TEST SUMMARY")
    logger.info("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        logger.info(f"{test_name}: {status}")
        if success:
            passed += 1
    
    logger.info(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Authentication system is fully functional.")
    else:
        logger.info(f"⚠️  {total - passed} tests failed. Review the logs above.")
    
    logger.info("\nAuthentication system test completed!")