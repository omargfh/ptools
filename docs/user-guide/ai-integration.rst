# AI Integration

PTools provides comprehensive AI integration through the `llm` module, supporting multiple AI providers and offering flexible configuration options for different use cases.

## Supported AI Providers

### OpenAI
- GPT-3.5 Turbo, GPT-4, and newer models
- Full chat API support
- Streaming responses
- Custom system prompts

### Google AI
- Gemini models (Gemini 2.0 Flash, etc.)
- Google AI Studio integration
- Advanced safety settings
- Multimodal capabilities (text, future support for images)

## Getting Started with AI

### Setting Up API Keys

First, configure your API keys for the services you want to use:

```bash
# OpenAI API key
ptools llm-opts set-api-key --service openai
# Enter your API key when prompted (hidden input)

# Google AI API key  
ptools llm-opts set-api-key --service google

# Verify your keys are stored
ptools llm-opts list-api-keys
```

API keys are securely stored using your system's keyring (Keychain on macOS, Credential Manager on Windows, etc.).

### Basic Chat Commands

```bash
# Simple one-off question
ptools llm "What is the capital of France?"

# Interactive chat session
ptools llm --interactive

# Use specific model
ptools llm "Explain Python decorators" --model gpt-4

# Non-interactive with specific model
ptools llm "Write a Python function to calculate fibonacci numbers" --model gemini-2.0-flash
```

### Interactive Chat Interface

The interactive mode provides a full chat experience:

```bash
ptools llm --interactive
```

In interactive mode:
- Type `/help` for available commands
- Use `/exit`, `/quit`, or `/q` to exit
- Chat history is automatically maintained
- Syntax highlighting for code responses

## Profiles and Configuration

Profiles allow you to customize AI behavior for different use cases.

### Creating Profiles

Create profiles interactively:

```bash
ptools llm-opts create-profile
# Follow the prompts to set:
# - Profile name
# - Temperature (creativity level)
# - Max tokens (response length)
# - Presence penalty (topic diversity)  
# - Frequency penalty (repetition avoidance)
# - System prompt (AI behavior instructions)
```

Create profiles from files:

```bash
# Create a profile configuration file
cat > code_reviewer.json << EOF
{
  "temperature": 0.3,
  "max_tokens": 2000,
  "presence_penalty": 0.0,
  "frequency_penalty": 0.0,
  "system_prompt": "You are an expert code reviewer. Provide detailed, constructive feedback on code quality, best practices, and potential improvements."
}
EOF

# Add the profile
ptools llm-opts add-profile code-reviewer code_reviewer.json
```

### Using Profiles

```bash
# Use a specific profile
ptools llm "Review this function" --profile code-reviewer

# Interactive session with profile
ptools llm --interactive --profile code-reviewer
```

### Managing Profiles

```bash
# List all profiles
ptools llm-opts list-profiles

# Delete a profile
ptools llm-opts delete-profile old-profile
```

## Chat History Management

### Persistent Chat Sessions

Save chat sessions for later reference:

```bash
# Create a named chat session
ptools llm --interactive --history project-planning --persist

# Continue a previous chat session
ptools llm --interactive --history project-planning
```

### Managing Chat History

```bash
# List all saved chats
ptools llm-opts list-chats

# Clean up old chats
ptools llm-opts prune-chats
```

### Chat File Format

Chat files are stored as JSON and can be manually inspected or processed:

```json
{
  "messages": [
    {
      "role": "user", 
      "content": "Hello!",
      "timestamp": "2025-01-01T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "Hello! How can I help you today?",
      "timestamp": "2025-01-01T10:00:01Z"
    }
  ],
  "metadata": {
    "model": "gpt-4",
    "profile": "default"
  }
}
```

## Advanced Features

### History Transformers

History transformers modify chat history before sending to the AI:

```bash
# Use pass-through transformer (default)
ptools llm --history-transformer pass_through

# Future: Summary transformer to compress long chats
# ptools llm --history-transformer summarize
```

