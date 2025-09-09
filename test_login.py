#!/usr/bin/env python3
"""
Test script per verificare il login
"""
import json
try:
    import requests
    
    # Test dell'endpoint di login
    url = "http://localhost:8000/api/v1/auth/login"
    data = {
        "username": "admin",
        "password": "WallBuild2024!"
    }
    
    print(f"Testing login endpoint: {url}")
    print(f"Credentials: {data}")
    
    response = requests.post(url, json=data)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        token_data = response.json()
        print("✅ Login SUCCESS!")
        print(f"Token: {token_data.get('access_token', 'N/A')[:50]}...")
    else:
        print("❌ Login FAILED!")
        
except ImportError:
    print("❌ requests library not available")
    # Fallback con urllib
    import urllib.request
    import urllib.parse
    
    url = "http://localhost:8000/api/v1/auth/login"
    data = json.dumps({
        "username": "admin",
        "password": "WallBuild2024!"
    }).encode('utf-8')
    
    req = urllib.request.Request(
        url, 
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = response.read().decode('utf-8')
            print(f"Status: {response.status}")
            print(f"Response: {result}")
    except Exception as e:
        print(f"Error: {e}")

except Exception as e:
    print(f"Unexpected error: {e}")
