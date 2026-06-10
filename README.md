# Cloudability MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-0.19+-green.svg)](https://github.com/jlowin/fastmcp)

A comprehensive Model Context Protocol (MCP) server for the Cloudability API, providing advanced cost management, Kubernetes container analytics, and budget forecasting capabilities.

## 🌟 Why Use This MCP Server?

- **🔥 Container-First**: Comprehensive Kubernetes cost allocation and monitoring
- **📊 Advanced Analytics**: 15 dimensions, 8 metrics, flexible filtering and grouping
- **💰 Budget Management**: Complete budget lifecycle with forecasting and alerts
- **🚀 Production Ready**: Full test coverage, type safety, and error handling
- **🌍 Multi-Region**: Support for US, EU, APAC, and ME Cloudability regions
- **🔐 Flexible Auth**: Bearer tokens, legacy Basic auth, or Frontdoor API keys for automatic token acquisition

## 🚀 Quick Start

### Prerequisites

- **Python 3.14+** (required for modern type annotations)
- **uv** (recommended package manager)
- **Cloudability API access** (Bearer token, API key, or Frontdoor API keys in `.env`)

### Installation

```bash
# Clone the repository
git clone https://github.com/eelzinaty/cloudability-mcp-server.git
cd cloudability-mcp-server

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Set up configuration
cp .env.example .env
# Edit .env with your Cloudability credentials

# Run the server
uv run python main.py
```

### MCP Client Configuration

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "cloudability": {
      "command": "uv",
      "args": ["run", "python", "main.py"],
      "cwd": "/path/to/cloudability-mcp-server",
      "env": {
        "CLOUDABILITY_API_URL": "https://api.cloudability.com/v3",
        "CLOUDABILITY_ENVIRONMENT_ID": "your-environment-id",
        "CLOUDABILITY_DEFAULT_VIEW_ID": "12345",
        "CLOUDABILITY_KEY_ACCESS": "your-public-key",
        "CLOUDABILITY_KEY_SECRET": "your-private-key",
        "CLOUDABILITY_FRONTDOOR_URL": "https://frontdoor.apptio.com/service/apikeylogin"
      }
    }
  }
}
```

## Features

### 🚀 **Comprehensive API Coverage**
- **🔥 Container Cost Allocation**: Complete Kubernetes cost allocation and monitoring
- **🔥 Container Provisioning**: Cluster setup and Metrics Agent deployment
- **🔥 Container Analytics**: Usage patterns, resource allocation, and efficiency analysis
- **🔥 Container Discovery**: Labels and resource inventory via containers_report
- **Cost Reporting**: Flexible, powerful cost analysis with 15 dimensions & 8 metrics
- **Asynchronous Reports**: Queue long-running reports for background processing
- **Budgets & Forecasting**: Complete budget lifecycle management and spending predictions
- **Budget Subscriptions**: Email notifications for budget thresholds
- **Estimates**: Current month spending projections with detailed breakdowns
- **Forecasts**: Multi-month predictive analytics with confidence intervals
- **Vendor Accounts**: List cloud provider credential accounts (AWS, Azure, GCP, IBM, OCI)
### 🔐 **Flexible Authentication**
- **Bearer Token**: Modern apptio-opentoken authentication
- **Frontdoor API Keys**: Automatic apptio-opentoken acquisition when keys are set in the environment
- **Basic Auth**: Traditional API key authentication
- **Multi-Region Support**: US, EU, APAC, and ME Cloudability API and Frontdoor login endpoints

### 📊 **Advanced Analytics**
- **Rich Filtering**: Filter by cluster, namespace, workload type, and more
- **Flexible Grouping**: Group results by multiple dimensions
- **Sorting & Pagination**: Handle large datasets efficiently
- **Multiple Widget Types**: Support for tables, KPIs, charts, and time series

### 🛠️ **Developer Experience**
- **FastMCP Framework**: Modern MCP server implementation
- **Comprehensive Testing**: Full test coverage with mocking
- **Type Safety**: Complete type annotations for better IDE support
- **Clean Architecture**: Separated business logic for maintainability

## Installation

This project uses `uv` for dependency management. Make sure you have `uv` installed.

```bash
# Install dependencies
uv sync

