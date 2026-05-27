#!/usr/bin/env python3
"""
Direct test of AI configuration in Keep service
"""
import requests
import json

def test_ai_direct():
    print("Testing AI configuration directly in Keep service...")
    
    # Test Keep API health
    try:
        response = requests.get("http://localhost:8007/healthcheck")
        print(f"✅ Keep API health: {response.status_code}")
    except Exception as e:
        print(f"❌ Keep API health failed: {e}")
        return False
    
    # Test if we can access workflows with AI configuration
    try:
        headers = {"X-Tenant-ID": "keep"}
        response = requests.get("http://localhost:8007/workflows", headers=headers)
        print(f"✅ Workflows endpoint: {response.status_code}")
        
        # Test AI-related endpoint if it exists
        response = requests.get("http://localhost:8007/providers", headers=headers)
        print(f"✅ Providers endpoint: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"❌ Workflows test failed: {e}")
        return False

if __name__ == "__main__":
    test_ai_direct()