### Custom System Prompts

System prompts define the AI's behavior and personality:

```bash
# Example system prompts for different use cases

# Code reviewer
"You are an expert code reviewer. Focus on best practices, security, and maintainability."

# Technical writer
"You are a technical writer. Explain complex topics clearly and provide practical examples."

# Unix expert
"You are a Unix system administrator. Provide command-line solutions and explain system concepts."
```

### Model Selection

Choose the best model for your task:

```bash
# Fast and cost-effective (default)
ptools llm "Quick question" --model gemini-2.0-flash

# More capable for complex tasks
ptools llm "Complex analysis needed" --model gpt-4

# List available models
ptools llm --help  # See model choices in help text
```

## Integration with Other Modules

### AI + Data Processing

Use AI responses in data processing pipelines:

```bash
# Process AI responses
ptools llm "List 5 programming languages" | \
  ptools flow map "x.lower()" | \
  ptools flow filter "'python' in x"
```

### AI + File Operations

Get AI help with file analysis:

```bash
# Analyze file content
ptools fs info suspicious_file.py | \
  ptools llm "Analyze this file information for security issues"

# Process multiple files
ptools fs walkdir --regex "\.py$" | \
  head -5 | \
  xargs -I {} ptools llm "Suggest improvements for: {}"
```

### AI + Development Tools

Integrate AI into development workflows:

```bash
# Get AI help with project structure
ptools projects list | \
  ptools llm "Suggest improvements for this project organization"

# AI-assisted debugging
ptools llm --interactive --profile debugger --history debug-session
```

## Best Practices

### Profile Organization

1. **Create task-specific profiles**:
   - `code-reviewer`: Low temperature, focused on code quality
   - `creative-writer`: High temperature, encourages creativity
   - `debugger`: Medium temperature, systematic problem-solving

2. **Use descriptive names**: Profile names should clearly indicate their purpose

3. **Document your profiles**: Keep notes about when to use each profile

### Efficient API Usage

1. **Choose appropriate models**:
   - Use Gemini 2.0 Flash for most tasks (fast, cost-effective)
   - Use GPT-4 for complex reasoning tasks
   - Consider model capabilities vs. cost

2. **Manage context length**:
   - Use history transformers for long conversations
   - Start new sessions for unrelated topics
   - Be mindful of token limits

3. **Optimize system prompts**:
   - Be specific about desired output format
   - Include relevant context and constraints
   - Test and iterate on prompts

### Security Considerations

1. **Protect API keys**:
   - Never commit API keys to version control
   - Use secure storage (system keyring)
   - Rotate keys regularly

2. **Be mindful of data privacy**:
   - Don't share sensitive information in prompts
   - Understand your AI provider's data policies
   - Use local storage for sensitive chat histories

3. **Monitor usage**:
   - Track API costs
   - Set up usage alerts with your provider
   - Review chat histories periodically

## Troubleshooting

### Common Issues

1. **API Key Not Found**:
   ```bash
   # Re-run the setup command
   ptools llm-opts set-api-key --service openai
   ```

2. **Rate Limiting**:
   ```bash
   # Wait and retry, or upgrade your API plan
   # Check your provider's rate limits
   ```

3. **Model Not Available**:
   ```bash
   # Check available models
   ptools llm --help
   # Use a different model
   ptools llm "question" --model gemini-2.0-flash
   ```

4. **Chat History Issues**:
   ```bash
   # List chats to verify names
   ptools llm-opts list-chats
   # Clean up corrupted chats
   ptools llm-opts prune-chats
   ```

### Debug Mode

Enable debug output for troubleshooting:

```bash
export PTOOLS_DEBUG=1
ptools llm "test question" --model gpt-4
```

This will show:
- API request details
- Response metadata
- Token usage information
- Error details

### Getting Help

For AI-related issues:
1. Check API key configuration
2. Verify internet connectivity  
3. Check your API provider's status page
4. Review token usage and limits
5. Try a different model or profile
