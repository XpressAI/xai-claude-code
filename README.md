# XAI Claude Code Components

A Xircuits component library for integrating with Claude Code CLI, enabling scripted automation of Claude Code commands with cost and edit tracking.

## Components

### ClaudeCodeExecute
Executes Claude Code CLI commands and captures output, errors, and execution metrics.

**Input Ports:**
- `command`: The claude command to execute (e.g., "chat", "help")
- `args`: Additional arguments for the command
- `input_text`: Text input to provide to the command
- `working_dir`: Working directory for command execution
- `timeout`: Command timeout in seconds

**Output Ports:**
- `output`: Command stdout
- `error`: Command stderr
- `return_code`: Exit code
- `execution_time`: Execution time in seconds

### ClaudeCodeAnalyze
Analyzes Claude Code output to extract usage statistics and edit information.

**Input Ports:**
- `output`: stdout from Claude Code command
- `error`: stderr from Claude Code command

**Output Ports:**
- `input_tokens`: Number of input tokens used
- `output_tokens`: Number of output tokens used
- `total_cost`: Total cost in USD
- `files_edited`: List of edited files
- `edit_summary`: Summary of edits made
- `has_errors`: Boolean indicating errors
- `success`: Boolean indicating success

### ClaudeCodeChat
Convenient wrapper for Claude Code chat commands.

**Input Ports:**
- `prompt`: The prompt to send to Claude
- `model`: Optional model specification
- `working_dir`: Working directory

**Output Ports:**
- `response`: Claude's response
- `tokens_used`: Total tokens used
- `cost`: Cost of interaction
- `success`: Success indicator

### ClaudeCodeFileEdit
Executes file editing commands with Claude Code.

**Input Ports:**
- `file_path`: Path to file to edit
- `instruction`: Edit instruction
- `model`: Optional model

**Output Ports:**
- `success`: Edit success indicator
- `changes_made`: Description of changes
- `tokens_used`: Tokens consumed
- `cost`: Operation cost

### ClaudeCodeBatch
Executes multiple Claude Code commands in sequence with aggregated results.

**Input Ports:**
- `commands`: List of command strings
- `working_dir`: Working directory

**Output Ports:**
- `results`: List of individual results
- `total_tokens`: Aggregated token usage
- `total_cost`: Total cost
- `success_count`: Number of successful operations
- `failed_count`: Number of failed operations

### ClaudeCodeUsageSummary
Generates usage summaries from Claude Code operation results.

**Input Ports:**
- `results`: List of operation results

**Output Ports:**
- `summary`: Text summary
- `total_operations`: Operation count
- `successful_operations`: Success count
- `total_tokens`: Total tokens
- `total_cost`: Total cost
- `average_cost_per_operation`: Average cost per operation

## Installation

```bash
pip install -r requirements.txt
```

## Prerequisites

- Claude Code CLI must be installed and configured
- xai-components must be installed
- Valid Claude API credentials configured

## Usage Examples

### Basic Chat Interaction

Create a workflow with:
1. `ClaudeCodeChat` component with prompt "Explain Python decorators"
2. `ClaudeCodeAnalyze` component to extract cost information
3. Output the response and cost data

### File Editing Workflow

1. `ClaudeCodeFileEdit` - Edit a specific file
2. `ClaudeCodeAnalyze` - Extract edit and cost information
3. Log or display the results

### Batch Processing

1. `ClaudeCodeBatch` - Execute multiple commands
2. `ClaudeCodeUsageSummary` - Generate usage report
3. Output aggregated statistics

### Custom Command Execution

1. `ClaudeCodeExecute` - Run any Claude Code command
2. `ClaudeCodeAnalyze` - Parse the results
3. Process the extracted data

## Configuration

The components rely on the Claude Code CLI being properly configured with:
- Valid API credentials
- Appropriate model access
- Proper authentication setup

Refer to the Claude Code documentation for setup instructions.

## Error Handling

All components include error handling for:
- Command timeouts
- Invalid commands
- Network issues
- Authentication failures

Error information is captured in the respective output ports.

## Cost Monitoring

The components automatically extract and track:
- Token usage (input/output)
- Operation costs
- Usage summaries
- Per-operation metrics

This enables effective monitoring and budgeting of Claude Code usage in automated workflows.