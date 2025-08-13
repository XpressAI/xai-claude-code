#!/usr/bin/env python3
"""
Test script for Claude Code session management and system prompt features.
"""

import os
import tempfile
import shutil
from claude_code_components import ClaudeCodeInit, ClaudeCodeChat

def test_session_management():
    """Test session management and system prompt features."""
    
    # Create a temporary testing directory
    test_dir = os.path.join(tempfile.gettempdir(), 'claude_session_test')
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    print(f"Created test directory: {test_dir}")
    
    # Mock context (like what Xircuits would provide)
    ctx = {}
    
    try:
        # Test 1: Initialize Claude Code configuration
        print("\n=== Testing ClaudeCodeInit ===")
        init_component = ClaudeCodeInit()
        
        # Set input values
        init_component.model.value = "sonnet"
        init_component.working_dir.value = test_dir
        init_component.timeout.value = 60
        init_component.api_key.value = None  # Use environment variable
        init_component.verbose.value = False
        init_component.debug.value = False
        
        # Execute initialization
        init_component.execute(ctx)
        
        print(f"Init Success: {init_component.success.value}")
        if not init_component.success.value:
            print("❌ Initialization failed!")
            return
        
        # Test 2: Chat with system prompt
        print("\n=== Testing ClaudeCodeChat with System Prompt ===")
        chat_component1 = ClaudeCodeChat()
        
        # Set up first conversation with system prompt
        chat_component1.prompt.value = "What programming language should I use for data analysis?"
        chat_component1.system_prompt.value = "You are a helpful programming mentor. Always recommend Python for data analysis and explain why."
        chat_component1.continue_conversation.value = False
        chat_component1.session_id.value = None
        
        # Execute the chat
        chat_component1.execute(ctx)
        
        print(f"Chat 1 Success: {chat_component1.success.value}")
        print(f"Response: {chat_component1.response.value}")
        print(f"Session ID: {chat_component1.session_id_out.value}")
        print(f"Total Cost: ${chat_component1.total_cost.value:.6f}")
        
        # Save the session ID for resumption
        session_id = chat_component1.session_id_out.value
        
        if session_id:
            # Test 3: Resume the conversation
            print(f"\n=== Testing Session Resumption with ID: {session_id} ===")
            chat_component2 = ClaudeCodeChat()
            
            # Resume the conversation
            chat_component2.prompt.value = "Can you give me a specific example with pandas?"
            chat_component2.system_prompt.value = None  # Should use the system prompt from the original session
            chat_component2.continue_conversation.value = False
            chat_component2.session_id.value = session_id
            
            # Execute the resumed chat
            chat_component2.execute(ctx)
            
            print(f"Chat 2 (Resumed) Success: {chat_component2.success.value}")
            print(f"Response: {chat_component2.response.value}")
            print(f"Session ID: {chat_component2.session_id_out.value}")
            print(f"Total Cost: ${chat_component2.total_cost.value:.6f}")
        
        # Test 4: Continue most recent conversation
        print("\n=== Testing Continue Most Recent Conversation ===")
        chat_component3 = ClaudeCodeChat()
        
        # Continue the most recent conversation
        chat_component3.prompt.value = "What about data visualization libraries?"
        chat_component3.system_prompt.value = None
        chat_component3.continue_conversation.value = True
        chat_component3.session_id.value = None
        
        # Execute the continued chat
        chat_component3.execute(ctx)
        
        print(f"Chat 3 (Continue) Success: {chat_component3.success.value}")
        print(f"Response: {chat_component3.response.value}")
        print(f"Session ID: {chat_component3.session_id_out.value}")
        print(f"Total Cost: ${chat_component3.total_cost.value:.6f}")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print(f"\n=== Cleanup ===")
        if os.path.exists(test_dir):
            print(f"Cleaning up test directory: {test_dir}")
            shutil.rmtree(test_dir)
        print("Session management test completed!")

if __name__ == "__main__":
    print("Claude Code Session Management Test")
    print("=" * 50)
    
    # Check if ANTHROPIC_API_KEY is set
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("❌ ANTHROPIC_API_KEY environment variable is not set!")
        print("Please set your Anthropic API key before running this test.")
        exit(1)
    
    print("✅ ANTHROPIC_API_KEY is set")
    
    test_session_management()