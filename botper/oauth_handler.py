#!/usr/bin/env python3
"""
OAuth handler for Webex Integration
This handles OAuth flow to get user tokens for creating meetings
"""
import os
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

class WebexOAuthHandler:
    def __init__(self):
        self.client_id = os.getenv("WEBEX_CLIENT_ID")
        self.client_secret = os.getenv("WEBEX_CLIENT_SECRET")
        self.redirect_uri = os.getenv("WEBEX_REDIRECT_URI", "http://localhost:8000/auth/webex/callback")
        self.base_url = "https://webexapis.com/v1"
        
        if not self.client_id or not self.client_secret:
            print("Warning: WEBEX_CLIENT_ID and WEBEX_CLIENT_SECRET not found in environment")
        
    def get_authorization_url(self, state=None):
        """Generate the authorization URL for OAuth flow"""
        if not self.client_id:
            raise Exception("WEBEX_CLIENT_ID not configured")
            
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': 'spark:messages_read spark:messages_write spark:rooms_read spark:people_read meeting:schedules_write meeting:schedules_read',
        }
        
        if state:
            params['state'] = state
            
        auth_url = f"https://webexapis.com/v1/authorize?{urlencode(params)}"
        return auth_url
    
    def exchange_code_for_token(self, authorization_code):
        """Exchange authorization code for access token"""
        if not self.client_id or not self.client_secret:
            raise Exception("OAuth credentials not configured")
            
        token_url = f"{self.base_url}/access_token"
        
        data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': authorization_code,
            'redirect_uri': self.redirect_uri
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            return {
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'expires_in': token_data.get('expires_in'),
                'token_type': token_data.get('token_type')
            }
        else:
            raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")
    
    def refresh_access_token(self, refresh_token):
        """Refresh an expired access token"""
        if not self.client_id or not self.client_secret:
            raise Exception("OAuth credentials not configured")
            
        token_url = f"{self.base_url}/access_token"
        
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            return {
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'expires_in': token_data.get('expires_in'),
                'token_type': token_data.get('token_type')
            }
        else:
            raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")
    
    def get_user_info(self, access_token):
        """Get information about the authenticated user"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(f"{self.base_url}/people/me", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get user info: {response.status_code} - {response.text}")

    def create_meeting(self, access_token, meeting_details):
        """Create a Webex meeting using user's OAuth token"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(f"{self.base_url}/meetings", headers=headers, json=meeting_details)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to create meeting: {response.status_code} - {response.text}")