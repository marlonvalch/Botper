#!/usr/bin/env python3
"""
Webex Bot Permission Checker
Verifies if your bot token has the required scopes for meeting creation
"""

import os
import requests
from dotenv import load_dotenv

def check_bot_permissions():
    """Check if bot has required scopes for meeting creation"""
    
    # Load environment variables
    load_dotenv()
    token = os.getenv("WEBEX_BOT_TOKEN")
    
    if not token:
        print("❌ WEBEX_BOT_TOKEN not found in .env file")
        return False
    
    print("🔍 Checking bot permissions...\n")
    
    # Test basic bot info (should always work)
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Check bot identity
        response = requests.get("https://webexapis.com/v1/people/me", headers=headers)
        if response.status_code != 200:
            print(f"❌ Invalid bot token - Status: {response.status_code}")
            return False
            
        bot_info = response.json()
        print(f"✅ Bot Identity: {bot_info.get('displayName', 'Unknown')}")
        print(f"✅ Bot Email: {bot_info.get('emails', ['Unknown'])[0]}")
        print()
        
        # Test meeting API access (this will fail if scopes are missing)
        print("🎯 Testing Meeting API Access...")
        meeting_response = requests.get("https://webexapis.com/v1/meetings", headers=headers)
        
        if meeting_response.status_code == 200:
            print("✅ Meeting API Access: GRANTED")
            print("✅ Bot has proper meeting scopes!")
            print("\n🎉 Your bot is ready to create Webex meetings!")
            return True
            
        elif meeting_response.status_code == 403:
            print("❌ Meeting API Access: DENIED")
            print("❌ Missing required scopes: meeting:schedules_write, meeting:schedules_read")
            print("\n🔧 TO FIX:")
            print("1. Go to https://developer.webex.com")
            print("2. Find your bot in 'My Apps'")
            print("3. Click 'Scopes' or 'OAuth & Permissions'")
            print("4. Add these scopes:")
            print("   ✓ meeting:schedules_write")
            print("   ✓ meeting:schedules_read")
            print("5. Regenerate your bot token")
            print("6. Update your .env file with new token")
            return False
            
        else:
            print(f"❌ Unexpected API response: {meeting_response.status_code}")
            print(f"Response: {meeting_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking permissions: {e}")
        return False

if __name__ == "__main__":
    print("🤖 Webex Bot Permission Checker")
    print("=" * 40)
    
    success = check_bot_permissions()
    
    if success:
        print("\n✅ Permission check PASSED - Bot ready for meetings!")
    else:
        print("\n❌ Permission check FAILED - Fix permissions to enable meetings")
        print("\n📚 Quick Reference:")
        print("- Spaces/messaging: Works with basic bot token")
        print("- Video meetings: Requires meeting API scopes")
        print("- Fallback: Bot creates meeting spaces instead")