# Install development dependencies (for testing)
uv sync --dev
```

## Configuration

Create a `.env` file based on `.env.example`:

```bash
# Copy the example configuration
cp .env.example .env
```

### Environment Variables

Copy `.env.example` to `.env` and configure the variables below.

| Variable | Required | Description |
|----------|----------|-------------|
| `CLOUDABILITY_API_URL` | No (defaults to US) | Cloudability API base URL for your region |
| `CLOUDABILITY_ENVIRONMENT_ID` | Yes (for Bearer auth) | Environment ID from Access Administration |
| `CLOUDABILITY_KEY_ACCESS` | No | Frontdoor public API key for automatic token acquisition |
| `CLOUDABILITY_KEY_SECRET` | No | Frontdoor private API key (pair with `CLOUDABILITY_KEY_ACCESS`) |
| `CLOUDABILITY_FRONTDOOR_URL` | No (defaults to US) | Frontdoor API key login endpoint for your region |
| `CLOUDABILITY_DEFAULT_VIEW_ID` | Yes (for containers tools) | Default view ID for containers/report and clusters calls |

```bash
# Cloudability API Base URL (choose based on your region)
# US: https://api.cloudability.com/v3
# EU: https://api-eu.cloudability.com/v3
# APAC: https://api-au.cloudability.com/v3
# ME: https://api-me.cloudability.com/v3
CLOUDABILITY_API_URL=https://api.cloudability.com/v3

# Required for Bearer token authentication (apptio-opentoken)
# Get this from your Access Administration environment
CLOUDABILITY_ENVIRONMENT_ID=your-environment-id-here

# Optional: Frontdoor API keys for automatic apptio-opentoken acquisition
# When set, tools can omit the authorization parameter
# CLOUDABILITY_KEY_ACCESS=your-public-key-here
# CLOUDABILITY_KEY_SECRET=your-private-key-here

# Optional: Frontdoor login URL (defaults to US region)
# US: https://frontdoor.apptio.com/service/apikeylogin
# EU: https://frontdoor-eu.apptio.com/service/apikeylogin
# AU: https://frontdoor-au.apptio.com/service/apikeylogin
# CLOUDABILITY_FRONTDOOR_URL=https://frontdoor.apptio.com/service/apikeylogin

# Default view ID for containers API calls (required for containers/report and clusters)
CLOUDABILITY_DEFAULT_VIEW_ID=12345
```

#### Regional endpoints

**Cloudability API (`CLOUDABILITY_API_URL`)**

| Region | URL |
|--------|-----|
| US | `https://api.cloudability.com/v3` |
| EU | `https://api-eu.cloudability.com/v3` |
| APAC | `https://api-au.cloudability.com/v3` |
| ME | `https://api-me.cloudability.com/v3` |

**Frontdoor login (`CLOUDABILITY_FRONTDOOR_URL`)**

| Region | URL |
|--------|-----|
| US | `https://frontdoor.apptio.com/service/apikeylogin` |
| EU | `https://frontdoor-eu.apptio.com/service/apikeylogin` |
| AU | `https://frontdoor-au.apptio.com/service/apikeylogin` |

### Authentication Methods

#### 1. Frontdoor API Keys (optional, server-side)
When `CLOUDABILITY_KEY_ACCESS` and `CLOUDABILITY_KEY_SECRET` are set, the server exchanges them for an apptio-opentoken via `CLOUDABILITY_FRONTDOOR_URL`. Tool calls can omit the `authorization` parameter. Set `CLOUDABILITY_ENVIRONMENT_ID` as well — Bearer authentication still requires it.

#### 2. Bearer Token
For modern Cloudability environments using apptio-opentoken:
- Set `CLOUDABILITY_ENVIRONMENT_ID` in your environment
- Pass `authorization: "Bearer your-apptio-opentoken"` to tool calls (unless Frontdoor keys handle auth for you)

#### 3. Basic Auth (Legacy)
For traditional API key authentication:
- Pass `authorization: "Basic your-api-key:"` to tool calls
- No environment ID required

## Usage

### Running the Server

```bash
uv run python main.py
```

### MCP Reference Resources

Read-only reference data for building cost reports (cached, default TTL 15 minutes via `CLOUDABILITY_RESOURCE_CACHE_TTL_SECONDS`):

