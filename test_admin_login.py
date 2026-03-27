#!/usr/bin/env python3
"""
Test login with provided admin credentials
"""

import requests
import json

def test_admin_login():
    base_url = "https://novavision-finanzas.preview.emergentagent.com"
    
    # Test login with provided credentials
    login_data = {
        "email": "admin@novavision.gt",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{base_url}/api/auth/login", json=login_data, timeout=10)
        print(f"Login Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            user = data.get('user', {})
            print(f"✅ Login successful!")
            print(f"User: {user.get('name')} ({user.get('email')})")
            print(f"Role: {user.get('role')}")
            print(f"Active: {user.get('is_active')}")
            
            # Test user management access
            token = data.get('access_token')
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            users_response = requests.get(f"{base_url}/api/users", headers=headers, timeout=10)
            print(f"\nUsers endpoint status: {users_response.status_code}")
            
            if users_response.status_code == 200:
                users = users_response.json()
                print(f"✅ Can access users endpoint - Found {len(users)} users")
                for user in users:
                    print(f"  - {user.get('name')} ({user.get('role')})")
            else:
                print(f"❌ Cannot access users endpoint: {users_response.text}")
                
        else:
            print(f"❌ Login failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_admin_login()