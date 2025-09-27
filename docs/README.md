# PTools Documentation

This directory contains the complete Sphinx documentation for PTools.

## Quick Start

### Building the Documentation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Build HTML documentation**:
   ```bash
   make html
   # or
   ./build.sh
   ```

3. **View the documentation**:
   Open `_build/html/index.html` in your browser.

### Development

For continuous building while editing:

```bash
pip install sphinx-autobuild
sphinx-autobuild . _build/html
```

This will start a local server and automatically rebuild when files change.

## Documentation Structure

```
docs/
├── index.rst                 # Main documentation entry point
├── introduction.rst          # Project introduction
├── installation.rst          # Installation guide
├── quickstart.rst           # Quick start tutorial
├── user-guide/              # Detailed user guides
│   ├── index.rst
│   ├── core-concepts.rst
│   ├── ai-integration.rst
│   ├── file-operations.rst
│   ├── data-processing.rst
│   ├── development-tools.rst
│   ├── configuration.rst
│   └── workflow-automation.rst
├── tutorials/               # Step-by-step tutorials
│   ├── index.rst
│   └── getting-started.rst
├── cli-reference/          # Complete CLI documentation
│   ├── index.rst
│   └── main.rst
├── api-reference/          # Auto-generated API docs
│   ├── index.rst
│   ├── core-modules.rst
│   └── lib-modules.rst
├── architecture/           # Architecture documentation
│   └── index.rst
├── contributing.rst        # Contributing guidelines
└── changelog.rst          # Version history
```

## Writing Documentation

### reStructuredText Basics

The documentation uses reStructuredText (RST) format. Here are some common patterns:

```rst
# Main Title
============

## Section Title
---------------

### Subsection
~~~~~~~~~~~~~~

**Bold text** and *italic text*

`inline code` and::

    code blocks
    with multiple lines

.. note::
   This is a note admonition.

.. warning::
   This is a warning admonition.
```

### Code Examples

Always test code examples before including them:

```rst
Example usage:

.. code-block:: bash

   ptools llm "Hello, world!"
   ptools fs info /path/to/file
   ptools flow map "x.upper()"
```

### Cross-References

Link to other sections:

```rst
See :doc:`user-guide/ai-integration` for details.
Refer to :ref:`configuration-section` for setup.
```

## API Documentation

API documentation is automatically generated from docstrings using Sphinx autodoc. To update:

1. Ensure docstrings follow Google style
2. Run `make html` to regenerate
3. API docs appear in `api-reference/`

Example docstring:
```python
def example_function(param1: str, param2: int = 10) -> bool:
    """
    Brief description of the function.
    
    Args:
        param1: Description of the first parameter
        param2: Description with default value
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is empty
        
    Example:
        >>> example_function("test", 20)
        True
    """
```

## Extensions and Plugins

The documentation uses these Sphinx extensions:

- **sphinx.ext.autodoc**: Auto-generate API docs from docstrings
- **sphinx.ext.napoleon**: Support for Google/NumPy style docstrings
- **sphinx.ext.viewcode**: Add source code links
- **sphinx.ext.intersphinx**: Cross-reference external docs
- **sphinx-click**: Document Click commands
- **myst-parser**: Support Markdown files

## Themes and Styling

The documentation uses the `sphinx_rtd_theme` (Read the Docs theme) with custom CSS in `_static/custom.css`.

## Building for Production

For production builds:

```bash
# Clean build
make clean html

# Check for broken links
make linkcheck

# Build all formats
make html epub latex
```

## Contributing to Documentation

1. Follow the existing structure and style
2. Test all code examples
3. Use appropriate RST formatting
4. Add new pages to the appropriate `toctree`
5. Build locally before submitting
6. Check for spelling and grammar

## Troubleshooting

### Common Issues

1. **Import errors during build**:
   - Ensure PTools is installed: `pip install -e ..`
   - Check Python path in `conf.py`

2. **Missing references**:
   - Check file names and paths
   - Ensure files are added to `toctree` directives

3. **Formatting issues**:
   - Validate RST syntax
   - Check indentation (RST is sensitive to whitespace)

### Getting Help

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [reStructuredText Primer](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [Read the Docs Theme](https://sphinx-rtd-theme.readthedocs.io/)

## License

The documentation is part of the PTools project and follows the same license terms.
