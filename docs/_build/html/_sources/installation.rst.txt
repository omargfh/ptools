# Installation

This guide covers how to install PTools and its dependencies on your system.

## Requirements

- Python 3.10 or higher
- pip package manager

## Installation Methods

### Development Installation (Recommended)

For development or to get the latest features, install directly from the source:

```bash
git clone <repository-url>
cd ptools
pip install -e .
```

The `-e` flag installs in "editable" mode, meaning changes to the source code will be immediately available without reinstalling.

### From PyPI (When Available)

Once published to PyPI, you can install with:

```bash
pip install ptools
```

## Verifying Installation

After installation, verify that PTools is working correctly:

```bash
# Check if ptools is available
ptools --version

# Get help for available commands
ptools --help

# Test a simple command
ptools fs info .
```

## Dependencies

PTools automatically installs the following core dependencies:

- **click>=8.1**: Command-line interface framework
- **watchdog>=3.0**: File system monitoring
- **keyring>=25.6.0**: Secure credential storage
- **pycryptodome>=3.14.0**: Cryptographic operations
- **pydantic>=2.10**: Data validation and settings management
- **lark>=1.1**: Parsing library for expressions
- **humanize>=4.8.0**: Human-friendly data formatting

## Optional Dependencies

Some features require additional packages that are installed on-demand:

### AI/LLM Features
```bash
pip install openai>=1.0.0        # For OpenAI GPT models
pip install google-generativeai  # For Google Gemini models
pip install prompt-toolkit       # For interactive chat interfaces
pip install pygments             # For syntax highlighting
```

### Development Tools
```bash
pip install watchdog[watchmedo]  # Enhanced file watching
```

### Data Processing
```bash
pip install pandas               # For advanced data operations
pip install numpy                # For numerical computations
```

## Platform-Specific Notes

### macOS
PTools works out of the box on macOS. The keyring dependency will use the macOS Keychain for secure storage.

### Linux
On Linux systems, you may need to install additional packages for keyring support:

```bash
# Ubuntu/Debian
sudo apt-get install python3-keyring

# CentOS/RHEL/Fedora
sudo yum install python3-keyring
```

### Windows
PTools should work on Windows with Python 3.10+. The keyring will use Windows Credential Manager.

## Configuration

After installation, PTools will create configuration directories in your home folder:

- `~/.config/ptools/` (Linux/macOS) or `%APPDATA%/ptools/` (Windows)
- Configuration files, profiles, and cached data are stored here

## Troubleshooting

### Common Issues

1. **Command not found**: Ensure your Python scripts directory is in your PATH
2. **Import errors**: Check that all required dependencies are installed
3. **Permission errors**: On some systems, you may need to use `pip install --user`

### Getting Help

If you encounter issues:

1. Check the version: `ptools --version`
2. Verify dependencies: `pip list | grep -E "(click|watchdog|keyring)"`
3. Check the logs in your configuration directory
4. File an issue on the project repository

## Next Steps

Once installed, you can:

1. Read the [Quick Start Guide](quickstart.rst) for immediate usage
2. Explore the [User Guide](user-guide/index.rst) for detailed instructions
3. Try the [Tutorials](tutorials/index.rst) for hands-on examples

## Uninstalling

To remove PTools:

```bash
pip uninstall ptools
```

Note that this won't remove configuration files. To completely remove PTools:

```bash
pip uninstall ptools
rm -rf ~/.config/ptools/  # Linux/macOS
# or
rmdir /s %APPDATA%\ptools\  # Windows
```
