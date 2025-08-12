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
            
            # Install locally using npm
            result = subprocess.run(
                ['npm', 'install', '@anthropic-ai/claude-code'],
                cwd=claude_dir,
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
class ClaudeCodeExecute(Component):
    """Executes Claude Code CLI with custom options and prompt.
    
    Uses configuration from ClaudeCodeInit component. Executes: claude [options] [prompt]
    Uses --print mode for non-interactive execution.

    ##### inPorts:
    - prompt: The prompt to send to Claude.
    - print_mode: Use --print for non-interactive output (default: True).
    - continue_conversation: Use --continue to continue most recent conversation.
    - resume_session: Session ID to resume with --resume.
    - additional_options: Additional CLI options as string (e.g. "--verbose --debug").

    ##### outPorts:
    - output: The stdout output from Claude.
    - error: The stderr output from the command.
    - return_code: The exit code of the command.
    - execution_time: Time taken to execute the command in seconds.
    """
    
    prompt: InCompArg[str]
    print_mode: InArg[bool]
    continue_conversation: InArg[bool]
    resume_session: InArg[str]
    additional_options: InArg[str]
    
    output: OutArg[str]
    error: OutArg[str]
    return_code: OutArg[int]
    execution_time: OutArg[float]

    def execute(self, ctx) -> None:
        import time
        
        # Get shared configuration from context
        working_dir = get_claude_config(ctx, 'working_dir', os.getcwd())
        timeout = get_claude_config(ctx, 'timeout', 120)
        model = get_claude_config(ctx, 'model')
        verbose = get_claude_config(ctx, 'verbose', False)
        debug = get_claude_config(ctx, 'debug', False)
        
        # Ensure claude command is available in context
        if 'claude_cmd' not in ctx:
            ensure_claude_code_available(ctx)
        
        # Build command: claude [options] [prompt]
        cmd_parts = [ctx['claude_cmd']]
        
        # Add default permission mode for automation
        cmd_parts.extend(['--permission-mode', 'bypassPermissions'])
        
        # Add current working directory to allowed directories
        cmd_parts.extend(['--add-dir', working_dir])
        
        # Add options
        if debug:
            cmd_parts.append('--debug')
        if verbose:
            cmd_parts.append('--verbose')
        if model:
            cmd_parts.extend(['--model', model])
        if self.print_mode.value is not False:  # Default to True
            cmd_parts.append('--print')
            cmd_parts.extend(['--output-format', 'json'])
        if self.continue_conversation.value:
            cmd_parts.append('--continue')
        if self.resume_session.value:
            cmd_parts.extend(['--resume', self.resume_session.value])
        if self.additional_options.value:
            cmd_parts.extend(self.additional_options.value.split())
        
        # Add prompt if provided
        if self.prompt.value:
            cmd_parts.append(self.prompt.value)
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd_parts,
                cwd=working_dir,
                timeout=timeout,
                capture_output=True,
                text=True
            )
            
            execution_time = time.time() - start_time
            
            self.output.value = result.stdout
            self.error.value = result.stderr
            self.return_code.value = result.returncode
            self.execution_time.value = execution_time
            
        except subprocess.TimeoutExpired as e:
            execution_time = time.time() - start_time
            self.output.value = ""
            self.error.value = f"Command timed out after {timeout} seconds"
            self.return_code.value = -1
            self.execution_time.value = execution_time
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.output.value = ""
            self.error.value = str(e)
            self.return_code.value = -1
            self.execution_time.value = execution_time


@xai_component
class ClaudeCodeAnalyze(Component):
    """Analyzes Claude Code output to extract cost information and edit details.

    ##### inPorts:
    - output: The stdout output from a Claude Code command.
    - error: The stderr output from a Claude Code command.

    ##### outPorts:
    - input_tokens: Number of input tokens used.
    - output_tokens: Number of output tokens used.
    - total_cost: Total cost of the operation in USD.
    - files_edited: List of files that were edited.
    - edit_summary: Summary of edits made.
    - has_errors: Boolean indicating if there were errors.
    - success: Boolean indicating if the command was successful.
    """
    
    output: InCompArg[str]
    error: InCompArg[str]
    
    input_tokens: OutArg[int]
    output_tokens: OutArg[int]
    total_cost: OutArg[float]
    files_edited: OutArg[list]
    edit_summary: OutArg[str]
    has_errors: OutArg[bool]
    success: OutArg[bool]

    def execute(self, ctx) -> None:
        import json
        
        # Ensure Claude Code is available and properly configured
        ensure_claude_code_available(ctx)
        
        output_text = self.output.value or ""
        error_text = self.error.value or ""
        
        # Initialize outputs
        self.input_tokens.value = 0
        self.output_tokens.value = 0
        self.total_cost.value = 0.0
        self.files_edited.value = []
        self.edit_summary.value = ""
        self.has_errors.value = bool(error_text)
        self.success.value = not bool(error_text)
        
        # Try to parse JSON output
        try:
            if output_text.strip():
                data = json.loads(output_text)
                
                # Extract usage information from JSON
                if 'usage' in data:
                    usage = data['usage']
                    self.input_tokens.value = usage.get('input_tokens', 0)
                    self.output_tokens.value = usage.get('output_tokens', 0)
                    self.total_cost.value = usage.get('total_cost', 0.0)
                
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
            # Fallback to text parsing if JSON parsing fails
            # Extract token usage information using regex patterns
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


