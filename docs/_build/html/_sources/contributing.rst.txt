# Contributing

Thank you for your interest in contributing to PTools! This guide will help you get started with contributing to the project.

## Getting Started

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ptools
   ```

2. **Set up development environment**:
   ```bash
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install in development mode
   pip install -e .
   
   # Install development dependencies
   pip install -r dev-requirements.txt  # If available
   ```

3. **Verify installation**:
   ```bash
   ptools --version
   ptools dev install  # Reinstalls the tool
   ```

## Development Workflow

### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards below

3. **Test your changes**:
   ```bash
   # Run tests (if test suite exists)
   python -m pytest
   
   # Test CLI functionality
   ptools --help
   ptools your-module --help
   ```

4. **Update documentation** if needed

### Coding Standards

#### Python Style
- Follow PEP 8 style guidelines
- Use type hints for all functions and methods
- Write docstrings for all public functions and classes
- Use meaningful variable and function names

#### Code Example
```python
from typing import Optional, List
import click

@click.command()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def example_command(verbose: bool) -> None:
    """
    Example command with proper typing and documentation.
    
    Args:
        verbose: Whether to enable verbose output
    """
    if verbose:
        click.echo("Verbose mode enabled")
```

#### Module Structure
Each module should follow this pattern:
```python
import click
# Other imports...

@click.group()
def cli():
    """Module description for help text."""
    pass

@cli.command()
def command_name():
    """Command description."""
    pass

# Register commands
cli.add_command(command_name)
```

### Documentation Standards

#### Docstring Format
Use Google-style docstrings:

```python
def function_name(arg1: str, arg2: int) -> bool:
    """
    Brief description of the function.
    
    Longer description if needed, explaining what the function does,
    any important implementation details, etc.
    
    Args:
        arg1: Description of first argument
        arg2: Description of second argument
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When arg1 is empty
        RuntimeError: When operation fails
        
    Example:
        >>> function_name("test", 42)
        True
    """
    pass
```

#### CLI Documentation
Commands should have:
- Clear help text
- Option descriptions
- Usage examples in docstrings

### Testing Guidelines

#### Test Structure
```python
import pytest
from ptools.module import function_to_test

def test_function_basic_case():
    """Test basic functionality."""
    result = function_to_test("input")
    assert result == expected_output

def test_function_error_case():
    """Test error handling."""
    with pytest.raises(ValueError):
        function_to_test("")
```

#### CLI Testing
```python
from click.testing import CliRunner
from ptools.module import cli

def test_cli_command():
    """Test CLI command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['command', '--option', 'value'])
    assert result.exit_code == 0
    assert "expected output" in result.output
```

## Types of Contributions

### Bug Reports
When reporting bugs, please include:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- System information (OS, Python version, PTools version)
- Complete error messages

### Feature Requests
For new features:
- Describe the use case and motivation
- Explain how it fits with existing functionality
- Consider implementation complexity
- Provide examples of usage

### Code Contributions

#### New Modules
To add a new module:

1. **Create the module file**: `src/ptools/new_module.py`
2. **Implement CLI commands** following existing patterns
3. **Add to main CLI** in `src/ptools/main.py`
4. **Write tests** for your module
5. **Update documentation**

Example module structure:
```python
import click

@click.group()
def cli():
    """New module for specific functionality."""
    pass

@cli.command()
def new_command():
    """New command description."""
    click.echo("Hello from new module!")

# Add to main.py:
# from . import new_module
# cli.add_command(new_module.cli, name="new-module")
```

#### Enhancements to Existing Modules
- Follow existing code patterns
- Maintain backward compatibility
- Add comprehensive tests
- Update relevant documentation

#### Bug Fixes
- Include tests that reproduce the bug
- Ensure fix doesn't break existing functionality
- Update documentation if behavior changes

## Documentation Contributions

### Documentation Structure
- User guides go in `docs/user-guide/`
- API documentation is auto-generated from docstrings
- Tutorials go in `docs/tutorials/`
- Architecture docs go in `docs/architecture/`

### Building Documentation Locally
```bash
cd docs
pip install sphinx sphinx-rtd-theme sphinx-click myst-parser
make html
# Open _build/html/index.html in browser
```

### Writing Guidelines
- Use clear, concise language
- Include code examples
- Test all code examples
- Use proper reStructuredText or Markdown formatting

## Pull Request Process

### Before Submitting
1. **Update the changelog** if your change is user-facing
2. **Ensure all tests pass**
3. **Update documentation** as needed
4. **Check code style** with linting tools

### Pull Request Description
Include:
- Clear title describing the change
- Detailed description of what was changed and why
- References to related issues
- Testing instructions
- Screenshots for UI changes (if applicable)

### Review Process
- Maintainers will review your PR
- Address any feedback promptly
- Be open to suggestions and changes
- All checks must pass before merging

## Development Tools

### Useful Commands
```bash
# Development installation
ptools dev install

# Open project in VS Code  
ptools dev code

# Check project root
ptools dev root

# Update to latest version
ptools dev update
```

### IDE Setup
For VS Code, recommended extensions:
- Python
- Python Docstring Generator
- autoDocstring
- GitLens

## Community Guidelines

### Code of Conduct
- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain professional communication

### Getting Help
- Check existing documentation first
- Search existing issues
- Ask questions in discussions
- Provide context when asking for help

### Recognition
Contributors are recognized in:
- Git history and blame
- Release notes for significant contributions
- Documentation credits

## Release Process

### Version Management
PTools follows semantic versioning (semver):
- Major version: Breaking changes
- Minor version: New features, backward compatible
- Patch version: Bug fixes

### Release Checklist
1. Update version numbers
2. Update changelog
3. Create release notes
4. Tag release in git
5. Build and publish packages

Thank you for contributing to PTools! Your contributions help make the tool better for everyone.
