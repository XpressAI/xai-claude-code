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
    - model: The Claude model to use (e.g., "claude-3-5-sonnet-20241022").
    - working_dir: Default working directory for Claude Code operations.
    - timeout: Default timeout in seconds for Claude Code commands.
    - api_key: Optional ANTHROPIC_API_KEY override (will use environment if not provided).

    ##### outPorts:
    - success: Whether the initialization was successful.
    - config_summary: Summary of the configuration that was set.
    """
    
    model: InArg[str]
    working_dir: InArg[str]
    timeout: InArg[int]
    api_key: InArg[str]
    
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
                'timeout': self.timeout.value or 30,
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
Claude Command: {ctx['claude_cmd']}"""
            
            self.config_summary.value = summary
            
        except Exception as e:
            self.success.value = False
            self.config_summary.value = f"Initialization failed: {str(e)}"


@xai_component
class ClaudeCodeExecute(Component):
    """Executes a Claude Code CLI command and captures the output.
    
    Uses configuration from ClaudeCodeInit component. Requires ClaudeCodeInit to be
    executed first in the workflow.

    ##### inPorts:
    - command: The claude command to execute (e.g., "chat", "help").
    - args: Additional arguments to pass to the command.
    - input_text: Optional text to provide as input to the command.

    ##### outPorts:
    - output: The stdout output from the command.
    - error: The stderr output from the command.
    - return_code: The exit code of the command.
    - execution_time: Time taken to execute the command in seconds.
    """
    
    command: InCompArg[str]
    args: InArg[str]
    input_text: InArg[str]
    
    output: OutArg[str]
    error: OutArg[str]
    return_code: OutArg[int]
    execution_time: OutArg[float]

    def execute(self, ctx) -> None:
        import time
        
        # Get shared configuration from context
        working_dir = get_claude_config(ctx, 'working_dir', os.getcwd())
        timeout = get_claude_config(ctx, 'timeout', 30)
        
        # Ensure claude command is available in context
        if 'claude_cmd' not in ctx:
            ensure_claude_code_available(ctx)
        
        # Build the full command using the claude path from context
        cmd_parts = [ctx['claude_cmd']]
        if self.command.value:
            cmd_parts.extend(self.command.value.split())
        if self.args.value:
            cmd_parts.extend(self.args.value.split())
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd_parts,
                input=self.input_text.value if self.input_text.value else None,
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
        
        # Extract token usage information
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
        
        # Extract file edit information
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
    """Executes a Claude Code chat command with a specific prompt.
    
    Uses configuration from ClaudeCodeInit component. Requires ClaudeCodeInit to be
    executed first in the workflow.

    ##### inPorts:
    - prompt: The prompt/question to send to Claude.

    ##### outPorts:
    - response: Claude's response to the prompt.
    - tokens_used: Total tokens used in the interaction.
    - cost: Cost of the interaction.
    - success: Whether the chat was successful.
    """
    
    prompt: InCompArg[str]
    
    response: OutArg[str]
    tokens_used: OutArg[int]
    cost: OutArg[float]
    success: OutArg[bool]

    def execute(self, ctx) -> None:
        # Get shared configuration from context
        model = get_claude_config(ctx, 'model')
        working_dir = get_claude_config(ctx, 'working_dir', os.getcwd())
        timeout = get_claude_config(ctx, 'timeout', 120)
        
        # Ensure claude command is available in context
        if 'claude_cmd' not in ctx:
            ensure_claude_code_available(ctx)
        
        # Build command using the claude path from context
        cmd_parts = [ctx['claude_cmd'], "chat"]
        if model:
            cmd_parts.extend(["--model", model])
        
        try:
            result = subprocess.run(
                cmd_parts,
                input=self.prompt.value,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            self.response.value = result.stdout
            self.success.value = result.returncode == 0
            
            # Extract token and cost info
            output_text = result.stdout
            token_match = re.search(r'(\d+)\s*total\s*tokens', output_text, re.IGNORECASE)
            self.tokens_used.value = int(token_match.group(1)) if token_match else 0
            
            cost_match = re.search(r'cost:\s*\$?([\d.]+)', output_text, re.IGNORECASE)
            self.cost.value = float(cost_match.group(1)) if cost_match else 0.0
            
        except Exception as e:
            self.response.value = str(e)
            self.success.value = False
            self.tokens_used.value = 0
            self.cost.value = 0.0


@xai_component
class ClaudeCodeFileEdit(Component):
    """Executes a Claude Code command to edit a specific file.
    
    Uses configuration from ClaudeCodeInit component. Requires ClaudeCodeInit to be
    executed first in the workflow.

    ##### inPorts:
    - file_path: Path to the file to edit.
    - instruction: Instruction for how to edit the file.

    ##### outPorts:
    - success: Whether the edit was successful.
    - changes_made: Description of changes made.
    - tokens_used: Tokens used for the edit.
    - cost: Cost of the edit operation.
    """
    
    file_path: InCompArg[str]
    instruction: InCompArg[str]
    
    success: OutArg[bool]
    changes_made: OutArg[str]
    tokens_used: OutArg[int]
    cost: OutArg[float]

    def execute(self, ctx) -> None:
        # Get shared configuration from context
        model = get_claude_config(ctx, 'model')
        timeout = get_claude_config(ctx, 'timeout', 120)
        
        # Ensure claude command is available in context
        if 'claude_cmd' not in ctx:
            ensure_claude_code_available(ctx)
        
        # Combine file path and instruction into a prompt
        prompt = f"Edit the file {self.file_path.value}: {self.instruction.value}"
        
        # Build command using the claude path from context
        cmd_parts = [ctx['claude_cmd'], "chat"]
        if model:
            cmd_parts.extend(["--model", model])
        
        try:
            result = subprocess.run(
                cmd_parts,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            self.success.value = result.returncode == 0
            self.changes_made.value = result.stdout
            
            # Extract usage information
            output_text = result.stdout
            token_match = re.search(r'(\d+)\s*total\s*tokens', output_text, re.IGNORECASE)
            self.tokens_used.value = int(token_match.group(1)) if token_match else 0
            
            cost_match = re.search(r'cost:\s*\$?([\d.]+)', output_text, re.IGNORECASE)
            self.cost.value = float(cost_match.group(1)) if cost_match else 0.0
            
        except Exception as e:
            self.success.value = False
            self.changes_made.value = f"Error: {str(e)}"
            self.tokens_used.value = 0
            self.cost.value = 0.0


@xai_component
class ClaudeCodeBatch(Component):
    """Executes multiple Claude Code commands in sequence and aggregates results.
    
    Uses configuration from ClaudeCodeInit component. Requires ClaudeCodeInit to be
    executed first in the workflow.

    ##### inPorts:
    - commands: List of command strings to execute.

    ##### outPorts:
    - results: List of results from each command.
    - total_tokens: Total tokens used across all commands.
    - total_cost: Total cost across all commands.
    - success_count: Number of successful commands.
    - failed_count: Number of failed commands.
    """
    
    commands: InCompArg[list]
    
    results: OutArg[list]
    total_tokens: OutArg[int]
    total_cost: OutArg[float]
    success_count: OutArg[int]
    failed_count: OutArg[int]

    def execute(self, ctx) -> None:
        # Get shared configuration from context
        working_dir = get_claude_config(ctx, 'working_dir', os.getcwd())
        timeout = get_claude_config(ctx, 'timeout', 120)
        
        # Ensure claude command is available in context
        if 'claude_cmd' not in ctx:
            ensure_claude_code_available(ctx)
        
        results = []
        total_tokens = 0
        total_cost = 0.0
        success_count = 0
        failed_count = 0
        
        for i, command in enumerate(self.commands.value):
            try:
                cmd_parts = [ctx['claude_cmd']] + command.split()
                
                result = subprocess.run(
                    cmd_parts,
                    cwd=working_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                # Parse tokens and cost from output
                output_text = result.stdout
                token_match = re.search(r'(\d+)\s*total\s*tokens', output_text, re.IGNORECASE)
                tokens = int(token_match.group(1)) if token_match else 0
                
                cost_match = re.search(r'cost:\s*\$?([\d.]+)', output_text, re.IGNORECASE)
                cost = float(cost_match.group(1)) if cost_match else 0.0
                
                command_result = {
                    'command': command,
                    'success': result.returncode == 0,
                    'output': result.stdout,
                    'error': result.stderr,
                    'tokens': tokens,
                    'cost': cost
                }
                
                results.append(command_result)
                total_tokens += tokens
                total_cost += cost
                
                if result.returncode == 0:
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                command_result = {
                    'command': command,
                    'success': False,
                    'output': '',
                    'error': str(e),
                    'tokens': 0,
                    'cost': 0.0
                }
                results.append(command_result)
                failed_count += 1
        
        self.results.value = results
        self.total_tokens.value = total_tokens
        self.total_cost.value = total_cost
        self.success_count.value = success_count
        self.failed_count.value = failed_count


@xai_component
class ClaudeCodeUsageSummary(Component):
    """Summarizes usage statistics from multiple Claude Code operations.

    ##### inPorts:
    - results: List of results from Claude Code operations.

    ##### outPorts:
    - summary: Text summary of usage statistics.
    - total_operations: Total number of operations.
    - successful_operations: Number of successful operations.
    - total_tokens: Total tokens used.
    - total_cost: Total cost incurred.
    - average_cost_per_operation: Average cost per operation.
    """
    
    results: InCompArg[list]
    
    summary: OutArg[str]
    total_operations: OutArg[int]
    successful_operations: OutArg[int]
    total_tokens: OutArg[int]
    total_cost: OutArg[float]
    average_cost_per_operation: OutArg[float]

    def execute(self, ctx) -> None:
        results = self.results.value or []
        
        total_ops = len(results)
        successful_ops = sum(1 for r in results if r.get('success', False))
        total_tokens = sum(r.get('tokens', 0) for r in results)
        total_cost = sum(r.get('cost', 0.0) for r in results)
        avg_cost = total_cost / total_ops if total_ops > 0 else 0.0
        
        summary = f"""Claude Code Usage Summary:
Total Operations: {total_ops}
Successful: {successful_ops}
Failed: {total_ops - successful_ops}
Total Tokens Used: {total_tokens:,}
Total Cost: ${total_cost:.4f}
Average Cost per Operation: ${avg_cost:.4f}
Success Rate: {(successful_ops/total_ops*100):.1f}%"""
        
        self.summary.value = summary
        self.total_operations.value = total_ops
        self.successful_operations.value = successful_ops
        self.total_tokens.value = total_tokens
        self.total_cost.value = total_cost
        self.average_cost_per_operation.value = avg_cost