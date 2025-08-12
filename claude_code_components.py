import os
import subprocess
import json
import re
from typing import Dict, List, Any, Optional

from xai_components.base import InArg, OutArg, InCompArg, Component, BaseComponent, secret, xai_component


@xai_component
class ClaudeCodeExecute(Component):
    """Executes a Claude Code CLI command and captures the output.

    ##### inPorts:
    - command: The claude command to execute (e.g., "claude chat", "claude help").
    - args: Additional arguments to pass to the command.
    - input_text: Optional text to provide as input to the command.
    - working_dir: Working directory to execute the command in.
    - timeout: Timeout in seconds for the command execution.

    ##### outPorts:
    - output: The stdout output from the command.
    - error: The stderr output from the command.
    - return_code: The exit code of the command.
    - execution_time: Time taken to execute the command in seconds.
    """
    
    command: InCompArg[str]
    args: InArg[str]
    input_text: InArg[str]
    working_dir: InArg[str]
    timeout: InArg[int]
    
    output: OutArg[str]
    error: OutArg[str]
    return_code: OutArg[int]
    execution_time: OutArg[float]

    def execute(self, ctx) -> None:
        import time
        
        # Build the full command
        cmd_parts = ["claude"]
        if self.command.value:
            cmd_parts.extend(self.command.value.split())
        if self.args.value:
            cmd_parts.extend(self.args.value.split())
        
        # Set working directory
        cwd = self.working_dir.value if self.working_dir.value else os.getcwd()
        
        # Set timeout (default 30 seconds)
        timeout = self.timeout.value if self.timeout.value else 30
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd_parts,
                input=self.input_text.value if self.input_text.value else None,
                cwd=cwd,
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
    files_edited: OutArg[List[str]]
    edit_summary: OutArg[str]
    has_errors: OutArg[bool]
    success: OutArg[bool]

    def execute(self, ctx) -> None:
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

    ##### inPorts:
    - prompt: The prompt/question to send to Claude.
    - model: Optional model to use (e.g., "claude-3-5-sonnet-20241022").
    - working_dir: Working directory for the chat session.

    ##### outPorts:
    - response: Claude's response to the prompt.
    - tokens_used: Total tokens used in the interaction.
    - cost: Cost of the interaction.
    - success: Whether the chat was successful.
    """
    
    prompt: InCompArg[str]
    model: InArg[str]
    working_dir: InArg[str]
    
    response: OutArg[str]
    tokens_used: OutArg[int]
    cost: OutArg[float]
    success: OutArg[bool]

    def execute(self, ctx) -> None:
        # Build command
        cmd_parts = ["claude", "chat"]
        if self.model.value:
            cmd_parts.extend(["--model", self.model.value])
        
        cwd = self.working_dir.value if self.working_dir.value else os.getcwd()
        
        try:
            result = subprocess.run(
                cmd_parts,
                input=self.prompt.value,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=120
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

    ##### inPorts:
    - file_path: Path to the file to edit.
    - instruction: Instruction for how to edit the file.
    - model: Optional model to use.

    ##### outPorts:
    - success: Whether the edit was successful.
    - changes_made: Description of changes made.
    - tokens_used: Tokens used for the edit.
    - cost: Cost of the edit operation.
    """
    
    file_path: InCompArg[str]
    instruction: InCompArg[str]
    model: InArg[str]
    
    success: OutArg[bool]
    changes_made: OutArg[str]
    tokens_used: OutArg[int]
    cost: OutArg[float]

    def execute(self, ctx) -> None:
        # Combine file path and instruction into a prompt
        prompt = f"Edit the file {self.file_path.value}: {self.instruction.value}"
        
        cmd_parts = ["claude", "chat"]
        if self.model.value:
            cmd_parts.extend(["--model", self.model.value])
        
        try:
            result = subprocess.run(
                cmd_parts,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=120
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

    ##### inPorts:
    - commands: List of command strings to execute.
    - working_dir: Working directory for all commands.

    ##### outPorts:
    - results: List of results from each command.
    - total_tokens: Total tokens used across all commands.
    - total_cost: Total cost across all commands.
    - success_count: Number of successful commands.
    - failed_count: Number of failed commands.
    """
    
    commands: InCompArg[List[str]]
    working_dir: InArg[str]
    
    results: OutArg[List[Dict[str, Any]]]
    total_tokens: OutArg[int]
    total_cost: OutArg[float]
    success_count: OutArg[int]
    failed_count: OutArg[int]

    def execute(self, ctx) -> None:
        results = []
        total_tokens = 0
        total_cost = 0.0
        success_count = 0
        failed_count = 0
        
        cwd = self.working_dir.value if self.working_dir.value else os.getcwd()
        
        for i, command in enumerate(self.commands.value):
            try:
                cmd_parts = ["claude"] + command.split()
                
                result = subprocess.run(
                    cmd_parts,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=120
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
    
    results: InCompArg[List[Dict[str, Any]]]
    
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