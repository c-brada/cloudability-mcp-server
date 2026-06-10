from fastmcp import FastMCP
from typing import Annotated, Any
from pydantic import BeforeValidator, Field
import json as _json

from cloudability_resources import register_resources
from cloudability_tools import (
    get_containers_report,
    get_clusters,
    get_budgets,
    get_budget_details,
    get_vendor_accounts,
    # Budgets & Forecasting APIs
    get_estimate,
    get_forecast,
    create_budget,
    update_budget,
    delete_budget,
    create_budget_subscription,
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
    get_container_usage,
    get_container_labels,
)


def _coerce_str_list(v: Any) -> Any:
    """Accept a JSON-encoded string in place of a list, e.g. '["a","b"]' → ["a","b"]."""
    if isinstance(v, str):
        try:
            parsed = _json.loads(v)
            if isinstance(parsed, list):
                return parsed
        except (_json.JSONDecodeError, ValueError):
            pass
        return [v]  # single bare string → one-element list
    return v


StrList = Annotated[list[str], BeforeValidator(_coerce_str_list)]

mcp = FastMCP("Cloudability MCP Server")

# ============================================================================
# CONTAINERS TOOLS
# ============================================================================

@mcp.tool()
def containers_report(
    start_date: str,
    end_date: str,
    cost_type: str = "adjusted",
    metrics: Annotated[
        StrList | None,
        Field(
            default=None,
            description=(
                'Metrics to retrieve. Defaults to ["total_cost", "total_cost_efficiency"] '
                "if omitted. total_cost is fairshare-allocated workload cost, NOT "
                "billing/invoiced cost — use execute_cost_report for unblended_cost, "
                "idle overhead, and amortized metrics."
            ),
        ),
    ] = None,
    group: Annotated[
        StrList | None,
        Field(
            default=None,
            description=(
                "Grouping dimensions. Standard values: cluster, namespace, workload_type, "
                "workload_name, container, pod, node, region, zone. Kubernetes labels: "
                "cldy:labels:<key>. Time grouping: only day is supported (not month); use "
                "group=['day'] with widget_type bar or line. widget_type top must not "
                "include time dimensions — split the date range or aggregate days client-side."
            ),
        ),
    ] = None,
    count: Annotated[
        StrList | None,
        Field(
            default=None,
            description=(
                "Dimensions to count distinct values for (replaces retired /containers/counts). "
                "Returns counts under result.data[].count. Examples: namespace, workload_name, "
                "pod, cluster. Combine with group to count within each group row."
            ),
        ),
    ] = None,
    filters: Annotated[
        StrList | None,
        Field(
            default=None,
            description=(
                "Filter expressions (e.g., cluster==<uuid>, namespace==kube-system, "
                "workload_type[]=deployment,statefulset). Cluster filters require the "
                "cluster UUID from list_clusters, not the cluster name."
            ),
        ),
    ] = None,
    widget_type: Annotated[
        str,
        Field(
            default="top",
            description=(
                "Response format: top (table, default), bar, or line. kpi is accepted but "
                "remapped to top because the Cloudability API returns HTTP 400 for kpi — "
                "use top with no group (org total) or group=['cluster'] with a cluster "
                "filter (cluster total). Use bar/line only when group includes day for "
                "time-series output. top must not include day/month in group."
            ),
        ),
    ] = "top",
    limit: int = 50,
    pagination_token: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Pagination token from result.pagination.nextToken for the next page. "
                "When set, all other request parameters must match the original query "
                "exactly. Responses may be truncated at limit with no further pages "
                "retrievable if this is omitted."
            ),
        ),
    ] = None,
    sort: list[dict[str, str]] | None = None,
    view_id: Annotated[
        str | None,
        Field(
            default=None,
            description="Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted)",
        ),
    ] = None,
    authorization: str | None = None
) -> dict[str, Any]:
    """
    Get Kubernetes workload cost and usage report from Cloudability (fairshare model).

    Reports fairshare-allocated container costs for namespaces, workloads, and clusters.
    total_cost does not reconcile with execute_cost_report billing totals and omits
    unallocated/idle overhead in namespace breakdowns. Use execute_cost_report for
    invoiced cost, idle resources, and amortized metrics.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        cost_type: Cost type - "adjusted" (cash) or "total_adjusted_amortized"
        metrics: Defaults to ["total_cost", "total_cost_efficiency"] when omitted
        group: Grouping dimensions (see parameter Field description for valid values)
        count: Distinct-value counts per row (replaces retired count_container_resources)
        filters: Filter expressions (cluster==uuid from list_clusters; not clusterName)
        widget_type: top (table), bar, or line; kpi is remapped to top (see Field desc)
        limit: Maximum number of results (1-1000); may truncate — use pagination_token
        sort: List of sort configurations with sortMetric and sortOrder
        pagination_token: nextToken from a prior response for the next page
        view_id: Cloudability view ID (required unless CLOUDABILITY_DEFAULT_VIEW_ID is set)
        authorization: Bearer token or Basic auth header

    Returns:
        Report with result.data rows, result.pagination (hasNext, nextToken), and
        _kpi_remapped_to_top when widget_type kpi was translated to top

    Grouping notes (per Cloudability Report API):
        - Standard: cluster, namespace, workload_type, workload_name, container, pod, etc.
        - Labels: cldy:labels:<key> (discover keys with discover_container_labels)
        - Time: only day is valid; month/year_month are not supported on this endpoint
        - widget_type top: aggregated table over the full date range (no time in group)
        - widget_type bar/line: requires group to include day for time-series buckets
        - KPI totals: use top with no group (org) or top + group cluster + cluster filter

    Example:
        group=["cldy:labels:team"], filters=["cluster==dd2d2d9a-6d6b-4965-8fbf-3482f9a4e7a3"]

        group=["cluster"], count=["namespace"], filters=["cluster==dd2d2d9a-..."]
    """
    return get_containers_report(
        start_date,
        end_date,
        cost_type,
        metrics,
        group,
        count,
        filters,
        widget_type,
        limit,
        sort,
        view_id,
        pagination_token,
        authorization,
    )

