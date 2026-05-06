from fastmcp import FastMCP
from typing import Dict, List, Optional, Any
from cloudability_tools import (
    get_containers_report,
    get_clusters,
    get_budgets,
    get_budget_details,
    get_billing_accounts,
    get_cost_reports_legacy,
    get_usage_data_legacy,
    # Budgets & Forecasting APIs
    get_estimate,
    get_forecast,
    create_budget,
    update_budget,
    delete_budget,
    create_budget_subscription,
    get_budget_subscription,
    list_budget_subscriptions,
    update_budget_subscription,
    delete_budget_subscription,
    # Cost Reporting APIs
    list_cost_reports,
    get_cost_measures,
    get_cost_filter_operators,
    run_cost_report,
    enqueue_cost_report,
    get_report_state,
    get_report_results,
    # Container APIs
    provision_cluster,
    get_cluster_deployment_config,
    list_provisioned_clusters,
    update_provisioned_cluster,
    get_container_clusters,
    get_container_allocations,
    get_container_usage,
    get_container_labels,
    get_container_counts,
    # Container APIs
    provision_cluster,
    get_cluster_deployment_config,
    list_provisioned_clusters,
    update_provisioned_cluster,
    get_container_clusters,
    get_container_allocations,
    get_container_usage,
    get_container_labels,
    get_container_counts
)

mcp = FastMCP("Cloudability MCP Server")

# ============================================================================
# CONTAINERS TOOLS
# ============================================================================

