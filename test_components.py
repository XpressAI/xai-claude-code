#!/usr/bin/env python3
"""
Test script for Claude Code components.
Creates a testing folder and uses Claude to create a hello world script.
"""

import os
import shutil
import tempfile
from claude_code_components import ClaudeCodeInit, ClaudeCodeChat

def test_claude_components():
    """Test the Claude Code components by creating a hello world script."""
    
    # Create a temporary testing directory
    test_dir = os.path.join(tempfile.gettempdir(), 'claude_code_test')
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
        print(f"Config Summary:\n{init_component.config_summary.value}")
        
        if not init_component.success.value:
            print("❌ Initialization failed!")
            return
        
        # Test 2: Use Claude to create a hello world Python script
        print("\n=== Testing ClaudeCodeChat - Create Hello World Script ===")
        chat_component = ClaudeCodeChat()
        
        # Create a prompt to generate a hello world script
        prompt = """Please create a simple Python hello world script and save it as 'hello.py' in the current directory. 
The script should:
1. Print "Hello, World!" 
2. Print the current date and time
3. Ask for the user's name and greet them personally

Just create the file, don't explain the code."""
        
        chat_component.prompt.value = prompt
        
        # Execute the chat
        chat_component.execute(ctx)
        
        print(f"Chat Success: {chat_component.success.value}")
        print(f"Response:\n{chat_component.response.value}")
        
        # Test 3: Ask Claude to list the files in the directory
        print("\n=== Testing ClaudeCodeChat - List Files ===")
        list_component = ClaudeCodeChat()
        list_component.prompt.value = "List all files in the current directory"
        list_component.execute(ctx)
        
        print(f"List Success: {list_component.success.value}")
        print(f"Files listed:\n{list_component.response.value}")
        
        # Check if the hello.py file was actually created
        hello_file = os.path.join(test_dir, 'hello.py')
        if os.path.exists(hello_file):
            print(f"\n✅ Success! hello.py was created at: {hello_file}")
            with open(hello_file, 'r') as f:
                content = f.read()
            print(f"File content:\n{content}")
        else:
            print(f"\n❌ hello.py was not found in {test_dir}")
            # List actual files in directory
            actual_files = os.listdir(test_dir)
            print(f"Actual files in directory: {actual_files}")
        
        # Test 4: Ask Claude to run the script (if it exists)
        if os.path.exists(hello_file):
            print("\n=== Testing ClaudeCodeChat - Run Script ===")
            run_component = ClaudeCodeChat()
            run_component.prompt.value = "Run the hello.py script and show me the output"
            run_component.execute(ctx)
            
            print(f"Run Success: {run_component.success.value}")
            print(f"Run Result:\n{run_component.response.value}")
        
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
        print("Test completed!")

if __name__ == "__main__":
    print("Claude Code Components Test")
    print("=" * 40)
    
    # Check if ANTHROPIC_API_KEY is set
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("❌ ANTHROPIC_API_KEY environment variable is not set!")
        print("Please set your Anthropic API key before running this test.")
        exit(1)
    
    print("✅ ANTHROPIC_API_KEY is set")
    
    test_claude_components()