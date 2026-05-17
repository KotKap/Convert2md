# Contributing to Convert2MD

Thank you for your interest in contributing to Convert2MD! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the work, not the person
- Assume good intentions

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/yourusername/convert2md.git
cd convert2md
```

### 2. Set Up Development Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

### 3. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
git checkout -b fix/your-bug-fix
```

## Development Workflow

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src

# Specific test
pytest tests/test_convert2md.py::TestStructuralRequirements -v

# Watch mode (requires pytest-watch)
ptw
```

### Code Quality

```bash
# Type checking
mypy src/

# Code formatting (recommended)
black src/ tests/

# Linting (recommended)
flake8 src/ tests/
```

## Adding New Features

### 1. Create Test First
```bash
# Add test to tests/test_convert2md.py
def test_new_feature():
    # Your test here
    assert result == expected
```

### 2. Implement Feature
- Write implementation code in appropriate module
- Follow existing code style
- Add docstrings to functions/classes
- Handle errors appropriately

### 3. Update Documentation
- Update README.md if user-facing
- Add docstrings to public API
- Update TEST_CHECKLIST.md if applicable

### 4. Run Tests
```bash
pytest
mypy src/
```

## Adding Support for New File Format

If adding support for a new document format (e.g., RTF, HTML):

### 1. Create Converter Class
```python
# src/new_format_converter.py

from .converter_strategy import ConverterStrategy

class NewFormatConverter(ConverterStrategy):
    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in ['.newformat']
    
    def convert(self, input_path: Path) -> Tuple[str, dict]:
        # Implementation
        pass
```

### 2. Register in Factory
```python
# src/converter.py

class ConverterFactory:
    def __init__(self):
        self.converters: list[ConverterStrategy] = [
            PDFConverter(),
            DOCXConverter(),
            NewFormatConverter(),  # Add here
        ]
```

### 3. Add Tests
```python
# tests/test_convert2md.py

class TestNewFormatConverter:
    def test_format_support(self):
        converter = NewFormatConverter()
        assert converter.supports(Path("test.newformat"))
    
    # Additional tests
```

## Code Style

### Python Style Guide
- Follow PEP 8
- Use type hints for function signatures
- Maximum line length: 100 characters
- Use docstrings for modules, classes, and functions

### Example

```python
"""
Module docstring describing the module's purpose.
"""

from typing import Optional, Tuple
from pathlib import Path


def example_function(
    param1: str,
    param2: int,
    param3: Optional[bool] = None
) -> Tuple[str, dict]:
    """
    Function docstring with description.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        param3: Optional parameter description
        
    Returns:
        Tuple of (result, metadata)
        
    Raises:
        ValueError: Description of when this is raised
        
    Example:
        >>> result, meta = example_function("test", 42)
        >>> assert result == "expected"
    """
    if not isinstance(param2, int):
        raise ValueError("param2 must be an integer")
    
    return "result", {"key": "value"}
```

## Testing Guidelines

### Test Structure
```python
class TestFeatureName:
    """Group related tests in classes."""
    
    def test_specific_behavior(self):
        """Each test should verify one thing."""
        # Arrange
        input_data = setup_data()
        
        # Act
        result = function_under_test(input_data)
        
        # Assert
        assert result == expected_output
    
    def test_error_handling(self):
        """Test error cases."""
        with pytest.raises(ValueError):
            function_under_test(invalid_input)
```

### Coverage Requirements
- Aim for >80% code coverage
- Every branch should be tested
- Test both success and failure paths

## Documentation

### Updating README.md
- Keep it current with new features
- Include usage examples
- Update troubleshooting section
- Update dependencies list

### Docstrings
Use Google-style docstrings:
```python
def convert(self, input_path: Path) -> Tuple[str, dict]:
    """
    Convert a document to Markdown.
    
    Args:
        input_path: Path to the input document
        
    Returns:
        Tuple of (markdown_content, metadata)
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        RuntimeError: If conversion fails
    """
```

## Commit Guidelines

### Commit Messages
- Use clear, descriptive commit messages
- Start with a verb: "Add", "Fix", "Update", "Refactor"
- Keep first line under 72 characters
- Reference issues when applicable

```
Add support for RTF format

- Create RTFConverter class
- Register in factory
- Add tests for RTF conversion
- Update documentation

Fixes #123
```

## Pull Request Process

1. **Update Tests**: Ensure all tests pass
   ```bash
   pytest
   ```

2. **Code Quality**: Run linters and type checker
   ```bash
   mypy src/
   black src/ tests/
   ```

3. **Update Documentation**: If needed
   - README.md
   - Docstrings
   - TEST_CHECKLIST.md

4. **Create Pull Request**
   - Clear title and description
   - Link related issues
   - Describe changes and rationale

5. **Code Review**
   - Address feedback
   - Keep changes focused
   - One feature per PR when possible

## Reporting Issues

### Bug Reports
Include:
- Python version and OS
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages or stack trace
- Relevant file samples (if possible)

```markdown
**Environment**
- Python: 3.10.5
- OS: macOS 13.0
- Convert2MD: 1.0.0

**Steps to Reproduce**
1. Convert PDF with complex table
2. Check output for table format

**Expected**
Table rendered as Markdown table

**Actual**
Table text appears jumbled

**Error**
[Stack trace if applicable]
```

### Feature Requests
Include:
- Use case and problem it solves
- Proposed solution
- Alternative solutions considered
- Additional context

## Release Process

For maintainers:

1. Update version in `setup.py` and `__init__.py`
2. Update CHANGELOG
3. Run full test suite
4. Create git tag: `git tag v1.0.0`
5. Push to repository
6. Create release on GitHub

## Questions?

- Check existing issues and discussions
- Review README and documentation
- Open a discussion issue if needed

Thank you for contributing! 🎉
