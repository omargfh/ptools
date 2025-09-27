# Architecture

Understanding the internal architecture and design principles of PTools.

```{toctree}
:maxdepth: 2
:caption: Architecture Topics:

design-principles
module-system
data-flow
extension-points
performance
```

## Overview

PTools follows a modular, extensible architecture designed around Unix philosophy principles while providing modern conveniences and powerful integrations.

## High-Level Architecture

```
┌─────────────────┐
│   CLI Interface │  ← Click-based command line interface
├─────────────────┤
│   Core Modules  │  ← Individual feature modules (llm, fs, flow, etc.)
├─────────────────┤  
│  Shared Libraries│  ← Common implementations (lib/)
├─────────────────┤
│   Utilities     │  ← Helper functions and decorators (utils/)
├─────────────────┤
│  Configuration  │  ← Settings, profiles, and persistence
└─────────────────┘
```

## Design Philosophy

### Unix Philosophy
- **Do one thing well**: Each module focuses on specific functionality
- **Composability**: Modules work together through pipes and standard interfaces
- **Text streams**: Data flows as text through processing pipelines

### Modern Python Practices
- **Type hints**: Comprehensive type annotations for better development experience
- **Pydantic models**: Data validation and serialization
- **Decorator patterns**: Consistent, reusable functionality across modules
- **Async support**: Ready for asynchronous operations where beneficial

### User Experience
- **Consistent interfaces**: All modules follow similar command patterns
- **Helpful error messages**: Clear guidance on fixing issues
- **Progressive disclosure**: Simple commands for common tasks, detailed options for advanced use

## Key Architectural Patterns

### Modular CLI Design
Each module provides its own Click command group:

```python
# Module pattern
@click.group()
def cli():
    """Module description."""
    pass

# Command registration
cli.add_command(module.cli, name="module")
```

### Decorator Composition
Common functionality implemented as composable decorators:

```python
@click.command()
@require.library('requests')
@require.key(['API_KEY'])
def command():
    pass
```

### Stream Processing
Data flows through processing stages using a consistent value model:

```python
class StreamValue:
    value: Any
    line_number: int
    metadata: dict
```

### Configuration Hierarchy
Settings resolved from multiple sources in priority order:
1. Command-line options
2. Environment variables  
3. Configuration files
4. Default values

## Component Architecture

### Core Modules Layer
- **Purpose**: Provide command-line interfaces for specific functionality
- **Pattern**: Click-based CLI groups with commands
- **Examples**: `llm.py`, `fs.py`, `flow.py`

### Library Layer  
- **Purpose**: Implement reusable functionality independent of CLI
- **Pattern**: Object-oriented classes and functions
- **Examples**: `lib/llm/client.py`, `lib/flow/runner.py`

### Utilities Layer
- **Purpose**: Common helper functions used across modules
- **Pattern**: Pure functions and utility classes
- **Examples**: `utils/config.py`, `utils/print.py`

### Models Layer
- **Purpose**: Data structures and validation
- **Pattern**: Pydantic models and dataclasses
- **Examples**: `models/default_config.py`

## Data Flow Architecture

### Input Processing
```
User Input → Validation → Parsing → Processing → Output
```

### Stream Processing Pipeline
```
Source → Transform → Filter → Aggregate → Sink
```

### Configuration Flow
```
Defaults ← Config Files ← Environment ← CLI Options
```

## Extension Architecture

PTools is designed to be extensible at multiple levels:

### Module Extensions
- Add new CLI modules by following existing patterns
- Register with main CLI in `main.py`
- Inherit common functionality from base classes

### Processing Extensions
- Custom flow transformers
- New AI providers
- Additional data formats

### Configuration Extensions
- Custom profile types
- New storage backends
- Additional validation rules

## Performance Considerations

### Memory Efficiency
- Stream processing avoids loading entire datasets
- Lazy evaluation where possible
- Configurable buffer sizes

### CPU Optimization
- Native Python performance for most operations
- Optional compiled extensions for heavy computation
- Parallel processing for independent operations

### I/O Optimization
- Async I/O for network operations
- Efficient file handling
- Minimal disk writes

## Security Architecture

### Credential Management
- System keyring integration for secure storage
- No plaintext credentials in configuration
- Proper cleanup of sensitive data

### Input Validation
- Pydantic models for data validation
- Sanitization of user inputs
- Protection against injection attacks

### Privilege Management
- Minimal required permissions
- Clear indication of privileged operations
- Safe handling of file operations

## Error Handling Architecture

### Error Categories
1. **User Errors**: Invalid input, missing files, etc.
2. **System Errors**: Permission denied, network issues, etc.
3. **Configuration Errors**: Invalid settings, missing dependencies, etc.
4. **Internal Errors**: Bugs, unexpected conditions, etc.

### Error Response Pattern
```python
try:
    # Operation
    pass
except SpecificError as e:
    # Provide helpful error message and solution
    click.echo(FormatUtils.error(f"Problem: {e}"))
    click.echo(FormatUtils.info(f"Solution: {suggested_fix}"))
    sys.exit(1)
```

### Graceful Degradation
- Optional dependencies handled gracefully
- Fallback implementations where possible
- Clear messaging about missing features

This architecture ensures PTools remains maintainable, extensible, and performant while providing a consistent user experience across all modules.
