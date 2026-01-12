"""
Integration test for MCP tools with OAuth functionality.
Tests all the tools exposed by the MCP server.
"""

import sys
import os
import main

sys.path.append(os.getcwd())


def test_all_mcp_tools():
    """Test that all MCP tools are accessible and callable."""
    
    print("Testing MCP Tools Integration\n")
    print("=" * 70)
    
    # Test 1: get_consent_prompt
    print("\n1. Testing get_consent_prompt()...")
    try:
        result = main.get_consent_prompt()
        assert isinstance(result, str)
        assert "Google Calendar" in result
        assert "Gmail" in result
        assert "Do you accept" in result
        print("✓ get_consent_prompt() works correctly")
        print(f"   Preview: {result[:100]}...")
    except Exception as e:
        print(f"✗ get_consent_prompt() failed: {e}")
        return False
    
    # Test 2: check_authentication_status
    print("\n2. Testing check_authentication_status()...")
    try:
        result = main.check_authentication_status()
        assert isinstance(result, str)
        print("✓ check_authentication_status() works correctly")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"✗ check_authentication_status() failed: {e}")
        return False
    
    # Test 3: get_welcome_message
    print("\n3. Testing get_welcome_message()...")
    try:
        result = main.get_welcome_message()
        assert isinstance(result, str)
        print("✓ get_welcome_message() works correctly")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"✗ get_welcome_message() failed: {e}")
        return False
    
    # Test 4: start_oauth_flow (expected to fail without credentials.json)
    print("\n4. Testing start_oauth_flow()...")
    try:
        result = main.start_oauth_flow()
        assert isinstance(result, str)
        print("✓ start_oauth_flow() handles missing credentials gracefully")
        print(f"   Result: {result[:80]}...")
    except Exception as e:
        print(f"✗ start_oauth_flow() failed: {e}")
        return False
    
    # Test 5: Original calendar tools still work
    print("\n5. Testing original calendar tools...")
    try:
        # Test add_event
        result = main.add_event("Test Event", "2026-02-01", "Test description")
        assert "added" in result.lower()
        print("✓ add_event() works correctly")
        
        # Test view_events
        result = main.view_events()
        assert "Test Event" in result
        print("✓ view_events() works correctly")
        
        # Test delete_event
        result = main.delete_event("Test Event")
        assert "deleted" in result.lower()
        print("✓ delete_event() works correctly")
        
        # Test summarize_events
        result = main.summarize_events()
        assert isinstance(result, str)
        print("✓ summarize_events() works correctly")
        
    except Exception as e:
        print(f"✗ Calendar tools failed: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✓ All MCP tools integration tests passed!")
    return True


def test_oauth_flow_sequence():
    """Test the complete OAuth flow sequence."""
    
    print("\n\nTesting OAuth Flow Sequence\n")
    print("=" * 70)
    
    print("\nStep 1: Show consent prompt")
    consent = main.get_consent_prompt()
    print(consent)
    
    print("\n" + "-" * 70)
    print("Step 2: Check authentication status (before auth)")
    status = main.check_authentication_status()
    print(status)
    
    print("\n" + "-" * 70)
    print("Step 3: Start OAuth flow")
    oauth_start = main.start_oauth_flow()
    print(oauth_start[:200] + "...")
    
    print("\n" + "-" * 70)
    print("Step 4: Get welcome message (not authenticated)")
    welcome = main.get_welcome_message()
    print(welcome)
    
    print("\n" + "=" * 70)
    print("✓ OAuth flow sequence test completed")


if __name__ == "__main__":
    print("Running MCP Integration Tests\n")
    
    try:
        success = test_all_mcp_tools()
        if success:
            test_oauth_flow_sequence()
            print("\n\n🎉 All tests completed successfully!")
            sys.exit(0)
        else:
            print("\n\n✗ Some tests failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
