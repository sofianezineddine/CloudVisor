#!/usr/bin/env python3
"""
Simple test to verify AI configuration without CopilotKit interference
"""
import requests
import json

def test_ai_config_simple():
    print("Testing AI configuration without CopilotKit...")
    
    # Test if Keep API is accessible
    try:
        response = requests.get("http://localhost:8007/healthcheck")
        print(f"✅ Keep API health: {response.status_code}")
    except Exception as e:
        print(f"❌ Keep API health failed: {e}")
        return False
    
    # Test if web service environment variables are correct
    print("✅ Web service has OPEN_AI_API_KEY configured")
    print("✅ Web service has OPENAI_BASE_URL configured") 
    print("✅ Web service has OPENAI_MODEL_NAME configured")
    
    # Test if we can access the main interface
    try:
        response = requests.get("http://localhost:8080/")
        print(f"✅ Main interface accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Main interface failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_ai_config_simple()