| URI | Description |
|-----|-------------|
| `cloudability://config` | Server config (API URL, default view ID, auth mode — no secrets) |
| `cloudability://measures` | Cost report dimensions and metrics catalog |
| `cloudability://measures/allocated` | Measures supported with cost allocations |
| `cloudability://filter-operators` | Filter operator reference (`==`, `=@`, `[]=`, …) |
| `cloudability://saved-reports` | Saved cost report definitions |

Use `resources/read` in your MCP client, or call the matching tools (`get_available_measures`, etc.) for the same data.

### Available Tools

#### 🔥 **Container Cost Allocation Tools**

##### `provision_kubernetes_cluster`
**Set up new clusters** for Cloudability monitoring with automated Metrics Agent deployment.

##### `get_cluster_deployment_yaml`
**Get deployment configuration** for installing the Cloudability Metrics Agent in your cluster.

##### `containers_report`
**Primary container cost allocation tool** — replaces the retired `/containers/allocations` and `/containers/counts` APIs with `POST /v3/containers/report`.

**Key Features:**
- **Shared resource allocation**: Fairshare and allocated cost metrics by namespace, workload, cluster, and labels
- **Flexible grouping**: namespace, workload_type, workload_name, pod, labels, etc.
- **Filtering**: cluster UUID, namespace, workload type, and more

**Parameters:**
- `group`: Grouping dimensions (e.g., ["namespace"], ["cldy:labels:team"])
- `metrics`: Report metrics (e.g., ["total_cost", "total_cost_efficiency"])
- `filters`: Scope analysis (e.g., ["cluster==uuid", "namespace==production"])
- `cost_type`: "adjusted" or "total_adjusted_amortized"

**Returns:**
- `result.data` rows with grouped dimensions and metrics
- Pagination via `result.pagination.nextToken`

##### `get_container_resource_usage`
**Daily usage trends** for capacity planning and rightsizing analysis.

##### `discover_container_labels`
**Find available Kubernetes labels** for custom cost allocation groupings.

##### `get_detailed_cluster_info`
**Comprehensive cluster metadata** with node details and data collection status.

#### 🚀 **Primary Tools**

##### `list_clusters`
**Get all Kubernetes clusters** with their UUIDs and metadata.

##### `list_budgets`
**Get all budget configurations** with current status and thresholds.

##### `get_budget`
**Get detailed budget information** including spend tracking and alerts.

##### `list_aws_accounts`
**Get AWS vendor credential accounts** configured in Cloudability (`GET /v3/vendors/AWS/accounts?viewId=0`).

##### `list_azure_accounts`
**Get Azure vendor credential accounts** configured in Cloudability (`GET /v3/vendors/azure/accounts?viewId=0`).

##### `list_gcp_accounts`
**Get GCP vendor credential accounts** configured in Cloudability (`GET /v3/vendors/gcp/accounts?viewId=0`).

##### `list_ibm_accounts`
**Get IBM Cloud vendor credential accounts** configured in Cloudability (`GET /v3/vendors/ibm/accounts?viewId=0`).

##### `list_oci_accounts`
**Get OCI vendor credential accounts** configured in Cloudability (`GET /v3/vendors/oci/accounts?viewId=0`).

#### 📊 **Budgets & Forecasting Tools**

##### `get_spending_estimate`
**Current month spending projections** with detailed service breakdowns and daily progression.

**Key Features:**
- Real-time spending estimates based on month-to-date usage
- Service-level spending drivers (AWS EC2, RDS, etc.)
- Daily cumulative spending progression
- Comparison with previous month actuals
- Rate limiting: 10 requests/user/minute, 20/org/minute

**Response format:** Standard Cloudability v3 envelope. All fields are under `result` (not top-level):

```json
{
  "result": {
    "estimatedSpend": 35615446.36,
    "previousMonthSpend": 33819722.57,
    "previousMonthFinalized": true,
    "currentDate": "2026-05-24",
    "cumulativeMtdSpend": [{"date": "2026-05-01", "spend": 1615288.82}],
    "details": [
      {
        "serviceName": "Azure Compute",
        "estimatedSpend": 5568954.48,
        "mtdSpend": 4128094.29,
        "previousMonthSpend": 5409219.11,
        "usageFamily": "Instance Usage"
      }
    ]
  }
}
```

