"""
Cloudability API tools for MCP server.
Comprehensive implementation of Cloudability API v3 endpoints.
"""

import requests
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CLOUDABILITY_API_URL = os.getenv("CLOUDABILITY_API_URL", "https://api.cloudability.com/v3")

def get_auth_headers(authorization: str) -> Dict[str, str]:
    """Get authentication headers for Cloudability API."""
    if not authorization:
        raise ValueError("Authorization token is required")
    
    # Support both Basic Auth (API key) and Bearer token (apptio-opentoken)
    if authorization.startswith("Bearer "):
        # Extract token for apptio-opentoken header
        token = authorization.replace("Bearer ", "")
        env_id = os.getenv("CLOUDABILITY_ENVIRONMENT_ID")
        if not env_id:
            raise ValueError("CLOUDABILITY_ENVIRONMENT_ID is required for Bearer token authentication")
        return {
            "apptio-opentoken": token,
            "apptio-environmentid": env_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    else:
        # Basic Auth with API key
        return {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

# ============================================================================
# CONTAINERS API - COMPREHENSIVE KUBERNETES COST ALLOCATION
# ============================================================================

# Provisioning API
def provision_cluster(
    cluster_name: str,
    kubernetes_version: str | None = None,
    cluster_version: str | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Provision a new Kubernetes cluster for Cloudability monitoring.

    This creates credentials and generates a deployment config for the
    Cloudability Metrics Agent to be installed in the cluster.

    Args:
        cluster_name: Unique name for the cluster (cannot be modified later)
        kubernetes_version: Kubernetes version (e.g., "1.11") - use this OR cluster_version
        cluster_version: Cluster version (e.g., "openshift_4.12", "kubernetes_1.25")
        authorization: Bearer token or Basic auth header

    Returns:
        Provisioned cluster object with ID and configuration details
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    if not kubernetes_version and not cluster_version:
        raise ValueError("Either kubernetes_version or cluster_version is required")

    if kubernetes_version and cluster_version:
        raise ValueError("Provide either kubernetes_version OR cluster_version, not both")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/provisioning"

    data = {"clusterName": cluster_name}
    if kubernetes_version:
        data["kubernetesVersion"] = kubernetes_version
    if cluster_version:
        data["clusterVersion"] = cluster_version

    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

def get_cluster_deployment_config(
    cluster_id: str,
    authorization: str | None = None
) -> str:
    """
    Get the Kubernetes deployment YAML for a provisioned cluster.

    Args:
        cluster_id: ID of the provisioned cluster
        authorization: Bearer token or Basic auth header

    Returns:
        Kubernetes deployment YAML as string
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/provisioning/{cluster_id}/config"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.text

def list_provisioned_clusters(authorization: str | None = None) -> Dict[str, Any]:
    """
    Get list of all provisioned clusters.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of provisioned clusters with their configurations
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/provisioning"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def update_provisioned_cluster(
    cluster_id: str,
    kubernetes_version: str | None = None,
    cluster_version: str | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Update a provisioned cluster configuration.

    Args:
        cluster_id: ID of the cluster to update
        kubernetes_version: New Kubernetes version
        cluster_version: New cluster version
        authorization: Bearer token or Basic auth header

    Returns:
        Updated cluster configuration

    Note: Currently requires ALL fields to be provided (PATCH support coming)
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    if not kubernetes_version and not cluster_version:
        raise ValueError("Either kubernetes_version or cluster_version is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/provisioning/{cluster_id}"

    data = {}
    if kubernetes_version:
        data["kubernetesVersion"] = kubernetes_version
    if cluster_version:
        data["clusterVersion"] = cluster_version

    response = requests.put(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

# Enhanced Clusters API
def get_container_clusters(
    start_date: str,
    end_date: str,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Get detailed information about clusters and their nodes.

    Args:
        start_date: Start date for cluster data window (YYYY-MM-DD)
        end_date: End date for cluster data window (YYYY-MM-DD)
        authorization: Bearer token or Basic auth header

    Returns:
        Detailed cluster information with nodes, timestamps, and metadata
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/clusters"

    params = {
        "start": start_date,
        "end": end_date
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def get_containers_report(
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
    Get containers cost and usage report from Cloudability.
    
    This is the main containers reporting endpoint that provides detailed
    cost and usage analytics for Kubernetes workloads.
    """
    if not authorization:
        raise ValueError("Authorization token is required")
    
    headers = get_auth_headers(authorization)
    
    # Default metrics if none provided
    if metrics is None:
        metrics = ["total_cost", "total_cost_efficiency"]
    
    # Build request body
    request_body = {
        "start": start_date,
        "end": end_date,
        "costType": cost_type,
        "metrics": metrics,
        "widgetType": widget_type,
        "limit": limit
    }
    
    # Add optional parameters
    if group:
        request_body["group"] = group
    if filters:
        request_body["filters"] = filters
    if sort:
        request_body["sort"] = sort
    
    # Build URL with optional view_id
    url = f"{CLOUDABILITY_API_URL}/containers/report"
    params = {}
    if view_id:
        params["viewId"] = view_id
    
    response = requests.post(url, json=request_body, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

# Container Allocations API
def get_container_allocations(
    start_date: str,
    end_date: str,
    group: List[str] | None = None,
    metrics: List[str] | None = None,
    filters: List[str] | None = None,
    cost_type: str = "adjusted_cost",
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Get container cost allocations broken down by specified groupings.

    This analyzes cluster usage, determines resource allocation percentages,
    and divides costs based on actual usage patterns.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        group: Grouping dimensions (e.g., ["namespace", "service"])
        metrics: Metrics to calculate (e.g., ["cpu/reserved", "memory/reserved_rss"])
        filters: Filter expressions (e.g., ["cluster==uuid", "namespace==production"])
        cost_type: Cost basis - "adjusted_cost", "adjusted_amortized_cost", or empty
        authorization: Bearer token or Basic auth header

    Returns:
        Detailed allocation data with costs, percentages, and resource usage
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/allocations"

    params = {
        "start": start_date,
        "end": end_date
    }

    if group:
        params["group"] = ",".join(group)
    if metrics:
        params["metrics"] = ",".join(metrics)
    if filters:
        for filter_expr in filters:
            params.setdefault("filters", []).append(filter_expr)
    if cost_type:
        params["costType"] = cost_type

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

# Container Usage API
def get_container_usage(
    start_date: str,
    end_date: str,
    metrics: List[str] | None = None,
    filters: List[str] | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Get daily resource usage data for containers.

    Reports resource allocation percentages and average values by day
    over the specified time range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        metrics: Metrics to report (e.g., ["cpu/reserved", "filesystem/usage"])
        filters: Filter expressions to scope the data
        authorization: Bearer token or Basic auth header

    Returns:
        Daily usage data with allocation percentages and resource values
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/usage"

    params = {
        "start": start_date,
        "end": end_date
    }

    if metrics:
        params["metrics"] = ",".join(metrics)
    if filters:
        for filter_expr in filters:
            params.setdefault("filters", []).append(filter_expr)

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

# Container Labels API
def get_container_labels(
    start_date: str,
    end_date: str,
    filters: List[str] | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Get list of Kubernetes label keys observed in the specified timeframe.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        filters: Filter expressions to scope the data
        authorization: Bearer token or Basic auth header

    Returns:
        List of label keys with their display names
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/labels"

    params = {
        "start": start_date,
        "end": end_date
    }

    if filters:
        for filter_expr in filters:
            params.setdefault("filters", []).append(filter_expr)

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

# Container Counts API
def get_container_counts(
    start_date: str,
    end_date: str,
    dimensions: List[str],
    group: List[str] | None = None,
    filters: List[str] | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Get counts of distinct values for dimension keys.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        dimensions: Dimensions to count (e.g., ["namespace", "service"])
        group: Group results by dimensions (e.g., ["cluster"])
        filters: Filter expressions to scope the data
        authorization: Bearer token or Basic auth header

    Returns:
        Counts of distinct values grouped by specified dimensions
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/counts"

    params = {
        "start": start_date,
        "end": end_date,
        "dimensions": ",".join(dimensions)
    }

    if group:
        params["group"] = ",".join(group)
    if filters:
        for filter_expr in filters:
            params.setdefault("filters", []).append(filter_expr)

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def get_clusters(authorization: str | None = None) -> Dict[str, Any]:
    """Get list of all clusters."""
    if not authorization:
        raise ValueError("Authorization token is required")
    
    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/clusters"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# ============================================================================
# BUDGETS API
# ============================================================================

def get_budgets(authorization: str | None = None) -> Dict[str, Any]:
    """Get list of all budgets."""
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/budgets"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_budget_details(budget_id: str, authorization: str | None = None) -> Dict[str, Any]:
    """Get details for a specific budget."""
    if not authorization:
        raise ValueError("Authorization token is required")
    
    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/budgets/{budget_id}"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# ============================================================================
# BILLING ACCOUNTS API
# ============================================================================

def get_billing_accounts(authorization: str | None = None) -> Dict[str, Any]:
    """Get list of billing accounts."""
    if not authorization:
        raise ValueError("Authorization token is required")
    
    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/billing-accounts"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# ============================================================================
# BUDGETS & FORECASTING API
# ============================================================================

def get_estimate(
    view_id: str = "0",
    basis: str = "cash",
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Generate a spending estimate for the current month.

    Args:
        view_id: The view ID to generate estimate for (0 = all cost data)
        basis: Cost basis - "cash", "amortized", "adjusted", "adjustedAmortized", "list"
        authorization: Bearer token or Basic auth header

    Returns:
        Estimate object with current month projections and spending drivers
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    params = {
        "viewId": view_id,
        "basis": basis
    }

    url = f"{CLOUDABILITY_API_URL}/estimate"
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def get_forecast(
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

    Args:
        view_id: The view ID to generate forecast for (0 = all cost data)
        basis: Cost basis - "cash", "amortized", "adjusted", "adjustedAmortized", "list"
        months_back: Months of history to use (3-24)
        months_forward: Months to forecast (1-24)
        use_current_estimate: Include current month estimate in model
        remove_credits: Remove credits from spending model
        remove_one_time_charges: Remove one-time charges from model
        authorization: Bearer token or Basic auth header

    Returns:
        Forecast object with projected spending and historical comparison
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    # Validate parameters
    if not (3 <= months_back <= 24):
        raise ValueError("months_back must be between 3 and 24")
    if not (1 <= months_forward <= 24):
        raise ValueError("months_forward must be between 1 and 24")

    headers = get_auth_headers(authorization)
    params = {
        "viewId": view_id,
        "basis": basis,
        "monthsBack": months_back,
        "monthsForward": months_forward,
        "useCurrentEstimate": use_current_estimate,
        "removeCredits": remove_credits,
        "removeOneTimeCharges": remove_one_time_charges
    }

    url = f"{CLOUDABILITY_API_URL}/forecast"
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def create_budget(
    name: str,
    basis: str,
    view_id: str = "0",
    months: List[Dict[str, Any]] | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Create a new budget.

    Args:
        name: Budget name
        basis: Cost basis - "cash", "amortized", "adjusted", "adjustedAmortized", "list"
        view_id: View ID to apply budget to (0 = all cost data)
        months: List of month objects with "month" (YYYY-MM) and "threshold" (number)
        authorization: Bearer token or Basic auth header

    Returns:
        Created budget object
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)

    budget_data = {
        "name": name,
        "basis": basis,
        "viewId": view_id,
        "months": months or []
    }

    url = f"{CLOUDABILITY_API_URL}/budgets"
    response = requests.post(url, json=budget_data, headers=headers)
    response.raise_for_status()
    return response.json()

def update_budget(
    budget_id: str,
    name: str | None = None,
    basis: str | None = None,
    view_id: str | None = None,
    months: List[Dict[str, Any]] | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Update an existing budget.

    Args:
        budget_id: UUID of the budget to update
        name: Budget name
        basis: Cost basis - "cash", "amortized", "adjusted", "adjustedAmortized", "list"
        view_id: View ID to apply budget to
        months: List of month objects with "month" (YYYY-MM) and "threshold" (number)
        authorization: Bearer token or Basic auth header

    Returns:
        Updated budget object
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)

    # Build update data with only provided fields
    budget_data = {}
    if name is not None:
        budget_data["name"] = name
    if basis is not None:
        budget_data["basis"] = basis
    if view_id is not None:
        budget_data["viewId"] = view_id
    if months is not None:
        budget_data["months"] = months

    url = f"{CLOUDABILITY_API_URL}/budgets/{budget_id}"
    response = requests.put(url, json=budget_data, headers=headers)
    response.raise_for_status()
    return response.json()

def delete_budget(budget_id: str, authorization: str | None = None) -> bool:
    """
    Delete a budget.

    Args:
        budget_id: UUID of the budget to delete
        authorization: Bearer token or Basic auth header

    Returns:
        True if deletion was successful
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/budgets/{budget_id}"

    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    return True

def create_budget_subscription(
    budget_id: str,
    notify_exceeded: bool = False,
    notify_expected: bool = False,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Create a budget subscription for email notifications.

    Args:
        budget_id: UUID of the budget to subscribe to
        notify_exceeded: Notify when actual spend exceeds budget
        notify_expected: Notify when expected spend exceeds budget
        authorization: Bearer token or Basic auth header

    Returns:
        Created subscription object
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)

    subscription_data = {
        "budgetId": budget_id,
        "notifyExceeded": notify_exceeded,
        "notifyExpected": notify_expected
    }

    url = f"{CLOUDABILITY_API_URL}/budget-subscriptions"
    response = requests.post(url, json=subscription_data, headers=headers)
    response.raise_for_status()
    return response.json()

def get_budget_subscription(
    subscription_id: str,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Get a specific budget subscription.

    Args:
        subscription_id: UUID of the subscription
        authorization: Bearer token or Basic auth header

    Returns:
        Budget subscription object
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/budget-subscriptions/{subscription_id}"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def list_budget_subscriptions(authorization: str | None = None) -> Dict[str, Any]:
    """
    Get list of all budget subscriptions.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of budget subscription objects
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/budget-subscriptions"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def update_budget_subscription(
    subscription_id: str,
    budget_id: str | None = None,
    notify_exceeded: bool | None = None,
    notify_expected: bool | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Update a budget subscription.

    Args:
        subscription_id: UUID of the subscription to update
        budget_id: UUID of the budget
        notify_exceeded: Notify when actual spend exceeds budget
        notify_expected: Notify when expected spend exceeds budget
        authorization: Bearer token or Basic auth header

    Returns:
        Updated subscription object
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)

    # Build update data with only provided fields
    subscription_data = {}
    if budget_id is not None:
        subscription_data["budgetId"] = budget_id
    if notify_exceeded is not None:
        subscription_data["notifyExceeded"] = notify_exceeded
    if notify_expected is not None:
        subscription_data["notifyExpected"] = notify_expected

    url = f"{CLOUDABILITY_API_URL}/budget-subscriptions/{subscription_id}"
    response = requests.put(url, json=subscription_data, headers=headers)
    response.raise_for_status()
    return response.json()

def delete_budget_subscription(
    subscription_id: str,
    authorization: str | None = None
) -> bool:
    """
    Delete a budget subscription.

    Args:
        subscription_id: UUID of the subscription to delete
        authorization: Bearer token or Basic auth header

    Returns:
        True if deletion was successful
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/budget-subscriptions/{subscription_id}"

    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    return True

# ============================================================================
# COST REPORTING API
# ============================================================================

def list_cost_reports(authorization: str | None = None) -> Dict[str, Any]:
    """
    Get list of saved cost reports owned by or shared with the user/org.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of cost report objects with metadata and configurations
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/reporting/reports/cost"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_cost_measures(
    apply_allocations: bool | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Get list of available cost reporting measures (dimensions and metrics).

    Args:
        apply_allocations: If true, only measures supported by cost sharing are listed
        authorization: Bearer token or Basic auth header

    Returns:
        List of available measures with metadata (dimensions and metrics)
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/reporting/cost/measures"

    params = {}
    if apply_allocations is not None:
        params["apply_allocations"] = str(apply_allocations).lower()

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def get_cost_filter_operators(authorization: str | None = None) -> Dict[str, Any]:
    """
    Get list of available filter operators for cost reporting.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of filter operators (==, !=, >, <, =@, etc.)
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/reporting/cost/filters"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def run_cost_report(
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
    Execute a cost report with flexible filtering, sorting, and pagination.

    Args:
        start_date: Start date (YYYY-MM-DD or relative date like "beginning of last month")
        end_date: End date (YYYY-MM-DD or relative date like "end of last month")
        dimensions: List of dimensions (max 15, e.g., ["vendor", "region"])
        metrics: List of metrics (max 8, e.g., ["total_amortized_cost", "usage_hours"])
        filters: List of filter expressions (e.g., ["transaction_type==usage"])
        sort: List of sort expressions (e.g., ["total_amortized_costASC", "regionDESC"])
        limit: Maximum rows to return (default 10000, set 0 for 64000)
        offset: Starting position for results
        chart: Format data for chart purposes (based on dates)
        view_id: View ID to apply (0 for unrestricted users to remove view)
        apply_allocations: Include post-allocated costs if true
        token: Pagination token for navigating between pages
        authorization: Bearer token or Basic auth header

    Returns:
        Cost report object with results, metadata, and pagination info
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    # Validate limits
    if len(dimensions) > 15:
        raise ValueError("Maximum 15 dimensions allowed")
    if len(metrics) > 8:
        raise ValueError("Maximum 8 metrics allowed")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/reporting/cost/run"

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "dimensions": ",".join(dimensions),
        "metrics": ",".join(metrics)
    }

    # Add optional parameters
    if filters:
        for filter_expr in filters:
            params.setdefault("filters", []).append(filter_expr)
    if sort:
        params["sort"] = ",".join(sort)
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    if chart:
        params["chart"] = "1"
    if view_id is not None:
        params["view_id"] = view_id
    if apply_allocations is not None:
        params["applyAllocations"] = str(apply_allocations).lower()
    if token:
        params["token"] = token

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def enqueue_cost_report(
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
    Enqueue a cost report for asynchronous processing.

    Use this for long-running reports. Returns a report ID that can be used
    to check status and retrieve results later.

    Args:
        start_date: Start date (YYYY-MM-DD or relative date)
        end_date: End date (YYYY-MM-DD or relative date)
        dimensions: List of dimensions (max 15)
        metrics: List of metrics (max 8)
        filters: List of filter expressions
        sort: List of sort expressions
        limit: Maximum rows to return
        offset: Starting position for results
        chart: Format data for chart purposes
        view_id: View ID to apply
        apply_allocations: Include post-allocated costs if true
        authorization: Bearer token or Basic auth header

    Returns:
        Object with report ID for tracking

    Note: Limited to 20 requests per user
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    # Validate limits
    if len(dimensions) > 15:
        raise ValueError("Maximum 15 dimensions allowed")
    if len(metrics) > 8:
        raise ValueError("Maximum 8 metrics allowed")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/reporting/cost/enqueue"

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "dimensions": ",".join(dimensions),
        "metrics": ",".join(metrics)
    }

    # Add optional parameters
    if filters:
        for filter_expr in filters:
            params.setdefault("filters", []).append(filter_expr)
    if sort:
        params["sort"] = ",".join(sort)
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    if chart:
        params["chart"] = "1"
    if view_id is not None:
        params["view_id"] = view_id
    if apply_allocations is not None:
        params["applyAllocations"] = str(apply_allocations).lower()

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def get_report_state(
    report_id: str,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Check the processing state of an enqueued cost report.

    Args:
        report_id: ID returned from enqueue_cost_report
        authorization: Bearer token or Basic auth header

    Returns:
        Object with status: "enqueued", "running", "errored", or "finished"
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/reporting/reports/{report_id}/state"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_report_results(
    report_id: str,
    token: str | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Retrieve results from a finished enqueued cost report.

    Args:
        report_id: ID of the finished report
        token: Pagination token for large reports (30,000+ rows)
        authorization: Bearer token or Basic auth header

    Returns:
        Standard cost report object with results and metadata

    Note: Enqueued reports paginate at 30,000 rows instead of 10,000
    """
    if not authorization:
        raise ValueError("Authorization token is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/reporting/reports/{report_id}/results"

    params = {}
    if token:
        params["token"] = token

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

# ============================================================================
# COST REPORTS API (Legacy endpoints for backward compatibility)
# ============================================================================

def get_cost_reports_legacy(
    start_date: str,
    end_date: str,
    dimensions: List[str] | None = None,
    authorization: str | None = None
) -> Dict[str, Any]:
    """
    Legacy cost reports endpoint for backward compatibility.
    Note: This may not be the actual Cloudability API endpoint.
    """
    if not authorization:
        raise ValueError("Authorization token is required")
    
    headers = get_auth_headers(authorization)
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "dimensions": ','.join(dimensions) if dimensions else '',
    }
    
    url = f"{CLOUDABILITY_API_URL}/reports/cost/run"
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return {"results": response.json().get("results", [])}

def get_usage_data_legacy(period: str, authorization: str | None = None) -> Dict[str, Any]:
    """
    Legacy usage data endpoint for backward compatibility.
    Note: This may not be the actual Cloudability API endpoint.
    """
    if not authorization:
        raise ValueError("Authorization token is required")
    
    headers = get_auth_headers(authorization)
    params = {"period": period}
    
    url = f"{CLOUDABILITY_API_URL}/reports/usage/run"
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return {"usage_records": response.json().get("results", [])}
