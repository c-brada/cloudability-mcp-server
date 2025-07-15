# Contributing to Cloudability MCP Server

Thank you for your interest in contributing to the Cloudability MCP Server! This document provides guidelines and information for contributors.

## 🚀 Quick Start for Contributors

### Prerequisites

- **Python 3.12+**: Required for modern type annotations
- **uv**: Fast Python package manager
- **Git**: For version control
- **Cloudability API Access**: For testing (optional but recommended)

### Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/your-username/cloudability-mcp-server.git
   cd cloudability-mcp-server
   ```

2. **Install dependencies**:
   ```bash
   # Install uv if needed
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install all dependencies including dev tools
   uv sync --group dev
   ```

3. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your test credentials (optional)
   ```

4. **Verify setup**:
   ```bash
   uv run pytest tests/ -v
   ```

## 📋 Contribution Guidelines

### Code Style

We use automated formatting and linting tools:

```bash
# Format code (required before commits)
uv run black .
uv run isort .

# Type checking (required)
uv run mypy main.py cloudability_tools.py

# Run all quality checks
uv run black . && uv run isort . && uv run mypy main.py cloudability_tools.py
```

**Code Style Requirements:**
- **Black formatting**: Line length 88 characters
- **Import sorting**: Using isort with black profile
- **Type annotations**: Required for all functions and methods
- **Docstrings**: Required for all public functions using Google style
- **Variable naming**: Use snake_case for variables and functions
- **Class naming**: Use PascalCase for classes

### Testing Requirements

All contributions must include comprehensive tests:

#### Test Coverage Requirements
- **New functions**: Must have 100% test coverage
- **Modified functions**: Must maintain existing coverage
- **Integration tests**: Required for new API endpoints
- **Error handling**: Must test both success and failure cases

#### Test Structure
```python
@responses.activate
def test_new_function():
    """Test description following Google docstring style."""
    # Arrange: Mock API responses
    responses.add(
        responses.GET,
        "https://api.cloudability.com/v3/endpoint",
        json={"expected": "response"},
        status=200
    )
    
    # Act: Call the function
    result = new_function(param="value", authorization="Bearer token")
    
    # Assert: Validate results
    assert result["expected"] == "response"
    assert len(responses.calls) == 1
```

#### Running Tests
```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ -v --cov=main --cov=cloudability_tools --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_cloudability_tools.py -v

# Run tests matching pattern
uv run pytest tests/ -k "test_container" -v
```

### Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Follow code style guidelines
   - Add comprehensive tests
   - Update documentation as needed

3. **Run quality checks**:
   ```bash
   # Format and lint
   uv run black . && uv run isort .
   uv run mypy main.py cloudability_tools.py
   
   # Run tests
   uv run pytest tests/ -v --cov=main --cov=cloudability_tools
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add new container analytics endpoint"
   ```

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

Use conventional commits format:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(containers): add cluster provisioning endpoint
fix(auth): handle bearer token edge cases
docs(readme): update installation instructions
test(budgets): add comprehensive budget API tests
```

## 🔧 Development Guidelines

### Adding New API Endpoints

1. **Research the API**: Study Cloudability API documentation thoroughly
2. **Implement in `cloudability_tools.py`**:
   ```python
   def new_api_endpoint(
       param1: str,
       param2: Optional[int] = None,
       authorization: str | None = None
   ) -> Dict[str, Any]:
       """
       Brief description of what this endpoint does.
       
       Args:
           param1: Description of parameter
           param2: Optional parameter description
           authorization: Bearer token or Basic auth header
           
       Returns:
           API response data with specific structure
           
       Raises:
           ValueError: If authorization is missing
           requests.HTTPError: If API request fails
       """
       if not authorization:
           raise ValueError("Authorization token is required")
           
       headers = get_auth_headers(authorization)
       url = f"{CLOUDABILITY_API_URL}/new-endpoint"
       
       # Implementation details
   ```

3. **Add MCP tool in `main.py`**:
   ```python
   @mcp.tool()
   def new_mcp_tool(
       param1: str,
       param2: Optional[int] = None,
       authorization: str | None = None
   ) -> Dict[str, Any]:
       """
       Tool description for MCP clients.
       
       Detailed description of what this tool does and when to use it.
       """
       return new_api_endpoint(param1, param2, authorization)
   ```

4. **Write comprehensive tests**
5. **Update documentation** in README.md and tool.yaml

### Error Handling Standards

- **Input validation**: Validate all parameters before API calls
- **HTTP errors**: Let `requests.HTTPError` propagate with context
- **Authentication**: Clear error messages for auth failures
- **Rate limiting**: Handle 429 responses gracefully
- **Logging**: Use appropriate log levels for debugging

### Documentation Standards

- **Function docstrings**: Google style with Args, Returns, Raises
- **Type hints**: Complete type annotations for all parameters
- **README updates**: Add examples for new functionality
- **tool.yaml**: Update schema definitions for new tools

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Environment information**:
   - Python version
   - uv version
   - Operating system
   - Cloudability region

2. **Reproduction steps**:
   - Minimal code example
   - Expected vs actual behavior
   - Error messages and stack traces

3. **Additional context**:
   - API endpoint being used
   - Authentication method
   - Rate limiting status

## 💡 Feature Requests

For new features, please:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** and business value
3. **Provide API documentation** links if available
4. **Consider backward compatibility** implications

## 📚 Resources

- **Cloudability API Documentation**: [Official API Docs](https://developers.cloudability.com/)
- **FastMCP Framework**: [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- **Model Context Protocol**: [MCP Specification](https://modelcontextprotocol.io/)
- **Python Type Hints**: [PEP 484](https://peps.python.org/pep-0484/)

## 🤝 Code of Conduct

- **Be respectful**: Treat all contributors with respect
- **Be inclusive**: Welcome contributors of all backgrounds
- **Be constructive**: Provide helpful feedback and suggestions
- **Be patient**: Remember that everyone is learning

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Code Review**: All PRs receive thorough review and feedback

## 🏆 Recognition

Contributors will be recognized in:
- **README.md**: Contributors section
- **Release notes**: Major contributions highlighted
- **GitHub**: Contributor graphs and statistics

Thank you for contributing to the Cloudability MCP Server! 🚀