Use `result["details"]` for vendor or service breakdowns (for example, filter lines where `serviceName` starts with `Azure`). Omit `view_id` or set it from the `cloudability://config` resource `default_view_id` when using the server's configured default view (`0` means all org cost data).

##### `get_spending_forecast`
**Multi-month predictive analytics** with confidence intervals and historical comparison.

**Parameters:**
- `months_back` (3-24): Historical data for modeling
- `months_forward` (1-24): Forecast horizon
- `use_current_estimate`: Include current month in model
- `remove_credits`: Exclude credits from analysis
- `remove_one_time_charges`: Filter out one-time costs

**Returns:** Cloudability v3 envelope with forecast data under `result` (for example `result.forecast`, `result.forecastDetail`, `result.actual`, `result.parameters`).

##### `create_new_budget`
**Create budgets** with monthly thresholds and cost basis configuration.

##### `modify_budget`
**Update existing budgets** with new thresholds or configuration changes.

##### `remove_budget`
**Delete budgets** permanently from the system.

##### `create_budget_alert`
**Set up email notifications** for budget threshold breaches.

**Notification Types:**
- `notify_exceeded`: Alerts when actual spend exceeds budget
- `notify_expected`: Alerts when projected spend exceeds budget

##### `list_budget_alerts`
**List budget subscriptions** and notification preferences.

##### `modify_budget_alert` / `remove_budget_alert`
**Update or delete** budget notification subscriptions.

#### 📊 **Cost Reporting Tools**

##### `execute_cost_report`
**Primary cost reporting tool** with advanced analytics and flexible configuration.

**Key Features:**
- **Up to 15 dimensions**: vendor, region, service_name, resource_identifier, etc.
- **Up to 8 metrics**: total_cost, amortized_cost, usage_hours, etc.
- **Advanced filtering**: 12 operators (==, !=, >, <, =@, []= etc.)
- **Flexible sorting**: Multi-column with ASC/DESC
- **Automatic pagination**: Handles 10,000+ row datasets
- **Relative dates**: "beginning of last month", "end of this quarter"
- **Chart formatting**: Date-based visualization support
- **View integration**: Apply saved views and allocations

**Parameters:**
- `dimensions`: List of grouping dimensions (max 15)
- `metrics`: List of cost/usage metrics (max 8)
- `filters`: Filter expressions (e.g., ["transaction_type==usage"])
- `sort`: Sort expressions (e.g., ["total_costDESC"])
- `start_date`/`end_date`: Date range or relative dates
- `view_id`: Apply saved view (0 for unrestricted)
- `apply_allocations`: Include post-allocated costs

##### `queue_cost_report`
**Asynchronous reporting** for long-running or complex reports.

**Benefits:**
- **Background processing**: No timeout limitations
- **Large datasets**: Pagination at 30,000 rows vs 10,000
- **Status tracking**: Monitor progress with `check_report_status`
- **Rate limiting**: 20 requests per user protection

##### `list_saved_cost_reports`
**Discover available reports** with complete configurations and sharing info.

##### `get_available_measures`
**Explore dimensions and metrics** with detailed metadata and grouping.

##### `get_filter_operators`
**Reference guide** for all supported filter comparison operators.

##### `check_report_status` / `get_queued_report_results`
**Manage asynchronous reports** from queue to completion.

## Testing

Run the test suite:

```bash
# Run unit tests (mocked HTTP; integration tests are skipped by default)
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ -v --cov=main --cov-report=term-missing

# Run live MCP + Cloudability API integration tests (requires .env credentials)
cp .env.example .env   # set CLOUDABILITY_KEY_ACCESS, CLOUDABILITY_KEY_SECRET, CLOUDABILITY_ENVIRONMENT_ID
uv run pytest tests/test_mcp_integration.py -v -m integration
```

Integration tests cover 10 core read-only MCP tools (budgets, cost reporting, containers), 3 optional tools that skip when your tenant lacks access, plus a chained `get_budget` test.

## Examples