@mcp.tool()
def list_clusters(
    start_date: str,
    end_date: str,
    view_id: Annotated[
        str | None,
        Field(
            default=None,
            description="Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted)",
        ),
    ] = None,
    concise: bool = True,
    authorization: str | None = None,
) -> dict[str, Any]:
    """
    Get list of all Kubernetes clusters in Cloudability.

    Returns cluster information including UUIDs, names, vendor, cluster type,
    and metadata needed for filtering other API calls.

    Args:
        start_date: Start date for cluster data window (YYYY-MM-DD)
        end_date: End date for cluster data window (YYYY-MM-DD)
        view_id: Cloudability view ID (required unless CLOUDABILITY_DEFAULT_VIEW_ID is set)
        concise: When True, omit per-node details (faster, smaller payload)
        authorization: Bearer token or Basic auth header

    Returns:
        Clusters with identifiers, names, vendor, clusterType, and timestamps
    """
    return get_clusters(
        start_date=start_date,
        end_date=end_date,
        view_id=view_id,
        concise=concise,
        authorization=authorization,
    )

# ============================================================================
# BUDGETS TOOLS
# ============================================================================

@mcp.tool()
def list_budgets(authorization: str | None = None) -> dict[str, Any]:
    """
    Get list of all budgets configured in Cloudability.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of budgets with their configurations and current status
    """
    return get_budgets(authorization)

@mcp.tool()
def get_budget(budget_id: str, authorization: str | None = None) -> dict[str, Any]:
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
# VENDOR ACCOUNTS TOOLS
# ============================================================================

