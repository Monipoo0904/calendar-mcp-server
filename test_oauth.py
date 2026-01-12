"""Test script for OAuth functionality without actual credentials."""
import sys
import os
import main

sys.path.append(os.getcwd())

from oauth_handler import OAuthHandler


def test_oauth_handler_initialization():
    """Test that OAuthHandler can be initialized."""
    handler = OAuthHandler()
    assert handler is not None
    assert handler.credentials is None
    assert handler.user_info is None
    print("✓ OAuthHandler initialization test passed")


def test_consent_message():
    """Test that consent message is generated correctly."""
    handler = OAuthHandler()
    message = handler.get_consent_message()
    assert "Google Calendar" in message
    assert "Gmail" in message
    assert "Do you accept" in message
    print("✓ Consent message test passed")


def test_welcome_message_unauthenticated():
    """Test welcome message when user is not authenticated."""
    handler = OAuthHandler()
    message = handler.get_welcome_message()
    assert "Welcome" in message
    print("✓ Unauthenticated welcome message test passed")


def test_authentication_status():
    """Test authentication status check."""
    handler = OAuthHandler()
    assert not handler.is_authenticated()
    print("✓ Authentication status test passed")


def test_mcp_tools_import():
    """Test that main.py tools can be imported."""
    # Check that new tools exist
    assert hasattr(main, 'get_consent_prompt')
    assert hasattr(main, 'start_oauth_flow')
    assert hasattr(main, 'complete_oauth_flow')
    assert hasattr(main, 'get_welcome_message')
    assert hasattr(main, 'check_authentication_status')
    print("✓ MCP tools import test passed")


if __name__ == "__main__":
    print("Running OAuth handler tests...\n")
    
    try:
        test_oauth_handler_initialization()
        test_consent_message()
        test_welcome_message_unauthenticated()
        test_authentication_status()
        test_mcp_tools_import()
        
        print("\n✓ All tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
