"""
Demonstration script showing the OAuth 2.0 flow with welcome message and consent prompt.

This script demonstrates the user experience flow:
1. Display consent prompt
2. User accepts/declines
3. If accepted, start OAuth flow
4. Complete authentication
5. Display welcome message with user's first name
"""

import sys
import os

sys.path.append(os.getcwd())

from oauth_handler import oauth_handler


def demonstrate_flow():
    """Demonstrate the complete OAuth flow."""
    
    print("=" * 70)
    print("Calendar MCP Server - OAuth 2.0 Authentication Flow Demonstration")
    print("=" * 70)
    print()
    
    # Step 1: Check if already authenticated
    print("Step 1: Checking authentication status...")
    if oauth_handler.load_credentials() and oauth_handler.is_authenticated():
        print("✓ Already authenticated!")
        print()
        print(oauth_handler.get_welcome_message())
        return
    
    print("Not authenticated. Starting authentication flow...")
    print()
    
    # Step 2: Display consent prompt
    print("Step 2: Consent Prompt")
    print("-" * 70)
    print(oauth_handler.get_consent_message())
    print("-" * 70)
    print()
    
    # Simulate user response
    print("Waiting for user consent...")
    print("(In a real application, the user would click 'Accept' or 'Decline')")
    print()
    
    response = input("Do you accept? (yes/no): ").lower().strip()
    
    if response not in ['yes', 'y']:
        print("\n✗ User declined. Authentication cancelled.")
        return
    
    print("\n✓ User accepted!")
    print()
    
    # Step 3: Start OAuth flow
    print("Step 3: Starting OAuth Flow")
    print("-" * 70)
    print("Note: This requires a credentials.json file from Google Cloud Console.")
    print()
    
    try:
        auth_url = oauth_handler.get_authorization_url()
        print("Authorization URL generated:")
        print(auth_url)
        print()
        print("In a real flow, the user would:")
        print("1. Visit this URL")
        print("2. Sign in to their Google account")
        print("3. Grant permissions")
        print("4. Receive an authorization code")
        print("5. Enter the code to complete authentication")
        print()
        
        # In a real implementation, this would be automated
        # For this demo, we'll stop here
        print("(Demo ends here - credentials.json not present)")
        
    except FileNotFoundError:
        print("⚠ credentials.json not found.")
        print()
        print("To complete the setup:")
        print("1. Go to Google Cloud Console")
        print("2. Create OAuth 2.0 credentials")
        print("3. Download as credentials.json")
        print("4. Place it in the project root")
        print()
        print("Once authenticated, the user would see:")
        print("-" * 70)
        print("Welcome, [FirstName]! You are now connected to your calendar and email.")
        print("-" * 70)
    
    print()
    print("=" * 70)
    print("End of Demonstration")
    print("=" * 70)


if __name__ == "__main__":
    demonstrate_flow()
