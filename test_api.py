#!/usr/bin/env python3
"""
Simple test runner for the professionals API endpoints.
Run this script to test the API functionality.
"""

import json
import requests
import sys
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000/api/v1"

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token = None
        self.refresh_token = None
        
    def register_professional(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new professional."""
        response = self.session.post(f"{self.base_url}/professionals/register", json=data)
        return {"status_code": response.status_code, "data": response.json()}
    
    def login_professional(self, identifier: str, password: str) -> Dict[str, Any]:
        """Login professional and store tokens."""
        data = {"identifier": identifier, "password": password}
        response = self.session.post(f"{self.base_url}/professionals/login", json=data)
        
        if response.status_code == 200:
            tokens = response.json()
            self.access_token = tokens["access_token"]
            self.refresh_token = tokens["refresh_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
        
        return {"status_code": response.status_code, "data": response.json()}
    
    def get_current_professional(self) -> Dict[str, Any]:
        """Get current professional info."""
        response = self.session.get(f"{self.base_url}/professionals/me")
        return {"status_code": response.status_code, "data": response.json()}
    
    def get_professional_by_id(self, professional_id: int) -> Dict[str, Any]:
        """Get professional by ID."""
        response = self.session.get(f"{self.base_url}/professionals/{professional_id}")
        return {"status_code": response.status_code, "data": response.json()}
    
    def update_professional(self, professional_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update professional."""
        response = self.session.put(f"{self.base_url}/professionals/{professional_id}", json=data)
        return {"status_code": response.status_code, "data": response.json()}
    
    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token."""
        data = {"refresh_token": self.refresh_token}
        response = self.session.post(f"{self.base_url}/professionals/refresh-token", json=data)
        
        if response.status_code == 200:
            tokens = response.json()
            self.access_token = tokens["access_token"]
            self.refresh_token = tokens["refresh_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
        
        return {"status_code": response.status_code, "data": response.json()}


def run_tests():
    """Run API tests."""
    print("🧪 Running Professional API Tests...")
    print("=" * 50)
    
    tester = APITester(BASE_URL)
    
    # Test data
    professional_data = {
        "first_name": "John",
        "last_name": "Doe",
        "mobile_number": "+1234567890",
        "password": "testpassword123",
        "country": "USA",
        "accept_privacy_policy": True
    }
    
    # Test 1: Register Professional
    print("\n1️⃣ Testing Professional Registration...")
    result = tester.register_professional(professional_data)
    if result["status_code"] == 201:
        print("✅ Registration successful")
        professional_id = result["data"]["id"]
        print(f"   Professional ID: {professional_id}")
    else:
        print(f"❌ Registration failed: {result['data']}")
        return
    
    # Test 2: Login Professional
    print("\n2️⃣ Testing Professional Login...")
    result = tester.login_professional(professional_data["mobile_number"], professional_data["password"])
    if result["status_code"] == 200:
        print("✅ Login successful")
        print("   Access token received ✓")
        print("   Refresh token received ✓")
    else:
        print(f"❌ Login failed: {result['data']}")
        return
    
    # Test 3: Get Current Professional Info
    print("\n3️⃣ Testing Get Current Professional Info...")
    result = tester.get_current_professional()
    if result["status_code"] == 200:
        print("✅ Get current professional successful")
        print(f"   Name: {result['data']['first_name']} {result['data']['last_name']}")
    else:
        print(f"❌ Get current professional failed: {result['data']}")
    
    # Test 4: Get Professional by ID
    print("\n4️⃣ Testing Get Professional by ID...")
    result = tester.get_professional_by_id(professional_id)
    if result["status_code"] == 200:
        print("✅ Get professional by ID successful")
    else:
        print(f"❌ Get professional by ID failed: {result['data']}")
    
    # Test 5: Update Professional
    print("\n5️⃣ Testing Update Professional...")
    update_data = {"first_name": "Johnny", "country": "Canada"}
    result = tester.update_professional(professional_id, update_data)
    if result["status_code"] == 200:
        print("✅ Update professional successful")
        print(f"   Updated name: {result['data']['first_name']}")
        print(f"   Updated country: {result['data']['country']}")
    else:
        print(f"❌ Update professional failed: {result['data']}")
    
    # Test 6: Refresh Token
    print("\n6️⃣ Testing Token Refresh...")
    result = tester.refresh_access_token()
    if result["status_code"] == 200:
        print("✅ Token refresh successful")
        print("   New access token received ✓")
    else:
        print(f"❌ Token refresh failed: {result['data']}")
    
    # Test 7: Test Authorization (try to access without token)
    print("\n7️⃣ Testing Authorization...")
    tester.session.headers.pop("Authorization", None)  # Remove auth header
    result = tester.get_current_professional()
    if result["status_code"] == 403:
        print("✅ Authorization test successful (correctly denied access)")
    else:
        print(f"❌ Authorization test failed: Expected 403, got {result['status_code']}")
    
    print("\n🎉 All tests completed!")
    print("=" * 50)


if __name__ == "__main__":
    try:
        run_tests()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server.")
        print("Make sure the server is running on http://localhost:8000")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