@mcp.tool()
def list_aws_accounts(
    view_id: Annotated[
        str | None,
        Field(
            default=None,
            description='Cloudability view ID (defaults to "0" for all org accounts)',
        ),
    ] = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """Get list of AWS vendor credential accounts configured in Cloudability."""
    return get_vendor_accounts("aws", view_id, authorization)


@mcp.tool()
def list_azure_accounts(
    view_id: Annotated[
        str | None,
        Field(
            default=None,
            description='Cloudability view ID (defaults to "0" for all org accounts)',
        ),
    ] = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """Get list of Azure vendor credential accounts configured in Cloudability."""
    return get_vendor_accounts("azure", view_id, authorization)


@mcp.tool()
def list_gcp_accounts(
    view_id: Annotated[
        str | None,
        Field(
            default=None,
            description='Cloudability view ID (defaults to "0" for all org accounts)',
        ),
    ] = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """Get list of GCP vendor credential accounts configured in Cloudability."""
    return get_vendor_accounts("gcp", view_id, authorization)


@mcp.tool()
def list_ibm_accounts(
    view_id: Annotated[
        str | None,
        Field(
            default=None,
            description='Cloudability view ID (defaults to "0" for all org accounts)',
        ),
    ] = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """Get list of IBM Cloud vendor credential accounts configured in Cloudability."""
    return get_vendor_accounts("ibm", view_id, authorization)


@mcp.tool()
def list_oci_accounts(
    view_id: Annotated[
        str | None,
        Field(
            default=None,
            description='Cloudability view ID (defaults to "0" for all org accounts)',
        ),
    ] = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """Get list of OCI vendor credential accounts configured in Cloudability."""
    return get_vendor_accounts("oci", view_id, authorization)

# ============================================================================
# BUDGETS & FORECASTING TOOLS
# ============================================================================

@mcp.tool(
    description=(
        "Generate a spending estimate for the current month based on month-to-date "
        "usage and historical patterns. "
        "Response is the Cloudability v3 envelope {\"result\": {...}}; summary and "
        "breakdown fields are nested under result (not top-level): "
        "result.estimatedSpend (projected month-end total), "
        "result.previousMonthSpend, result.previousMonthFinalized, "
        "result.currentDate (YYYY-MM-DD), "
        "result.cumulativeMtdSpend ([{date, spend}, ...]), and "
        "result.details ([{serviceName, estimatedSpend, mtdSpend, "
        "previousMonthSpend, usageFamily}, ...] for service/vendor breakdown). "
        "Filter vendors via result.details (e.g. lines where serviceName starts with "
        "\"Azure\"). Omit view_id to use CLOUDABILITY_DEFAULT_VIEW_ID; pass "
        "view_id \"0\" for all org cost data. "
        "Rate limit: 10 requests/user/minute, 20/org/minute."
    ),
)
def get_spending_estimate(
    view_id: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted; "
                "pass \"0\" for all org cost data)"
            ),
        ),
    ] = None,
    basis: str = "cash",
    authorization: str | None = None
) -> dict[str, Any]:
    """
    Generate a spending estimate for the current month.

    Provides detailed projections of current month spending based on historical patterns
    and month-to-date usage, including spending drivers by service and usage family.

    Args:
        view_id: Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted;
            pass "0" for all org cost data)
        basis: Cost basis - "cash", "amortized", "adjusted", "adjustedAmortized", "list"
        authorization: Bearer token or Basic auth header

    Returns:
        Cloudability v3 envelope ``{"result": {...}}``. Summary and breakdown
        fields are nested under ``result`` (not top-level):

        - result.estimatedSpend: Projected spending for current month
        - result.previousMonthSpend: Last month's total spending
        - result.previousMonthFinalized: Whether prior month actuals are final
        - result.currentDate: As-of date for the estimate (YYYY-MM-DD)
        - result.cumulativeMtdSpend: Daily MTD progression [{date, spend}, ...]
        - result.details: Spending drivers by service/usage family
          [{serviceName, estimatedSpend, mtdSpend, previousMonthSpend, usageFamily}, ...]

    Note: Limited to 10 requests per user per minute, 20 per org per minute
    """
    return get_estimate(view_id, basis, authorization)

@mcp.tool(
    description=(
        "Generate a multi-month spending forecast from historical patterns. "
        "Response is the Cloudability v3 envelope {\"result\": {...}}; forecast data "
        "is nested under result (not top-level), including result.forecast "
        "(monthly projections with confidence bounds), result.forecastDetail "
        "(service-level breakdown), result.actual, result.actualDetail, and "
        "result.parameters. Omit view_id to use CLOUDABILITY_DEFAULT_VIEW_ID; pass "
        "view_id \"0\" for all org cost data. "
        "Rate limit: 10 requests/user/minute, 20/org/minute."
    ),
)
def get_spending_forecast(
    view_id: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted; "
                "pass \"0\" for all org cost data)"
            ),
        ),
    ] = None,
    basis: str = "cash",
    months_back: int = 6,
    months_forward: int = 12,
    use_current_estimate: bool = False,
    remove_credits: bool = False,
    remove_one_time_charges: bool = False,
    authorization: str | None = None
) -> dict[str, Any]:
    """
    Generate a spending forecast for future months.

    Creates predictive models based on historical spending patterns to forecast
    future costs with confidence intervals and detailed service breakdowns.

    Args:
        view_id: Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted;
            pass "0" for all org cost data)
        basis: Cost basis - "cash", "amortized", "adjusted", "adjustedAmortized", "list"
        months_back: Months of history to use for prediction (3-24)
        months_forward: Months to forecast into the future (1-24)
        use_current_estimate: Include current month estimate in spending model
        remove_credits: Remove credits from the spending model
        remove_one_time_charges: Remove one-time charges from the model
        authorization: Bearer token or Basic auth header

    Returns:
        Cloudability v3 envelope ``{"result": {...}}``. Forecast fields are
        nested under ``result``, for example ``result.forecast``,
        ``result.forecastDetail``, ``result.actual``, ``result.actualDetail``,
        and ``result.parameters``.

    Note: Limited to 10 requests per user per minute, 20 per org per minute
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
    months: list[dict[str, Any]] | None = None,
    authorization: str | None = None
) -> dict[str, Any]:
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
    months: list[dict[str, Any]] | None = None,
    authorization: str | None = None
) -> dict[str, Any]:
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
def remove_budget(budget_id: str, authorization: str | None = None) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
def list_budget_alerts(authorization: str | None = None) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
def list_saved_cost_reports(authorization: str | None = None) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
def get_filter_operators(authorization: str | None = None) -> dict[str, Any]:
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
    dimensions: StrList,
    metrics: StrList,
    filters: StrList | None = None,
    sort: StrList | None = None,
    limit: int | None = None,
    offset: int | None = None,
    chart: bool = False,
    view_id: str | None = None,
    apply_allocations: bool | None = None,
    token: str | None = None,
    authorization: str | None = None
) -> dict[str, Any]:
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
    dimensions: StrList,
    metrics: StrList,
    filters: StrList | None = None,
    sort: StrList | None = None,
    limit: int | None = None,
    offset: int | None = None,
    chart: bool = False,
    view_id: str | None = None,
    apply_allocations: bool | None = None,
    authorization: str | None = None
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
def list_all_provisioned_clusters(
    view_id: Annotated[
        str | None,
        Field(
            default=None,
            description="Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted)",
        ),
    ] = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """
    Get list of all clusters provisioned for Cloudability monitoring.

    Args:
        view_id: Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted)
        authorization: Bearer token or Basic auth header

    Returns:
        List of provisioned clusters with their configurations and status
    """
    return list_provisioned_clusters(view_id=view_id, authorization=authorization)

@mcp.tool()
def update_cluster_configuration(
    cluster_id: str,
    kubernetes_version: str | None = None,
    cluster_version: str | None = None,
    authorization: str | None = None
) -> dict[str, Any]:
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
    view_id: Annotated[
        str | None,
        Field(
            default=None,
            description="Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted)",
        ),
    ] = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """
    Get comprehensive information about clusters and their nodes.

    Provides detailed cluster metadata including node information, timestamps
    for first/last data received, and provisioning details.

    Args:
        start_date: Start date for cluster data window (YYYY-MM-DD)
        end_date: End date for cluster data window (YYYY-MM-DD)
        view_id: Cloudability view ID (required unless CLOUDABILITY_DEFAULT_VIEW_ID is set)
        authorization: Bearer token or Basic auth header

    Returns:
        Detailed cluster information including:
        - Cluster IDs, names, and provisioning dates
        - Node details with vendor and resource identifiers
        - Data collection timestamps (firstSeen, lastSeen)
        - Organization metadata (hasProvisioned, hasData)
    """
    return get_container_clusters(
        start_date, end_date, view_id=view_id, concise=False, authorization=authorization
    )

@mcp.tool()
def get_container_resource_usage(
    start_date: str,
    end_date: str,
    metrics: StrList | None = None,
    filters: StrList | None = None,
    view_id: Annotated[
        str | None,
        Field(
            default=None,
            description="Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted)",
        ),
    ] = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """
    Get daily container resource usage trends and patterns.

    Reports resource allocation percentages and average values by day,
    perfect for understanding usage patterns and capacity planning.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        metrics: Resource metrics to analyze (e.g., ["cpu/reserved", "filesystem/usage"])
        filters: Filter expressions to scope the analysis
        view_id: Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted)
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
    return get_container_usage(
        start_date, end_date, metrics, filters, view_id, authorization
    )

