"""OAuth 2.0 handler for Google Calendar and Gmail access."""
import os
import json
from pathlib import Path
from typing import Optional, Dict
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


# OAuth 2.0 scopes for calendar and Gmail access
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.profile',
]

# File to store user credentials
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'


class OAuthHandler:
    """Handles OAuth 2.0 authentication flow for Google services."""
    
    def __init__(self):
        self.credentials: Optional[Credentials] = None
        self.user_info: Optional[Dict] = None
        
    def get_authorization_url(self) -> str:
        """
        Initiates the OAuth flow and returns the authorization URL.
        
        Returns:
            str: Authorization URL for user to grant permissions
        """
        if not os.path.exists(CREDENTIALS_FILE):
            raise FileNotFoundError(
                f"Missing {CREDENTIALS_FILE}. Please download it from Google Cloud Console."
            )
        
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return auth_url
    
    def exchange_code_for_token(self, auth_code: str) -> bool:
        """
        Exchanges authorization code for access token.
        
        Args:
            auth_code: Authorization code from OAuth callback
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            flow = Flow.from_client_secrets_file(
                CREDENTIALS_FILE,
                scopes=SCOPES,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'
            )
            
            flow.fetch_token(code=auth_code)
            self.credentials = flow.credentials
            
            # Save credentials for future use
            self._save_credentials()
            
            # Fetch user info
            self._fetch_user_info()
            
            return True
        except Exception as e:
            print(f"Error exchanging code for token: {e}")
            return False
    
    def load_credentials(self) -> bool:
        """
        Loads credentials from token file if it exists.
        
        Returns:
            bool: True if credentials loaded successfully, False otherwise
        """
        if os.path.exists(TOKEN_FILE):
            try:
                self.credentials = Credentials.from_authorized_user_file(
                    TOKEN_FILE, SCOPES
                )
                if self.credentials and self.credentials.valid:
                    self._fetch_user_info()
                    return True
            except Exception as e:
                print(f"Error loading credentials: {e}")
        return False
    
    def _save_credentials(self):
        """Saves credentials to token file."""
        if self.credentials:
            token_data = {
                'token': self.credentials.token,
                'refresh_token': self.credentials.refresh_token,
                'token_uri': self.credentials.token_uri,
                'client_id': self.credentials.client_id,
                'client_secret': self.credentials.client_secret,
                'scopes': self.credentials.scopes
            }
            with open(TOKEN_FILE, 'w') as token_file:
                json.dump(token_data, token_file)
    
    def _fetch_user_info(self):
        """Fetches user profile information from Google."""
        if not self.credentials:
            return
        
        try:
            service = build('oauth2', 'v2', credentials=self.credentials)
            user_info = service.userinfo().get().execute()
            self.user_info = user_info
        except Exception as e:
            print(f"Error fetching user info: {e}")
    
    def get_user_first_name(self) -> Optional[str]:
        """
        Returns the user's first name.
        
        Returns:
            Optional[str]: User's first name or None if not available
        """
        if self.user_info:
            return self.user_info.get('given_name')
        return None
    
    def get_welcome_message(self) -> str:
        """
        Generates a welcome message with user's first name.
        
        Returns:
            str: Welcome message
        """
        first_name = self.get_user_first_name()
        if first_name:
            return f"Welcome, {first_name}! You are now connected to your calendar and email."
        return "Welcome! You are now connected to your calendar and email."
    
    def is_authenticated(self) -> bool:
        """
        Checks if user is authenticated.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        return self.credentials is not None and self.credentials.valid
    
    def get_consent_message(self) -> str:
        """
        Returns the consent message asking for permission.
        
        Returns:
            str: Consent message
        """
        return (
            "This application would like to access your Google Calendar and Gmail account.\n\n"
            "Permissions requested:\n"
            "- Read and manage your calendar events\n"
            "- Read your email messages\n"
            "- Access your basic profile information\n\n"
            "Do you accept the connection to your email account and calendar?"
        )


# Global OAuth handler instance
oauth_handler = OAuthHandler()
