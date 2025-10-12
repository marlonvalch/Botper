#!/usr/bin/env python3
"""
Script to set up Webex webhook
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

WEBEX_BOT_TOKEN = os.getenv("WEBEX_BOT_TOKEN")
NGROK_URL = "https://johnsie-unentangling-kolton.ngrok-free.dev"  # Current ngrok URL
WEBHOOK_URL = f"{NGROK_URL}/webex/webhook"

def list_existing_webhooks():
    """List all existing webhooks"""
    headers = {
        'Authorization': f'Bearer {WEBEX_BOT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get('https://webexapis.com/v1/webhooks', headers=headers)
    if response.status_code == 200:
        webhooks = response.json().get('items', [])
        print(f"Found {len(webhooks)} existing webhooks:")
        for webhook in webhooks:
            print(f"  - {webhook['name']}: {webhook['targetUrl']} (ID: {webhook['id']})")
        return webhooks
    else:
        print(f"Error listing webhooks: {response.status_code} - {response.text}")
        return []

def delete_webhook(webhook_id):
    """Delete a webhook by ID"""
    headers = {
        'Authorization': f'Bearer {WEBEX_BOT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    response = requests.delete(f'https://webexapis.com/v1/webhooks/{webhook_id}', headers=headers)
    if response.status_code == 204:
        print(f"✅ Deleted webhook: {webhook_id}")
    else:
        print(f"❌ Error deleting webhook: {response.status_code} - {response.text}")

def create_webhook(webhook_name, resource_type, event_type):
    """Create a new webhook for the specified resource and event"""
    headers = {
        'Authorization': f'Bearer {WEBEX_BOT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    webhook_data = {
        'name': webhook_name,
        'targetUrl': WEBHOOK_URL,
        'resource': resource_type,
        'event': event_type
    }
    
    response = requests.post('https://webexapis.com/v1/webhooks', 
                           headers=headers, 
                           json=webhook_data)
    
    if response.status_code == 200:
        webhook = response.json()
        print(f"✅ Webhook created successfully!")
        print(f"   Name: {webhook['name']}")
        print(f"   URL: {webhook['targetUrl']}")
        print(f"   Resource: {resource_type}")
        print(f"   Event: {event_type}")
        print(f"   ID: {webhook['id']}")
        return webhook
    else:
        print(f"❌ Error creating webhook: {response.status_code} - {response.text}")
        return None

def main():
    if not WEBEX_BOT_TOKEN:
        print("❌ WEBEX_BOT_TOKEN not found in .env file")
        return
    
    print("🔍 Checking existing webhooks...")
    existing_webhooks = list_existing_webhooks()
    
    # Delete existing webhooks for this bot (optional)
    if existing_webhooks:
        print("\n🗑️  Deleting existing webhooks...")
        for webhook in existing_webhooks:
            delete_webhook(webhook['id'])
    
    print(f"\n🔗 Creating webhooks for: {WEBHOOK_URL}")
    
    # Create webhook for messages
    print("\n📨 Creating message webhook...")
    create_webhook('Botper Message Webhook', 'messages', 'created')
    
    # Create webhook for attachment actions (button clicks)
    print("\n🔘 Creating attachment actions webhook...")
    create_webhook('Botper Actions Webhook', 'attachmentActions', 'created')

if __name__ == "__main__":
    main()