@mcp.tool()
def discover_container_labels(
    start_date: str,
    end_date: str,
    filters: Annotated[
        StrList | None,
        Field(
            default=None,
            description=(
                "Filter expressions using the same syntax as containers_report. "
                "Scope to a cluster with "
                "cluster==<uuid> (resolve UUID via list_clusters; clusterName is not "
                "valid). Examples: namespace==kube-system, workload_type==deployment."
            ),
        ),
    ] = None,
    view_id: Annotated[
        str | None,
        Field(
            default=None,
            description="Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted)",
        ),
    ] = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """
    Discover Kubernetes labels available for cost allocation and filtering.

    Returns all label keys observed in your clusters during the specified timeframe,
    which can then be used for grouping and filtering in other analyses.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        filters: Same filter syntax as containers_report (cluster==uuid, not clusterName)
        view_id: Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted)
        authorization: Bearer token or Basic auth header

    Returns:
        List of available label keys with their display names

    Usage:
        Use discovered labels in other tools with the format "cldy:labels:LABELNAME"
        For example, if you discover a "team" label, use "cldy:labels:team" in
        grouping or filtering expressions.

    Example:
        list_clusters → then filters=["cluster==dd2d2d9a-6d6b-4965-8fbf-3482f9a4e7a3"]
    """
    return get_container_labels(start_date, end_date, filters, view_id, authorization)

# ============================================================================
# REFERENCE RESOURCES
# ============================================================================

register_resources(mcp)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Cloudability MCP server")
    parser.add_argument(
        "--transport",
        "-t",
        choices=["stdio", "http", "sse", "streamable-http"],
        help="Transport protocol (default: stdio, or FASTMCP_TRANSPORT env var)",
    )
    parser.add_argument("--host", help="Host to bind for HTTP transports")
    parser.add_argument("--port", "-p", type=int, help="Port to bind for HTTP transports")
    parser.add_argument("--path", help="Route path for HTTP transports")
    parser.add_argument(
        "--log-level",
        "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level",
    )
    parser.add_argument("--no-banner", action="store_true", help="Suppress the server banner")
    args = parser.parse_args()

    run_kwargs: dict[str, Any] = {}
    if args.transport is not None:
        run_kwargs["transport"] = args.transport
    if args.host is not None:
        run_kwargs["host"] = args.host
    if args.port is not None:
        run_kwargs["port"] = args.port
    if args.path is not None:
        run_kwargs["path"] = args.path
    if args.log_level is not None:
        run_kwargs["log_level"] = args.log_level
    if args.no_banner:
        run_kwargs["show_banner"] = False

    mcp.run(**run_kwargs)
