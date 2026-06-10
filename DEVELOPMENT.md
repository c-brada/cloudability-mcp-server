# Development Guide

This guide covers everything you need to know to develop and contribute to the Cloudability MCP Server.

## 🚀 Quick Start

### Prerequisites

- **Python 3.14+**: Required for modern type annotations and performance
- **uv**: Fast Python package manager (recommended)
- **Cloudability API Access**: Valid API token or environment access

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/eelzinaty/cloudability-mcp-server.git
   cd cloudability-mcp-server
   ```

2. **Install dependencies**:
   ```bash
   # Install uv if you haven't already
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install project dependencies
   uv sync
   
   # Install development dependencies
   uv sync --group dev
   ```

3. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Cloudability credentials
   ```

4. **Run tests to verify setup**:
   ```bash
   uv run pytest tests/ -v
   ```

## 🏗️ Architecture

### Project Structure

```
cloudability-mcp-server/
├── main.py                      # MCP server entry point with tool definitions
├── cloudability_tools.py        # Core API implementation and business logic
├── tests/                      # Test suite
│   └── test_cloudability_tools.py # Comprehensive API tests
├── .env.example                # Environment configuration template
├── pyproject.toml              # Project configuration and dependencies
├── tool.yaml                   # MCP tool schema definitions
├── README.md                   # User documentation
├── DEVELOPMENT.md              # This file
└── CONTRIBUTING.md             # Contribution guidelines
```

### Key Components

#### `main.py` - MCP Server
- **FastMCP Integration**: Uses FastMCP framework for clean tool definitions
- **Tool Registration**: Decorators for registering API endpoints as MCP tools
- **Type Safety**: Full type annotations for better IDE support
- **Error Handling**: Consistent error responses across all tools

#### `cloudability_tools.py` - Business Logic
- **API Client**: HTTP client with authentication and error handling
- **Data Processing**: Response parsing and transformation
- **Validation**: Input validation and sanitization
- **Modular Design**: Separated functions for each API endpoint

#### Test Suite
- **Comprehensive Coverage**: Tests for all API endpoints and edge cases
- **HTTP Mocking**: Uses `responses` library for reliable testing
- **Integration Tests**: End-to-end testing with real API schemas
- **Performance Tests**: Validation of response times and memory usage

## 🧪 Testing

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v --cov=main --cov=cloudability_tools --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_cloudability_tools.py -v

# Run specific test
uv run pytest tests/test_cloudability_tools.py::test_get_containers_report -v
```

### Test Structure

- **Unit Tests**: Individual function testing with mocked dependencies
- **Integration Tests**: Full workflow testing with realistic data
- **Error Handling Tests**: Validation of error responses and edge cases
- **Authentication Tests**: Both Bearer token and Basic auth scenarios

### Adding New Tests

When adding new API endpoints:

1. **Add unit tests** in `test_cloudability_tools.py`
2. **Mock HTTP responses** using the `responses` library
3. **Test both success and error cases**
4. **Validate response schemas** match API documentation
5. **Test authentication** for both token types

Example test structure:
```python
@responses.activate
def test_new_endpoint():
    # Mock the API response
    responses.add(
        responses.GET,
        "https://api.cloudability.com/v3/new-endpoint",
        json={"result": "expected_data"},
        status=200
    )
    
    # Call the function
    result = new_endpoint_function(authorization="Bearer token")
    
    # Validate the result
    assert result["result"] == "expected_data"
```

## 🔧 Development Workflow

### Local Development

1. **Start the development server**:
   ```bash
   uv run python main.py
   ```

2. **Test with MCP client**:
   ```bash
   # The server runs on stdio by default for MCP compatibility
   # Use your preferred MCP client to connect
   ```

3. **Manual API testing**:
   ```bash
   # Test individual functions
   uv run python -c "
   from cloudability_tools import get_clusters
   result = get_clusters(authorization='Bearer your-token')
   print(result)
   "
   ```

### Code Style

We use automated formatting and linting:

```bash
# Format code
uv run black .
uv run isort .

# Type checking
uv run mypy main.py cloudability_tools.py

# Run all quality checks
uv run black . && uv run isort . && uv run mypy main.py cloudability_tools.py
```

### Adding New API Endpoints

1. **Research the API**: Study Cloudability API documentation
2. **Implement in `cloudability_tools.py`**:
   ```python
   def new_api_function(param1: str, authorization: str) -> Dict[str, Any]:
       """
       Description of what this function does.
       
       Args:
           param1: Description of parameter
           authorization: Bearer token or Basic auth string
           
       Returns:
           API response data
       """
       # Implementation
   ```

3. **Add MCP tool in `main.py`**:
   ```python
   @mcp.tool()
   def new_tool(param1: str, authorization: str) -> Dict[str, Any]:
       """Tool description for MCP clients."""
       return new_api_function(param1, authorization)
   ```

4. **Write comprehensive tests**
5. **Update documentation** in README.md and tool.yaml

## 🐛 Debugging

### Common Issues

#### Authentication Errors
- **Bearer Token**: Ensure `CLOUDABILITY_ENVIRONMENT_ID` is set correctly
- **Basic Auth**: Verify API key format includes trailing colon
- **Region**: Check API URL matches your Cloudability region

#### API Rate Limits
- **Container APIs**: 10 requests/user/minute, 20/org/minute
- **Cost Reports**: 20 requests/user/minute
- **Implement backoff**: Add retry logic for 429 responses

#### Environment Issues
- **Python Version**: Ensure Python 3.14+ is being used
- **Dependencies**: Run `uv sync` to update dependencies
- **Environment Variables**: Verify `.env` file is properly configured

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Profiling

For performance analysis:
```bash
uv run python -m cProfile -o profile.stats main.py
```

## 📚 API Documentation

### Cloudability API Regions

- **US**: `https://api.cloudability.com/v3`
- **EU**: `https://api-eu.cloudability.com/v3`
- **APAC**: `https://api-au.cloudability.com/v3`
- **ME**: `https://api-me.cloudability.com/v3`

### Authentication Methods

#### Bearer Token (Modern)
```python
authorization = f"Bearer {apptio_opentoken}"
```

#### Basic Auth (Legacy)
```python
authorization = f"Basic {api_key}:"
```

### Rate Limiting

Different endpoints have different rate limits:
- **Container APIs**: 10/user/min, 20/org/min
- **Cost Reports**: 20/user/min
- **Budgets**: Standard rate limits apply

## 🚀 Deployment

### Local Testing
```bash
# Run the server
uv run python main.py

# Test with curl (if HTTP mode)
curl -X POST http://localhost:8000/tools \
  -H "Content-Type: application/json" \
  -d '{"name": "list_clusters", "arguments": {"authorization": "Bearer token"}}'
```

### Production Considerations

- **Environment Variables**: Use secure secret management
- **Rate Limiting**: Implement client-side rate limiting
- **Error Handling**: Log errors for monitoring
- **Health Checks**: Add health check endpoints
- **Security**: Validate all inputs and sanitize outputs

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

### Quick Contribution Checklist

- [ ] Fork the repository
- [ ] Create a feature branch
- [ ] Add tests for new functionality
- [ ] Ensure all tests pass
- [ ] Update documentation
- [ ] Submit a pull request

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/eelzinaty/cloudability-mcp-server/issues)
- **Discussions**: [GitHub Discussions](https://github.com/eelzinaty/cloudability-mcp-server/discussions)
- **Documentation**: [README.md](README.md)
