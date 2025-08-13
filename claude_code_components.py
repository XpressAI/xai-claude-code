import os
import subprocess
import re
import shutil

from xai_components.base import InArg, OutArg, InCompArg, Component, xai_component


def ensure_claude_code_available(ctx):
    """
    Ensures Claude Code CLI is installed and ANTHROPIC_API_KEY is set.
    Installs Claude Code to ~/.claude_code/ to avoid conflicts with other installations.
    Stores the claude command path in the provided context for thread safety.
    
    Args:
        ctx: Component execution context to store claude command path.
    
    Raises:
        RuntimeError: If Claude Code is not installed or API key is missing.
        
    Returns:
        bool: True if everything is properly configured.
    """
    # Check if ANTHROPIC_API_KEY is set
    if not os.environ.get('ANTHROPIC_API_KEY'):
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Please set your Anthropic API key before using Claude Code components."
        )
    
    # Define local installation directory
    home_dir = os.path.expanduser("~")
    claude_dir = os.path.join(home_dir, ".claude_code")
    node_modules_dir = os.path.join(claude_dir, "node_modules")
    claude_bin = os.path.join(node_modules_dir, ".bin", "claude")
    
    # Check if claude command is available in local installation first, then global PATH
    claude_cmd = None
    if os.path.exists(claude_bin) and os.access(claude_bin, os.X_OK):
        claude_cmd = claude_bin
    else:
        global_claude = shutil.which('claude')
        if global_claude:
            # Test if global installation actually works
            try:
                test_result = subprocess.run(
                    [global_claude, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if test_result.returncode == 0:
                    claude_cmd = global_claude
            except:
                # Global installation is broken, ignore it
                pass
    
    if not claude_cmd:
        # Attempt to install claude-code locally
        try:
            print("Claude Code CLI not found. Installing to ~/.claude_code/...")
            
            # Create directory if it doesn't exist
            os.makedirs(claude_dir, exist_ok=True)
            
            # Install locally using npm with --prefix to specify the directory
            result = subprocess.run(
                ['npm', 'install', '--prefix', claude_dir, '@anthropic-ai/claude-code'],
                capture_output=True,
                text=True,
                check=True
            )
            print("Claude Code CLI installed successfully to ~/.claude_code/")
            
            # Verify installation
            if not (os.path.exists(claude_bin) and os.access(claude_bin, os.X_OK)):
                raise RuntimeError(
                    "Failed to install Claude Code CLI. Please install manually: "
                    "npm install -g @anthropic-ai/claude-code"
                )
            claude_cmd = claude_bin
                
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to install Claude Code CLI: {e.stderr}. "
                "Please ensure npm is installed and try manually: "
                "npm install -g @anthropic-ai/claude-code"
            )
        except FileNotFoundError:
            raise RuntimeError(
                "npm command not found. Please install Node.js and npm, then try manually: "
                "npm install -g @anthropic-ai/claude-code"
            )
        except Exception as e:
            raise RuntimeError(
                f"Error during Claude Code installation: {str(e)}. "
                "Please install manually: npm install -g @anthropic-ai/claude-code"
            )
    
    # Verify claude command works
    try:
        result = subprocess.run(
            [claude_cmd, '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Claude Code CLI is installed but not working properly: {result.stderr}"
            )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Claude Code CLI is not responding. Please check your installation.")
    except Exception as e:
        raise RuntimeError(f"Error verifying Claude Code CLI: {str(e)}")
    
    # Store the claude command path in the context for thread safety
    ctx['claude_cmd'] = claude_cmd
    
    return True


def get_claude_config(ctx, key=None, default=None):
    """
    Retrieves Claude Code configuration from context.
    
    Args:
        ctx: Component execution context.
        key: Specific config key to retrieve, or None for entire config.
        default: Default value if key is not found.
        
    Returns:
        Configuration value or entire config dict.
        
    Raises:
        RuntimeError: If no configuration found and no default provided.
    """
    if 'claude_config' not in ctx:
        if default is not None:
            return default
        raise RuntimeError(
            "Claude Code configuration not found in context. "
            "Please add a ClaudeCodeInit component before other Claude Code components."
        )
    
    config = ctx['claude_config']
    
    if key is None:
        return config
    
    return config.get(key, default)


@xai_component
class ClaudeCodeInit(Component):
    """Initializes Claude Code configuration that will be shared across all Claude components.
    
    This component should be used once at the beginning of a workflow to set common
    configuration values that other Claude Code components will use. Values are stored
    in the execution context and automatically picked up by other components.

    ##### inPorts:
    - model: Model alias (e.g. 'sonnet', 'opus') or full name (e.g. 'claude-sonnet-4-20250514').
    - working_dir: Default working directory for Claude Code operations.
    - timeout: Default timeout in seconds for Claude Code commands.
    - api_key: Optional ANTHROPIC_API_KEY override (will use OAuth/tokens if not provided).
    - verbose: Enable verbose logging.
    - debug: Enable debug mode.

    ##### outPorts:
    - success: Whether the initialization was successful.
    - config_summary: Summary of the configuration that was set.
    """
    
    model: InArg[str]
    working_dir: InArg[str]
    timeout: InArg[int]
    api_key: InArg[str]
    verbose: InArg[bool]
    debug: InArg[bool]
    
    success: OutArg[bool]
    config_summary: OutArg[str]

    def execute(self, ctx) -> None:
        try:
            # Set API key in environment if provided
            if self.api_key.value:
                os.environ['ANTHROPIC_API_KEY'] = self.api_key.value
            
            # Store configuration in context
            ctx['claude_config'] = {
                'model': self.model.value,
                'working_dir': self.working_dir.value or os.getcwd(),
                'timeout': self.timeout.value or 120,
                'output_format': 'json',
                'verbose': self.verbose.value or False,
                'debug': self.debug.value or False,
            }
            
            # Ensure Claude Code is available and properly configured
            ensure_claude_code_available(ctx)
            
            self.success.value = True
            
            # Create configuration summary
            config = ctx['claude_config']
            summary = f"""Claude Code Configuration:
Model: {config['model'] or 'default'}
Working Directory: {config['working_dir']}
Timeout: {config['timeout']} seconds
Output Format: json (required)
Verbose: {config['verbose']}
Debug: {config['debug']}
Claude Command: {ctx['claude_cmd']}"""
            
            self.config_summary.value = summary
            
        except Exception as e:
            self.success.value = False
            self.config_summary.value = f"Initialization failed: {str(e)}"


@xai_component
class ClaudeCodeChat(Component):
    """Chat interface to Claude Code CLI with built-in analysis of results.
    
    Executes Claude Code commands and automatically analyzes the JSON response
    to extract cost information, file edits, and other metadata.
    Uses configuration from ClaudeCodeInit component.

    ##### inPorts:
    - prompt: The prompt/question to send to Claude.
    - system_prompt: Optional system prompt to append (uses --append-system-prompt).
    - session_id: Optional session ID to resume a conversation (uses --resume).
    - continue_conversation: Use --continue to continue the most recent conversation.

    ##### outPorts:
    - response: Claude's response to the prompt.
    - success: Whether the chat was successful.
    - input_tokens: Number of input tokens used.
    - output_tokens: Number of output tokens used.
    - total_cost: Total cost of the operation in USD.
    - files_edited: List of files that were edited.
    - edit_summary: Summary of edits made.
    - has_errors: Boolean indicating if there were errors.
    - raw_output: The raw JSON output from Claude Code.
    - session_id_out: The session ID of this conversation for future resumption.
    """
    
    prompt: InCompArg[str]
    system_prompt: InArg[str]
    session_id: InArg[str]
    continue_conversation: InArg[bool]
    
    response: OutArg[str]
    success: OutArg[bool]
    input_tokens: OutArg[int]
    output_tokens: OutArg[int]
    total_cost: OutArg[float]
    files_edited: OutArg[list]
    edit_summary: OutArg[str]
    has_errors: OutArg[bool]
    raw_output: OutArg[str]
    session_id_out: OutArg[str]

    def execute(self, ctx) -> None:
        import json
        
        # Get shared configuration from context
        model = get_claude_config(ctx, 'model')
        working_dir = get_claude_config(ctx, 'working_dir', os.getcwd())
        timeout = get_claude_config(ctx, 'timeout', 120)
        verbose = get_claude_config(ctx, 'verbose', False)
        debug = get_claude_config(ctx, 'debug', False)
        
        # Initialize all outputs
        self.input_tokens.value = 0
        self.output_tokens.value = 0
        self.total_cost.value = 0.0
        self.files_edited.value = []
        self.edit_summary.value = ""
        self.has_errors.value = False
        self.raw_output.value = ""
        self.session_id_out.value = ""
        
        # Ensure claude command is available in context
        if 'claude_cmd' not in ctx:
            ensure_claude_code_available(ctx)
        
        # Build command: claude --print --permission-mode bypassPermissions [options] "prompt"
        cmd_parts = [ctx['claude_cmd'], '--print', '--permission-mode', 'bypassPermissions']
        
        # Add current working directory to allowed directories
        cmd_parts.extend(['--add-dir', working_dir])
        
        if debug:
            cmd_parts.append('--debug')
        if verbose:
            cmd_parts.append('--verbose')
        if model:
            cmd_parts.extend(['--model', model])
        cmd_parts.extend(['--output-format', 'json'])
        
        # Add session management options
        if self.continue_conversation.value:
            cmd_parts.append('--continue')
        elif self.session_id.value:
            cmd_parts.extend(['--resume', self.session_id.value])
        
        # Add system prompt if provided
        if self.system_prompt.value:
            cmd_parts.extend(['--append-system-prompt', self.system_prompt.value])
        
        # Add the prompt
        cmd_parts.append(self.prompt.value)
        
        try:
            result = subprocess.run(
                cmd_parts,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output_text = result.stdout
            error_text = result.stderr
            
            self.raw_output.value = output_text
            self.has_errors.value = bool(error_text)
            self.success.value = result.returncode == 0
            
            # Try to parse JSON output and analyze it
            try:
                if output_text.strip():
                    data = json.loads(output_text)
                    
                    # Extract the actual response/result from JSON
                    if 'result' in data:
                        self.response.value = data['result']
                    elif data.get('subtype') == 'error_during_execution':
                        # For error_during_execution, show a helpful message instead of raw JSON
                        self.response.value = "Claude Code completed but encountered an error during execution. Check raw_output for details."
                    else:
                        self.response.value = output_text
                    
                    # Extract usage information from JSON
                    if 'usage' in data:
                        usage = data['usage']
                        self.input_tokens.value = usage.get('input_tokens', 0)
                        self.output_tokens.value = usage.get('output_tokens', 0)
                    
                    # Extract cost from root level
                    self.total_cost.value = data.get('total_cost_usd', 0.0)
                    
                    # Extract session ID for future resumption
                    self.session_id_out.value = data.get('session_id', '')
                    
                    # Extract tool calls and file operations
                    edited_files = set()
                    if 'tool_calls' in data:
                        for tool_call in data['tool_calls']:
                            if tool_call.get('name') in ['Edit', 'Write', 'MultiEdit']:
                                if 'parameters' in tool_call:
                                    file_path = tool_call['parameters'].get('file_path')
                                    if file_path:
                                        edited_files.add(file_path)
                    
                    self.files_edited.value = list(edited_files)
                    
                    # Generate edit summary
                    if edited_files:
                        self.edit_summary.value = f"Edited {len(edited_files)} file(s): {', '.join(edited_files)}"
                    else:
                        self.edit_summary.value = "No files were edited"
                        
            except json.JSONDecodeError:
                # Fallback: use raw output as response
                self.response.value = output_text
                
                # Fallback to text parsing if JSON parsing fails
                token_patterns = [
                    r'Input tokens:\s*(\d+)',
                    r'Output tokens:\s*(\d+)',
                    r'Total cost:\s*\$?([\d.]+)',
                    r'(\d+)\s*input\s*tokens',
                    r'(\d+)\s*output\s*tokens'
                ]
                
                for pattern in token_patterns:
                    matches = re.findall(pattern, output_text, re.IGNORECASE)
                    if matches:
                        if 'input' in pattern.lower():
                            self.input_tokens.value = int(matches[0])
                        elif 'output' in pattern.lower():
                            self.output_tokens.value = int(matches[0])
                        elif 'cost' in pattern.lower():
                            self.total_cost.value = float(matches[0])
                
                # Extract file edit information using regex patterns
                file_patterns = [
                    r'Edited:\s*([^\n]+)',
                    r'Modified:\s*([^\n]+)',
                    r'Writing to:\s*([^\n]+)',
                    r'Created:\s*([^\n]+)'
                ]
                
                edited_files = set()
                for pattern in file_patterns:
                    matches = re.findall(pattern, output_text, re.IGNORECASE)
                    edited_files.update(matches)
                
                self.files_edited.value = list(edited_files)
                
                # Generate edit summary
                if edited_files:
                    self.edit_summary.value = f"Edited {len(edited_files)} file(s): {', '.join(edited_files)}"
                else:
                    self.edit_summary.value = "No files were edited"
            
        except Exception as e:
            self.response.value = f"Error: {str(e)}"
            self.success.value = False
            self.has_errors.value = True
