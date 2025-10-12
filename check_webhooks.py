#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()

WEBEX_BOT_TOKEN = os.getenv("WEBEX_BOT_TOKEN")

def list_webhooks():
    headers = {
        'Authorization': f'Bearer {WEBEX_BOT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get('https://webexapis.com/v1/webhooks', headers=headers)
    if response.status_code == 200:
        webhooks = response.json().get('items', [])
        print(f"Found {len(webhooks)} webhooks:")
        for webhook in webhooks:
            print(f"  - {webhook['name']}: {webhook['resource']} -> {webhook['targetUrl']} (ID: {webhook['id']})")
        return webhooks
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return []

if __name__ == "__main__":
    list_webhooks()