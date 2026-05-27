#!/usr/bin/env python3
"""
Test script to verify AI configuration in Keep service
"""
import requests
import json

def test_ai_config():
    # Test if Keep API is accessible
    try:
        response = requests.get("http://localhost:8007/healthcheck")
        print(f"✅ Keep API health check: {response.status_code}")
    except Exception as e:
        print(f"❌ Keep API health check failed: {e}")
        return False
    
    # Test if AI endpoint exists
    try:
        response = requests.get("http://localhost:8007/ai/status")
        print(f"✅ AI status endpoint: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ AI status endpoint failed: {e}")
    
    # Test if workflows endpoint is accessible
    try:
        response = requests.get("http://localhost:8007/workflows")
        print(f"✅ Workflows endpoint: {response.status_code}")
    except Exception as e:
        print(f"❌ Workflows endpoint failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Testing AI configuration in Keep service...")
    test_ai_config()