### Container Cost Allocation (Most Important!)
```python
# Provision a new cluster for monitoring
cluster = provision_kubernetes_cluster(
    cluster_name="production-k8s",
    kubernetes_version="1.28",
    authorization="Bearer your-token"
)

# Get deployment YAML for Metrics Agent
deployment = get_cluster_deployment_yaml(
    cluster_id=cluster["result"]["id"],
    authorization="Bearer your-token"
)
# Save deployment["deployment_yaml"] and apply: kubectl apply -f deployment.yaml

# Analyze cost allocation by namespace (primary use case)
allocation = containers_report(
    start_date="2024-01-01",
    end_date="2024-01-31",
    group=["namespace"],
    metrics=["total_cost", "total_cost_efficiency"],
    authorization="Bearer your-token"
)

# Team-based cost allocation using labels
team_costs = containers_report(
    start_date="2024-01-01",
    end_date="2024-01-31",
    group=["cldy:labels:team", "namespace"],
    metrics=["total_cost", "total_cost_allocated"],
    filters=["cluster==your-cluster-uuid"],
    cost_type="total_adjusted_amortized",
    authorization="Bearer your-token"
)

# Workload-level cost breakdown for a namespace
service_costs = containers_report(
    start_date="2024-01-01",
    end_date="2024-01-31",
    group=["workload_name", "workload_type"],
    metrics=["total_cost"],
    filters=["namespace==production", "cluster==your-cluster-uuid"],
    authorization="Bearer your-token"
)
```

### Container Resource Analysis
```python
# Daily usage trends for capacity planning
usage_trends = get_container_resource_usage(
    start_date="2024-01-01",
    end_date="2024-01-31",
    metrics=["cpu/reserved", "memory/reserved_rss", "filesystem/usage"],
    filters=["cluster==your-cluster-uuid"],
    authorization="Bearer your-token"
)

# Discover available labels for cost allocation
labels = discover_container_labels(
    start_date="2024-01-01",
    end_date="2024-01-31",
    filters=["cluster==your-cluster-uuid"],
    authorization="Bearer your-token"
)

# Get detailed cluster information
cluster_info = get_detailed_cluster_info(
    start_date="2024-01-01",
    end_date="2024-01-31",
    authorization="Bearer your-token"
)
```

### Basic Cost Analysis
```python
# Get cost breakdown by namespace for the last month
result = containers_report(
    start_date="2024-01-01",
    end_date="2024-01-31",
    metrics=["total_cost", "total_cost_efficiency"],
    group=["namespace"],
    authorization="Bearer your-token"
)
```

### Advanced Filtering
```python
# Get cost data for specific cluster and production workloads
result = containers_report(
    start_date="2024-01-01",
    end_date="2024-01-31",
    filters=[
        "cluster==your-cluster-uuid",
        "namespace==production",
        "workload_type[]=deployment,statefulset"
    ],
    group=["workload_name"],
    sort=[{"sortMetric": "total_cost", "sortOrder": "desc"}],
    limit=10,
    authorization="Bearer your-token"
)
```

### Budget Monitoring
```python
# Check all budgets and their current status
budgets = list_budgets(authorization="Basic your-api-key:")

# Get detailed information for a specific budget
budget_details = get_budget(
    budget_id="budget-123",
    authorization="Basic your-api-key:"
)
```

### Spending Estimates & Forecasts
```python
# Get current month spending estimate (fields are under result)
estimate = get_spending_estimate(
    view_id="0",
    basis="cash",
    authorization="Bearer your-token"
)
summary = estimate["result"]
print(summary["estimatedSpend"], summary["currentDate"])

# Azure month-end estimate from service breakdown
azure_estimate = sum(
    row["estimatedSpend"]
    for row in summary["details"]
    if row["serviceName"].startswith("Azure")
)

# Generate 12-month forecast based on 6 months of history
forecast = get_spending_forecast(
    view_id="0",
    basis="cash",
    months_back=6,
    months_forward=12,
    use_current_estimate=True,
    remove_one_time_charges=True,
    authorization="Bearer your-token"
)
forecast_rows = forecast["result"]["forecast"]
```

### Budget Management
```python
# Create a quarterly budget
budget = create_new_budget(
    name="Q1 2024 Budget",
    basis="adjusted",
    view_id="0",
    months=[
        {"month": "2024-01", "threshold": 50000},
        {"month": "2024-02", "threshold": 55000},
        {"month": "2024-03", "threshold": 60000}
    ],
    authorization="Bearer your-token"
)

# Set up budget alerts
alert = create_budget_alert(
    budget_id=budget["result"]["id"],
    notify_exceeded=True,
    notify_expected=True,
    authorization="Bearer your-token"
)

# Update budget thresholds
updated_budget = modify_budget(
    budget_id=budget["result"]["id"],
    months=[
        {"month": "2024-01", "threshold": 45000},
        {"month": "2024-02", "threshold": 50000}
    ],
    authorization="Bearer your-token"
)
```