@xai_component
class ClaudeCodeChat(Component):
    """Simple chat interface to Claude Code CLI using --print mode.
    
    Simplified wrapper around ClaudeCodeExecute for basic chat functionality.
    Uses configuration from ClaudeCodeInit component.

    ##### inPorts:
    - prompt: The prompt/question to send to Claude.

    ##### outPorts:
    - response: Claude's response to the prompt.
    - success: Whether the chat was successful.
    """
    
    prompt: InCompArg[str]
    
    response: OutArg[str]
    success: OutArg[bool]

    def execute(self, ctx) -> None:
        # Get shared configuration from context
        model = get_claude_config(ctx, 'model')
        working_dir = get_claude_config(ctx, 'working_dir', os.getcwd())
        timeout = get_claude_config(ctx, 'timeout', 120)
        verbose = get_claude_config(ctx, 'verbose', False)
        debug = get_claude_config(ctx, 'debug', False)
        
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
            
            self.response.value = result.stdout
            self.success.value = result.returncode == 0
            
        except Exception as e:
            self.response.value = f"Error: {str(e)}"
            self.success.value = False


@xai_component
class ClaudeCodeConfig(Component):
    """Manages Claude Code configuration using 'claude config' command.
    
    Uses the real 'claude config' command to get/set configuration values.

    ##### inPorts:
    - action: Action to perform: 'get' or 'set'.
    - key: Configuration key (e.g. 'theme', 'model').
    - value: Value to set (only used with 'set' action).
    - global_config: Use -g flag for global configuration.

    ##### outPorts:
    - success: Whether the config operation was successful.
    - result: The result of the config operation.
    """
    
    action: InCompArg[str]
    key: InCompArg[str]
    value: InArg[str]
    global_config: InArg[bool]
    
    success: OutArg[bool]
    result: OutArg[str]

    def execute(self, ctx) -> None:
        # Get shared configuration from context
        working_dir = get_claude_config(ctx, 'working_dir', os.getcwd())
        timeout = get_claude_config(ctx, 'timeout', 30)
        
        # Ensure claude command is available in context
        if 'claude_cmd' not in ctx:
            ensure_claude_code_available(ctx)
        
        # Build command: claude config [action] [options] [key] [value]
        cmd_parts = [ctx['claude_cmd'], 'config']
        
        if self.action.value:
            cmd_parts.append(self.action.value)
        
        if self.global_config.value:
            cmd_parts.append('-g')
            
        if self.key.value:
            cmd_parts.append(self.key.value)
            
        if self.action.value == 'set' and self.value.value:
            cmd_parts.append(self.value.value)
        
        try:
            result = subprocess.run(
                cmd_parts,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            self.success.value = result.returncode == 0
            self.result.value = result.stdout if result.stdout else result.stderr
            
        except Exception as e:
            self.success.value = False
            self.result.value = f"Error: {str(e)}"


@xai_component
class ClaudeCodeUpdate(Component):
    """Updates Claude Code to the latest version using 'claude update' command.

    ##### inPorts:
    - check_only: Only check for updates, don't install.

    ##### outPorts:
    - success: Whether the update operation was successful.
    - result: The result of the update operation.
    - update_available: Whether an update is available.
    """
    
    check_only: InArg[bool]
    
    success: OutArg[bool]
    result: OutArg[str]
    update_available: OutArg[bool]

    def execute(self, ctx) -> None:
        # Get shared configuration from context
        working_dir = get_claude_config(ctx, 'working_dir', os.getcwd())
        timeout = get_claude_config(ctx, 'timeout', 60)
        
        # Ensure claude command is available in context
        if 'claude_cmd' not in ctx:
            ensure_claude_code_available(ctx)
        
        # Build command: claude update
        cmd_parts = [ctx['claude_cmd'], 'update']
        
        try:
            result = subprocess.run(
                cmd_parts,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            self.success.value = result.returncode == 0
            output = result.stdout if result.stdout else result.stderr
            self.result.value = output
            
            # Check if update is available by looking at output
            self.update_available.value = 'available' in output.lower() or 'update' in output.lower()
            
        except Exception as e:
            self.success.value = False
            self.result.value = f"Error: {str(e)}"
            self.update_available.value = False


@xai_component
class ClaudeCodeDoctor(Component):
    """Runs Claude Code health check using 'claude doctor' command.

    ##### outPorts:
    - success: Whether Claude Code is healthy.
    - result: The health check results.
    """
    
    success: OutArg[bool]
    result: OutArg[str]

    def execute(self, ctx) -> None:
        # Get shared configuration from context
        working_dir = get_claude_config(ctx, 'working_dir', os.getcwd())
        timeout = get_claude_config(ctx, 'timeout', 30)
        
        # Ensure claude command is available in context
        if 'claude_cmd' not in ctx:
            ensure_claude_code_available(ctx)
        
        # Build command: claude doctor
        cmd_parts = [ctx['claude_cmd'], 'doctor']
        
        try:
            result = subprocess.run(
                cmd_parts,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            self.success.value = result.returncode == 0
            self.result.value = result.stdout if result.stdout else result.stderr
            
        except Exception as e:
            self.success.value = False
            self.result.value = f"Error: {str(e)}"