@mcp.tool()
def containers_report(
    start_date: str,
    end_date: str,
    cost_type: str = "adjusted",
    metrics: List[str] | None = None,
    group: List[str] | None = None,
    filters: List[str] | None = None,
    widget_type: str = "top",
    limit: int = 50,
    sort: List[Dict[str, str]] | None = None,
    view_id: Optional[str] = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Get comprehensive containers cost and usage report from Cloudability.

    This is the main containers reporting endpoint providing detailed cost and usage
    analytics for Kubernetes workloads with advanced filtering and grouping capabilities.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        cost_type: Cost type - "adjusted" (cash) or "total_adjusted_amortized"
        metrics: List of metrics to retrieve (e.g., ["total_cost", "total_cost_efficiency"])
        group: List of dimensions to group by (e.g., ["cluster", "namespace"])
        filters: List of filter expressions (e.g., ["cluster==uuid", "namespace==kube-system"])
        widget_type: Widget type - "top", "kpi", "bar", or "line"
        limit: Maximum number of results (1-1000)
        sort: List of sort configurations with sortMetric and sortOrder
        view_id: Optional Cloudability view identifier
        authorization: Bearer token or Basic auth header

    Returns:
        Detailed cost and usage report with metrics, dimensions, and pagination info
    """
    return get_containers_report(
        start_date, end_date, cost_type, metrics, group, filters,
        widget_type, limit, sort, view_id, authorization
    )

@mcp.tool()
def list_clusters(authorization: str | None = None) -> Dict[str, Any]:
    """
    Get list of all Kubernetes clusters in Cloudability.

    Returns cluster information including UUIDs, names, and metadata needed
    for filtering other API calls.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of clusters with their identifiers and metadata
    """
    return get_clusters(authorization)

# ============================================================================
# BUDGETS TOOLS
# ============================================================================

@mcp.tool()
def list_budgets(authorization: str | None = None) -> Dict[str, Any]:
    """
    Get list of all budgets configured in Cloudability.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of budgets with their configurations and current status
    """
    return get_budgets(authorization)

@mcp.tool()
def get_budget(budget_id: str, authorization: str | None = None) -> Dict[str, Any]:
    """
    Get detailed information for a specific budget.

    Args:
        budget_id: Unique identifier for the budget
        authorization: Bearer token or Basic auth header

    Returns:
        Detailed budget information including thresholds, alerts, and current spend
    """
    return get_budget_details(budget_id, authorization)

# ============================================================================
# BILLING ACCOUNTS TOOLS
# ============================================================================

@mcp.tool()
def list_billing_accounts(authorization: str | None = None) -> Dict[str, Any]:
    """
    Get list of billing accounts configured in Cloudability.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of billing accounts with their configurations and metadata
    """
    return get_billing_accounts(authorization)

# ============================================================================
# BUDGETS & FORECASTING TOOLS
# ============================================================================

@mcp.tool()
def get_spending_estimate(
    view_id: str = "0",
    basis: str = "cash",
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Generate a spending estimate for the current month.

    Provides detailed projections of current month spending based on historical patterns
    and month-to-date usage, including spending drivers by service and usage family.

    Args:
        view_id: View ID to generate estimate for (0 = all cost data)
        basis: Cost basis - "cash", "amortized", "adjusted", "adjustedAmortized", "list"
        authorization: Bearer token or Basic auth header

    Returns:
        Estimate object with:
        - estimatedSpend: Projected spending for current month
        - previousMonthSpend: Last month's total spending
        - cumulativeMtdSpend: Daily spending progression
        - details: Spending drivers by service/usage family

    Note: Limited to 10 requests per user per minute, 20 per org per minute
    """
    return get_estimate(view_id, basis, authorization)

@mcp.tool()
def get_spending_forecast(
    view_id: str = "0",
    basis: str = "cash",
    months_back: int = 6,
    months_forward: int = 12,
    use_current_estimate: bool = False,
    remove_credits: bool = False,
    remove_one_time_charges: bool = False,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Generate a spending forecast for future months.

    Creates predictive models based on historical spending patterns to forecast
    future costs with confidence intervals and detailed service breakdowns.

    Args:
        view_id: View ID to generate forecast for (0 = all cost data)
        basis: Cost basis - "cash", "amortized", "adjusted", "adjustedAmortized", "list"
        months_back: Months of history to use for prediction (3-24)
        months_forward: Months to forecast into the future (1-24)
        use_current_estimate: Include current month estimate in spending model
        remove_credits: Remove credits from the spending model
        remove_one_time_charges: Remove one-time charges from the model
        authorization: Bearer token or Basic auth header

    Returns:
        Forecast object with:
        - forecast: Monthly projections with confidence bounds
        - forecastDetail: Service-level forecast breakdowns
        - actual: Historical spending for comparison
        - actualDetail: Historical service-level spending
        - parameters: Forecast configuration used
    """
    return get_forecast(
        view_id, basis, months_back, months_forward,
        use_current_estimate, remove_credits, remove_one_time_charges,
        authorization
    )

# ============================================================================
# BUDGET MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
def create_new_budget(
    name: str,
    basis: str,
    view_id: str = "0",
    months: List[Dict[str, Any]] | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Create a new budget with monthly thresholds.

    Args:
        name: Budget name for identification
        basis: Cost basis - "cash", "amortized", "adjusted", "adjustedAmortized", "list"
        view_id: View ID to apply budget to (0 = all cost data)
        months: List of month objects with "month" (YYYY-MM) and "threshold" (number)
        authorization: Bearer token or Basic auth header

    Returns:
        Created budget object with ID and configuration

    Example months format:
    [
        {"month": "2024-01", "threshold": 10000},
        {"month": "2024-02", "threshold": 12000}
    ]
    """
    return create_budget(name, basis, view_id, months, authorization)

@mcp.tool()
def modify_budget(
    budget_id: str,
    name: str | None = None,
    basis: str | None = None,
    view_id: str | None = None,
    months: List[Dict[str, Any]] | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Update an existing budget configuration.

    Args:
        budget_id: UUID of the budget to update
        name: New budget name (optional)
        basis: New cost basis (optional)
        view_id: New view ID (optional)
        months: New month thresholds (optional)
        authorization: Bearer token or Basic auth header

    Returns:
        Updated budget object
    """
    return update_budget(budget_id, name, basis, view_id, months, authorization)

@mcp.tool()
def remove_budget(budget_id: str, authorization: str | None = None) -> Dict[str, Any]:
    """
    Delete a budget permanently.

    Args:
        budget_id: UUID of the budget to delete
        authorization: Bearer token or Basic auth header

    Returns:
        Success confirmation
    """
    success = delete_budget(budget_id, authorization)
    return {"success": success, "message": f"Budget {budget_id} deleted successfully"}

# ============================================================================
# BUDGET SUBSCRIPTION TOOLS
# ============================================================================

@mcp.tool()
def create_budget_alert(
    budget_id: str,
    notify_exceeded: bool = False,
    notify_expected: bool = False,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Create email notifications for budget thresholds.

    Args:
        budget_id: UUID of the budget to monitor
        notify_exceeded: Send alerts when actual spend exceeds budget
        notify_expected: Send alerts when projected spend exceeds budget
        authorization: Bearer token or Basic auth header

    Returns:
        Created subscription object with notification settings
    """
    return create_budget_subscription(budget_id, notify_exceeded, notify_expected, authorization)

@mcp.tool()
def get_budget_alert(
    subscription_id: str,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Get details of a specific budget subscription.

    Args:
        subscription_id: UUID of the subscription
        authorization: Bearer token or Basic auth header

    Returns:
        Budget subscription object with notification settings
    """
    return get_budget_subscription(subscription_id, authorization)

@mcp.tool()
def list_budget_alerts(authorization: str | None = None) -> Dict[str, Any]:
    """
    Get all budget subscriptions and their notification settings.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of all budget subscription objects
    """
    return list_budget_subscriptions(authorization)

@mcp.tool()
def modify_budget_alert(
    subscription_id: str,
    budget_id: str | None = None,
    notify_exceeded: bool | None = None,
    notify_expected: bool | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Update budget subscription notification settings.

    Args:
        subscription_id: UUID of the subscription to update
        budget_id: New budget ID to monitor (optional)
        notify_exceeded: New setting for actual spend alerts (optional)
        notify_expected: New setting for projected spend alerts (optional)
        authorization: Bearer token or Basic auth header

    Returns:
        Updated subscription object
    """
    return update_budget_subscription(
        subscription_id, budget_id, notify_exceeded, notify_expected, authorization
    )

@mcp.tool()
def remove_budget_alert(
    subscription_id: str,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Delete a budget subscription permanently.

    Args:
        subscription_id: UUID of the subscription to delete
        authorization: Bearer token or Basic auth header

    Returns:
        Success confirmation
    """
    success = delete_budget_subscription(subscription_id, authorization)
    return {"success": success, "message": f"Budget subscription {subscription_id} deleted successfully"}

# ============================================================================
# COST REPORTING TOOLS
# ============================================================================

@mcp.tool()
def list_saved_cost_reports(authorization: str | None = None) -> Dict[str, Any]:
    """
    Get list of saved cost reports owned by or shared with the user/organization.

    Returns detailed information about each saved report including dimensions,
    metrics, filters, and sharing permissions.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of cost report objects with complete configurations and metadata
    """
    return {"result": list_cost_reports(authorization)}

@mcp.tool()
def get_available_measures(
    apply_allocations: bool | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Get comprehensive list of available cost reporting measures.

    Returns all dimensions and metrics that can be used in cost reports,
    including their data types, descriptions, and grouping information.

    Args:
        apply_allocations: If true, only measures supported by cost sharing are listed
        authorization: Bearer token or Basic auth header

    Returns:
        List of measures with metadata:
        - Dimensions: vendor, region, service_name, resource_identifier, etc.
        - Metrics: total_cost, amortized_cost, usage_hours, etc.
        - Each with data_type, description, group, and sub_group info
    """
    return {"result": get_cost_measures(apply_allocations, authorization)}

@mcp.tool()
def get_filter_operators(authorization: str | None = None) -> Dict[str, Any]:
    """
    Get list of available filter operators for cost reporting.

    Returns all comparison operators that can be used in cost report filters.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of operators: ==, !=, >, <, >=, <=, =@, !=@, []=, []!=, ===, !==
        - == (equals), != (not equals)
        - > (greater than), < (less than)
        - =@ (contains), !=@ (does not contain)
        - []= (in), []!= (not in)
        - === (strictly equals), !== (strictly not equals)
    """
    return {"result": get_cost_filter_operators(authorization)}

@mcp.tool()
def execute_cost_report(
    start_date: str,
    end_date: str,
    dimensions: List[str],
    metrics: List[str],
    filters: List[str] | None = None,
    sort: List[str] | None = None,
    limit: int | None = None,
    offset: int | None = None,
    chart: bool = False,
    view_id: str | None = None,
    apply_allocations: bool | None = None,
    token: str | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Execute a comprehensive cost report with advanced filtering and analytics.

    This is the primary cost reporting tool providing flexible, detailed cost analysis
    with support for up to 15 dimensions and 8 metrics, advanced filtering, sorting,
    and pagination for large datasets.

    Args:
        start_date: Start date (YYYY-MM-DD or relative like "beginning of last month")
        end_date: End date (YYYY-MM-DD or relative like "end of last month")
        dimensions: List of dimensions (max 15, e.g., ["vendor", "region", "service_name"])
        metrics: List of metrics (max 8, e.g., ["total_amortized_cost", "usage_hours"])
        filters: Filter expressions (e.g., ["transaction_type==usage", "region=@us-east"])
        sort: Sort expressions (e.g., ["total_amortized_costDESC", "vendorASC"])
        limit: Max rows (default 10000, set 0 for 64000)
        offset: Starting position for pagination
        chart: Format data for chart visualization (date-based)
        view_id: View ID to apply (0 for unrestricted access)
        apply_allocations: Include post-allocated costs
        token: Pagination token for navigating large result sets
        authorization: Bearer token or Basic auth header

    Returns:
        Comprehensive cost report with:
        - results: Array of cost data rows
        - meta: Detailed metadata (dates, filters, metrics, dimensions, aggregates)
        - pagination: Navigation tokens for large datasets
        - total_results: Total number of matching rows

    Examples:
        Basic vendor breakdown:
        dimensions=["vendor"], metrics=["total_amortized_cost"]

        Regional analysis with filters:
        dimensions=["vendor", "region"], filters=["transaction_type==usage"]

        Resource-level detail:
        dimensions=["resource_identifier", "service_name"],
        filters=["total_amortized_cost>100"]

    Note: Pagination triggers automatically at 10,000 rows
    """
    return run_cost_report(
        start_date, end_date, dimensions, metrics, filters, sort,
        limit, offset, chart, view_id, apply_allocations, token, authorization
    )

@mcp.tool()
def queue_cost_report(
    start_date: str,
    end_date: str,
    dimensions: List[str],
    metrics: List[str],
    filters: List[str] | None = None,
    sort: List[str] | None = None,
    limit: int | None = None,
    offset: int | None = None,
    chart: bool = False,
    view_id: str | None = None,
    apply_allocations: bool | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Queue a cost report for asynchronous processing.

    Use this for long-running reports that might timeout with synchronous execution.
    Returns a report ID that can be used to check processing status and retrieve
    results when complete.

    Args:
        start_date: Start date (YYYY-MM-DD or relative date)
        end_date: End date (YYYY-MM-DD or relative date)
        dimensions: List of dimensions (max 15)
        metrics: List of metrics (max 8)
        filters: Filter expressions
        sort: Sort expressions
        limit: Maximum rows to return
        offset: Starting position
        chart: Format for chart visualization
        view_id: View ID to apply
        apply_allocations: Include post-allocated costs
        authorization: Bearer token or Basic auth header

    Returns:
        Object with report ID for tracking: {"id": 12345}

    Note:
        - Limited to 20 requests per user
        - Use check_report_status and get_queued_report_results to retrieve data
        - Pagination occurs at 30,000 rows (vs 10,000 for sync reports)
    """
    return enqueue_cost_report(
        start_date, end_date, dimensions, metrics, filters, sort,
        limit, offset, chart, view_id, apply_allocations, authorization
    )

@mcp.tool()
def check_report_status(
    report_id: str,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Check the processing status of a queued cost report.

    Args:
        report_id: Report ID returned from queue_cost_report
        authorization: Bearer token or Basic auth header

    Returns:
        Status object with current state:
        - "enqueued": Report is waiting to be processed
        - "running": Report is currently being generated
        - "finished": Report is complete and ready for retrieval
        - "errored": Report failed to process
    """
    return get_report_state(report_id, authorization)

@mcp.tool()
def get_queued_report_results(
    report_id: str,
    token: str | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Retrieve results from a completed queued cost report.

    Args:
        report_id: ID of the finished report
        token: Pagination token for large reports (30,000+ rows)
        authorization: Bearer token or Basic auth header

    Returns:
        Standard cost report object with results, metadata, and pagination

    Note: Only works for reports with status "finished"
    """
    return get_report_results(report_id, token, authorization)

# ============================================================================
# CONTAINER PROVISIONING TOOLS
# ============================================================================

@mcp.tool()
def provision_kubernetes_cluster(
    cluster_name: str,
    kubernetes_version: str | None = None,
    cluster_version: str | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Provision a new Kubernetes cluster for Cloudability monitoring.

    This creates the necessary credentials and generates a deployment configuration
    for the Cloudability Metrics Agent to be installed in your cluster.

    Args:
        cluster_name: Unique name for the cluster (cannot be modified after creation)
        kubernetes_version: Kubernetes version (e.g., "1.25") - use this OR cluster_version
        cluster_version: Cluster version (e.g., "openshift_4.12", "kubernetes_1.25")
        authorization: Bearer token or Basic auth header

    Returns:
        Provisioned cluster object with ID and configuration details

    Note: After provisioning, use get_cluster_deployment_yaml to retrieve the
          deployment configuration for installing the Metrics Agent.
    """
    return provision_cluster(cluster_name, kubernetes_version, cluster_version, authorization)

@mcp.tool()
def get_cluster_deployment_yaml(
    cluster_id: str,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Get the Kubernetes deployment YAML for a provisioned cluster.

    Returns the complete deployment configuration that should be applied to your
    cluster to install the Cloudability Metrics Agent.

    Args:
        cluster_id: ID of the provisioned cluster (from provision_kubernetes_cluster)
        authorization: Bearer token or Basic auth header

    Returns:
        Kubernetes deployment YAML configuration as string

    Usage:
        1. Save the returned YAML to a file
        2. Apply it to your cluster: kubectl apply -f deployment.yaml
        3. The Metrics Agent will start collecting data automatically
    """
    yaml_content = get_cluster_deployment_config(cluster_id, authorization)
    return {"deployment_yaml": yaml_content}

@mcp.tool()
def list_all_provisioned_clusters(authorization: str | None = None) -> Dict[str, Any]:
    """
    Get list of all clusters provisioned for Cloudability monitoring.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of provisioned clusters with their configurations and status
    """
    return list_provisioned_clusters(authorization)

@mcp.tool()
def update_cluster_configuration(
    cluster_id: str,
    kubernetes_version: str | None = None,
    cluster_version: str | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Update the configuration of a provisioned cluster.

    Args:
        cluster_id: ID of the cluster to update
        kubernetes_version: New Kubernetes version
        cluster_version: New cluster version
        authorization: Bearer token or Basic auth header

    Returns:
        Updated cluster configuration

    Note: After updating, retrieve the new deployment YAML and re-deploy
          to your cluster to update the Metrics Agent.
    """
    return update_provisioned_cluster(cluster_id, kubernetes_version, cluster_version, authorization)

# ============================================================================
# CONTAINER ANALYTICS TOOLS
# ============================================================================

@mcp.tool()
def get_detailed_cluster_info(
    start_date: str,
    end_date: str,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Get comprehensive information about clusters and their nodes.

    Provides detailed cluster metadata including node information, timestamps
    for first/last data received, and provisioning details.

    Args:
        start_date: Start date for cluster data window (YYYY-MM-DD)
        end_date: End date for cluster data window (YYYY-MM-DD)
        authorization: Bearer token or Basic auth header

    Returns:
        Detailed cluster information including:
        - Cluster IDs, names, and provisioning dates
        - Node details with vendor and resource identifiers
        - Data collection timestamps (firstSeen, lastSeen)
        - Organization metadata (hasProvisioned, hasData)
    """
    return get_container_clusters(start_date, end_date, authorization)

@mcp.tool()
def analyze_container_cost_allocations(
    start_date: str,
    end_date: str,
    group: List[str] | None = None,
    metrics: List[str] | None = None,
    filters: List[str] | None = None,
    cost_type: str = "adjusted_cost",
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Perform comprehensive container cost allocation analysis.

    This is the primary tool for understanding how shared Kubernetes resources
    are being used and how costs should be allocated across teams, namespaces,
    services, and other dimensions.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        group: Grouping dimensions (e.g., ["namespace", "service", "deployment"])
        metrics: Resource metrics (e.g., ["cpu/reserved", "memory/reserved_rss", "network/tx"])
        filters: Filter expressions (e.g., ["cluster==uuid", "namespace==production"])
        cost_type: Cost basis - "adjusted_cost", "adjusted_amortized_cost", or empty
        authorization: Bearer token or Basic auth header

    Returns:
        Comprehensive allocation data including:
        - Cost allocations by group with fair share calculations
        - Resource usage metrics (CPU, memory, network, filesystem)
        - Allocation percentages and unallocated resources
        - Available resources and weighting factors

    Available Grouping Dimensions:
        - cluster, namespace, service, deployment, pod
        - daemonset, job, replicaset, replication_controller
        - cldy:labels:* (for custom Kubernetes labels)

    Available Metrics:
        - cpu/reserved, cpu/usage
        - memory/reserved, memory/reserved_rss, memory/usage
        - network/tx, network/rx
        - filesystem/usage

    Example Usage:
        # Cost by namespace
        group=["namespace"], metrics=["cpu/reserved", "memory/reserved_rss"]

        # Service-level analysis for specific cluster
        group=["service"], filters=["cluster==abc-123", "namespace==production"]

        # Team allocation using labels
        group=["cldy:labels:team"], metrics=["cpu/reserved"]
    """
    return get_container_allocations(
        start_date, end_date, group, metrics, filters, cost_type, authorization
    )

@mcp.tool()
def get_container_resource_usage(
    start_date: str,
    end_date: str,
    metrics: List[str] | None = None,
    filters: List[str] | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Get daily container resource usage trends and patterns.

    Reports resource allocation percentages and average values by day,
    perfect for understanding usage patterns and capacity planning.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        metrics: Resource metrics to analyze (e.g., ["cpu/reserved", "filesystem/usage"])
        filters: Filter expressions to scope the analysis
        authorization: Bearer token or Basic auth header

    Returns:
        Daily usage data with:
        - Allocation percentages by day
        - Resource usage values (mean) by day
        - Available resource capacity by day
        - Trends over the specified time period

    Perfect for:
        - Capacity planning and rightsizing
        - Understanding usage patterns
        - Identifying resource waste or constraints
        - Tracking efficiency improvements over time
    """
    return get_container_usage(start_date, end_date, metrics, filters, authorization)

@mcp.tool()
def discover_container_labels(
    start_date: str,
    end_date: str,
    filters: List[str] | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Discover Kubernetes labels available for cost allocation and filtering.

    Returns all label keys observed in your clusters during the specified timeframe,
    which can then be used for grouping and filtering in other analyses.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        filters: Filter expressions to scope the discovery
        authorization: Bearer token or Basic auth header

    Returns:
        List of available label keys with their display names

    Usage:
        Use discovered labels in other tools with the format "cldy:labels:LABELNAME"
        For example, if you discover a "team" label, use "cldy:labels:team" in
        grouping or filtering expressions.
    """
    return get_container_labels(start_date, end_date, filters, authorization)

@mcp.tool()
def count_container_resources(
    start_date: str,
    end_date: str,
    dimensions: List[str],
    group: List[str] | None = None,
    filters: List[str] | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Count distinct container resources across dimensions.

    Provides counts of namespaces, services, pods, deployments, and other
    Kubernetes resources, optionally grouped by cluster or other dimensions.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        dimensions: Dimensions to count (e.g., ["namespace", "service", "pod"])
        group: Group results by dimensions (e.g., ["cluster"])
        filters: Filter expressions to scope the counting
        authorization: Bearer token or Basic auth header

    Returns:
        Counts of distinct values grouped by specified dimensions

    Available Dimensions:
        - cluster, namespace, service, deployment, pod
        - daemonset, job, replicaset, replication_controller
        - cldy:labels:* (for custom labels)

    Perfect for:
        - Understanding cluster scale and complexity
        - Resource inventory and governance
        - Capacity planning across environments
        - Comparing cluster sizes and configurations
    """
    return get_container_counts(start_date, end_date, dimensions, group, filters, authorization)

# ============================================================================
# LEGACY TOOLS (for backward compatibility)
# ============================================================================

@mcp.tool()
def get_cost_reports(start_date: str, end_date: str, dimensions: list[str] | None = None, authorization: str | None = None):
    """
    Legacy cost reports endpoint for backward compatibility.

    Note: This endpoint may not reflect the actual Cloudability API structure.
    Consider using containers_report for comprehensive cost analysis.
    """
    return get_cost_reports_legacy(start_date, end_date, dimensions, authorization)

@mcp.tool()
def get_usage_data(period: str, authorization: str | None = None):
    """
    Legacy usage data endpoint for backward compatibility.

    Note: This endpoint may not reflect the actual Cloudability API structure.
    Consider using containers_report for comprehensive usage analysis.
    """
    return get_usage_data_legacy(period, authorization)

# Internal functions for testing
_get_cost_reports = get_cost_reports_legacy
_get_usage_data = get_usage_data_legacy

if __name__ == "__main__":
    mcp.run()
