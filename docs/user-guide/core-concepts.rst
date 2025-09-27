# Core Concepts

This section explains the fundamental concepts that underpin PTools' design and operation. Understanding these concepts will help you use PTools more effectively and understand how the different modules work together.

## Modular Architecture

PTools is built around a modular architecture where each module provides a specific set of functionality:

### Module Structure

Each module follows a consistent pattern:

```python
# Module structure example
import click

@click.group()
def cli():
    """Module description."""
    pass

@cli.command()
def some_command():
    """Command description."""
    pass
```

Modules are composed in the main CLI:

```python
# main.py
cli.add_command(module.cli, name="module")
```

### Benefits of Modularity

- **Independence**: Each module can be used standalone
- **Composability**: Modules can be combined in pipelines
- **Maintainability**: Easy to add, modify, or remove functionality
- **Testing**: Modules can be tested in isolation

## Command Line Interface Patterns

PTools uses several consistent patterns across all modules:

### Standard Options

Most commands support these common options:

- `--help`, `-h`: Get detailed help for any command
- `--verbose`, `-v`: Enable verbose output
- `--quiet`, `-q`: Suppress non-essential output
- `--output`, `-o`: Specify output file or format

### Input/Output Patterns

Commands follow Unix conventions:

```bash
# Read from stdin, write to stdout
cat file.txt | ptools flow map "x.upper()"

# Explicit input/output files
ptools json format --input data.json --output formatted.json

# Pipe between PTools commands
ptools fs walkdir | ptools flow filter "'.py' in x"
```

### Help System

Every command provides comprehensive help:

```bash
ptools --help                    # Top-level help
ptools module --help            # Module help
ptools module command --help    # Command help
```

## Configuration System

PTools uses a hierarchical configuration system:

### Configuration Hierarchy

1. **Command-line options**: Highest priority
2. **Environment variables**: Medium priority
3. **Configuration files**: Default values

### Configuration Storage

Configuration is stored in platform-appropriate locations:

- **Linux/macOS**: `~/.config/ptools/`
- **Windows**: `%APPDATA%\ptools\`

### Configuration Files

- `config.json`: Main configuration
- `profiles/`: AI model profiles
- `keys/`: Encrypted API keys
- `chats/`: Chat history files

## Data Flow and Streaming

PTools implements a streaming data model for efficient processing:

### Stream Values

Data flows through PTools as `StreamValue` objects:

```python
class StreamValue:
    value: Any          # The actual data
    line_number: int    # Source line number
    metadata: dict      # Additional context
```

### Processing Pipeline

Data flows through processing stages:

```
Input → Transform → Filter → Output
```

Each stage can:
- Transform data (map operations)
- Filter data (conditional operations)
- Aggregate data (reduce operations)
- Branch data (split operations)

### Example Pipeline

```bash
# Read lines → convert to uppercase → filter long lines → output as JSON
cat file.txt | \
  ptools flow map "x.upper()" | \
  ptools flow filter "len(x) > 10" | \
  ptools flow --flavor json
```

## Error Handling and Validation

PTools implements consistent error handling across all modules:

### Validation Decorators

Common validations are implemented as decorators:

```python
@require.library('requests')    # Ensure library is available
@require.key(['API_KEY'])      # Ensure required keys exist
@require.file_exists()         # Validate file exists
def command():
    pass
```

### Error Messages

Errors provide actionable information:

```bash
$ ptools llm "hello"
Error: OpenAI API key not found.
Solution: Run 'ptools llm-opts set-api-key --service openai'
```

### Graceful Degradation

When optional dependencies are missing:

- Commands prompt to install missing packages
- Alternative implementations may be used
- Clear error messages explain what's needed

## Security Model

PTools implements security best practices:

### Credential Management

- API keys stored in system keyring
- Configuration files have restricted permissions
- Sensitive data never logged or cached

### Data Privacy

- Chat histories are stored locally by default
- No data sent to external services without explicit user action
- Clear indication when external APIs are being used

## Extension Points

PTools is designed to be extensible:

### Adding New Modules

1. Create a new Python module with a `cli` Click group
2. Add it to `main.py`
3. Follow existing patterns for consistency

### Custom Transformers

Flow processing supports custom transformers:

```python
from ptools.lib.flow.history import HistoryTransformer

class MyTransformer(HistoryTransformer):
    def transform(self, history):
        # Custom transformation logic
        return modified_history
```

### Plugin System

Future versions will support plugin-based extensions for:
- New data sources
- Custom AI providers
- Additional output formats

## Performance Considerations

### Memory Usage

- Stream processing avoids loading entire datasets into memory
- Lazy evaluation where possible
- Configurable buffer sizes for large datasets

### Execution Speed

- Native Python performance for most operations
- Optional C extensions for heavy computation
- Parallel processing for independent operations

### Caching

- Configuration cached in memory
- API responses cached when appropriate
- File metadata cached to avoid repeated system calls

## Debugging and Troubleshooting

### Debug Mode

Enable debug output with `--debug` or environment variable:

```bash
export PTOOLS_DEBUG=1
ptools flow map "x.upper()" --debug
```

### Logging

Logs are written to:
- Console (configurable level)
- Log files in configuration directory
- System logs for errors

### Common Issues

1. **Import Errors**: Missing optional dependencies
2. **Permission Errors**: Configuration directory access
3. **API Errors**: Invalid or missing API keys
4. **Data Errors**: Malformed input data

Each module's documentation provides specific troubleshooting guidance.
