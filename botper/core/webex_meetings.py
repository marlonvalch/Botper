"""
Webex Meetings SDK Wrapper
Provides a clean interface for creating Webex video meetings
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

class WebexMeetingsSDK:
    """Enhanced SDK wrapper for Webex Meetings API"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://webexapis.com/v1"
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def create_meeting(self, 
                      title: str,
                      start_time: str,
                      end_time: str,
                      host_email: str,
                      participants: List[str] = None,
                      timezone: str = "UTC",
                      password: str = None,
                      enable_recording: bool = False) -> Dict:
        """
        Create a Webex video meeting
        
        Args:
            title: Meeting title
            start_time: ISO format datetime (2025-10-12T14:30:00.000Z)
            end_time: ISO format datetime 
            host_email: Email of meeting host
            participants: List of participant emails
            timezone: Meeting timezone (default UTC)
            password: Optional meeting password
            enable_recording: Whether to enable auto-recording
        
        Returns:
            Dict with meeting details (webLink, id, password, etc.)
        """
        
        meeting_data = {
            "title": title,
            "start": start_time,
            "end": end_time,
            "timezone": timezone,
            "hostEmail": host_email,
            "enabledAutoRecordMeeting": enable_recording,
            "allowFirstUserToBeCoHost": True,
            "allowAuthenticatedDevices": True,
            "sendEmail": True,
            "enabledJoinBeforeHost": True,
            "joinBeforeHostMinutes": 5,
            "enableConnectAudioBeforeHost": True,
            "excludePassword": False if password else True,
            "publicMeeting": False,
            "reminderTime": 15,
            "unlockedMeetingJoinSecurity": "allowJoinWithLobby",
            "sessionTypeId": 0,
            "enabledBreakoutSessions": True,
            "audioConnectionOptions": {
                "audioConnectionType": "webexAudio",
                "enabledTollFreeCallIn": True,
                "enabledGlobalCallIn": True,
                "enabledAudienceCallBack": True
            }
        }
        
        # Add custom password if provided
        if password:
            meeting_data["password"] = password
        
        # Add invitees if participants provided
        if participants:
            meeting_data["invitees"] = []
            for participant_email in participants:
                meeting_data["invitees"].append({
                    "email": participant_email,
                    "sendEmail": True,
                    "panelist": False,
                    "coHost": False
                })
        
        # Make API call
        response = requests.post(
            f"{self.base_url}/meetings",
            headers=self.headers,
            json=meeting_data
        )
        
        if response.status_code in [200, 201]:
            return {
                "success": True,
                "meeting": response.json(),
                "webLink": response.json().get('webLink'),
                "meetingId": response.json().get('id'),
                "password": response.json().get('password'),
                "joinUrl": response.json().get('webLink'),
                "hostKey": response.json().get('hostKey'),
                "sipAddress": response.json().get('sipAddress')
            }
        else:
            return {
                "success": False,
                "error": f"API Error {response.status_code}: {response.text}",
                "details": response.json() if response.text else None
            }
    
    def list_meetings(self, host_email: str = None, max_meetings: int = 100) -> Dict:
        """List meetings for a host or all meetings"""
        
        params = {"max": max_meetings}
        if host_email:
            params["hostEmail"] = host_email
            
        response = requests.get(
            f"{self.base_url}/meetings",
            headers=self.headers,
            params=params
        )
        
        if response.status_code == 200:
            return {
                "success": True,
                "meetings": response.json().get('items', [])
            }
        else:
            return {
                "success": False,
                "error": f"API Error {response.status_code}: {response.text}"
            }
    
    def get_meeting(self, meeting_id: str) -> Dict:
        """Get details of a specific meeting"""
        
        response = requests.get(
            f"{self.base_url}/meetings/{meeting_id}",
            headers=self.headers
        )
        
        if response.status_code == 200:
            return {
                "success": True,
                "meeting": response.json()
            }
        else:
            return {
                "success": False,
                "error": f"API Error {response.status_code}: {response.text}"
            }
    
    def delete_meeting(self, meeting_id: str) -> Dict:
        """Delete a meeting"""
        
        response = requests.delete(
            f"{self.base_url}/meetings/{meeting_id}",
            headers=self.headers
        )
        
        if response.status_code == 204:
            return {"success": True}
        else:
            return {
                "success": False,
                "error": f"API Error {response.status_code}: {response.text}"
            }
    
    def update_meeting(self, meeting_id: str, updates: Dict) -> Dict:
        """Update an existing meeting"""
        
        response = requests.patch(
            f"{self.base_url}/meetings/{meeting_id}",
            headers=self.headers,
            json=updates
        )
        
        if response.status_code == 200:
            return {
                "success": True,
                "meeting": response.json()
            }
        else:
            return {
                "success": False,
                "error": f"API Error {response.status_code}: {response.text}"
            }

    @staticmethod
    def format_datetime(date_str: str, time_str: str, timezone_offset: str = "UTC+00:00") -> tuple:
        """
        Convert date/time strings to ISO format for API
        
        Args:
            date_str: Date in YYYY-MM-DD format
            time_str: Time in HH:MM format
            timezone_offset: Timezone like "UTC-05:00"
        
        Returns:
            Tuple of (start_time_iso, end_time_iso)
        """
        try:
            # Parse the input datetime
            meeting_datetime_str = f"{date_str} {time_str}"
            local_dt = datetime.strptime(meeting_datetime_str, "%Y-%m-%d %H:%M")
            
            # Convert to UTC for Webex API
            if timezone_offset.startswith('UTC'):
                offset_str = timezone_offset.replace('UTC', '')
                if offset_str:
                    hours_offset = float(offset_str.replace(':', '.'))
                    utc_dt = local_dt - timedelta(hours=hours_offset)
                else:
                    utc_dt = local_dt
            else:
                utc_dt = local_dt  # Default to treating as UTC
            
            start_time = utc_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            end_time = (utc_dt + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            return start_time, end_time
            
        except Exception as e:
            # Fallback: create meeting for 1 hour from now
            now_utc = datetime.utcnow()
            start_time = now_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            end_time = (now_utc + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            return start_time, end_time

    def create_instant_meeting(self, title: str, host_email: str, participants: List[str] = None) -> Dict:
        """Create an instant meeting (starts now, 1 hour duration)"""
        
        try:
            now_utc = datetime.utcnow()
            start_time = now_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            end_time = (now_utc + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            result = self.create_meeting(
                title=title,
                start_time=start_time,
                end_time=end_time,
                host_email=host_email,
                participants=participants
            )
            
            # Check if meeting creation failed due to permissions
            if not result.get("success") and "403" in result.get("error", ""):
                return {
                    "success": False,
                    "error": "PERMISSION_ERROR",
                    "message": (
                        "❌ **BOT PERMISSION ERROR**\n\n"
                        "Your Webex bot token is missing **meeting API permissions**.\n\n"
                        "🔧 **TO FIX:**\n"
                        "1. Go to [developer.webex.com](https://developer.webex.com)\n"
                        "2. Edit your bot → **Scopes**\n"
                        "3. Add: `meeting:schedules_write` & `meeting:schedules_read`\n"
                        "4. **Regenerate** your bot token\n"
                        "5. Update your `.env` file\n\n"
                        "📞 **ALTERNATIVE:** Use `create space <name>` for a meeting space instead."
                    )
                }
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": "UNEXPECTED_ERROR",
                "message": f"Failed to create instant meeting: {str(e)}"
            }