### Advanced Cost Reporting
```python
# Basic cost breakdown by vendor and region
basic_report = execute_cost_report(
    start_date="2024-01-01",
    end_date="2024-01-31",
    dimensions=["vendor", "region"],
    metrics=["total_amortized_cost", "usage_hours"],
    authorization="Bearer your-token"
)

# Advanced filtering and sorting
filtered_report = execute_cost_report(
    start_date="beginning of last month",
    end_date="end of last month",
    dimensions=["vendor", "service_name", "resource_identifier"],
    metrics=["total_amortized_cost", "total_cost_efficiency"],
    filters=[
        "transaction_type==usage",
        "total_amortized_cost>100",
        "region=@us-east"
    ],
    sort=["total_amortized_costDESC", "vendorASC"],
    limit=1000,
    authorization="Bearer your-token"
)

# Asynchronous reporting for large datasets
report_id = queue_cost_report(
    start_date="2024-01-01",
    end_date="2024-03-31",
    dimensions=["resource_identifier", "service_name", "region"],
    metrics=["total_amortized_cost", "usage_hours"],
    filters=["vendor==Amazon"],
    authorization="Bearer your-token"
)

# Check status and retrieve results
status = check_report_status(
    report_id=report_id["id"],
    authorization="Bearer your-token"
)

if status["status"] == "finished":
    results = get_queued_report_results(
        report_id=report_id["id"],
        authorization="Bearer your-token"
    )

# Discover available dimensions and metrics
measures = get_available_measures(authorization="Bearer your-token")
operators = get_filter_operators(authorization="Bearer your-token")
```

## Development

### Project Structure

```
cloudability-mcp-server/
├── main.py                      # Main MCP server with tool definitions
├── cloudability_tools.py        # Core API implementation
├── tests/
│   └── test_cloudability_tools.py # Comprehensive API tests
├── .env.example                 # Environment configuration template
├── pyproject.toml              # Project configuration
└── README.md                   # This documentation
```

### Architecture

- **main.py**: Clean MCP tool definitions using FastMCP decorators
- **cloudability_tools.py**: Separated business logic with comprehensive API coverage
- **Flexible Authentication**: Support for both Bearer tokens and Basic auth
- **Comprehensive Testing**: Full test coverage with HTTP mocking
- **Type Safety**: Complete type annotations for better development experience

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes with tests
4. Run quality checks: `uv run black . && uv run pytest`
5. Submit a pull request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/eelzinaty/cloudability-mcp-server.git
cd cloudability-mcp-server

# Install development dependencies
uv sync --group dev

# Run tests
uv run pytest tests/ -v

# Format code
uv run black . && uv run isort .
```

## 📚 Documentation

- **[Development Guide](DEVELOPMENT.md)**: Comprehensive development documentation
- **[Contributing Guide](CONTRIBUTING.md)**: How to contribute to the project
- **[API Documentation](tool.yaml)**: Complete tool schema definitions
- **[Cloudability API Docs](https://developers.cloudability.com/)**: Official API documentation

## 🐛 Issues & Support

- **Bug Reports**: [GitHub Issues](https://github.com/eelzinaty/cloudability-mcp-server/issues)
- **Feature Requests**: [GitHub Issues](https://github.com/eelzinaty/cloudability-mcp-server/issues)
- **Discussions**: [GitHub Discussions](https://github.com/eelzinaty/cloudability-mcp-server/discussions)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[FastMCP](https://github.com/jlowin/fastmcp)**: Modern MCP server framework
- **[Model Context Protocol](https://modelcontextprotocol.io/)**: The protocol specification
- **Cloudability**: For providing comprehensive cloud cost management APIs

## 🔗 Related Projects

- **[MCP Servers](https://github.com/modelcontextprotocol/servers)**: Official MCP server implementations
- **[Claude Desktop](https://claude.ai/desktop)**: Popular MCP client
- **[Other MCP Tools](https://github.com/topics/model-context-protocol)**: Community MCP implementations

---

**Made with ❤️ for the FinOps and Kubernetes communities**
