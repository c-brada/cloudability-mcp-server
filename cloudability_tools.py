"""
Cloudability API tools for MCP server.
Comprehensive implementation of Cloudability API v3 endpoints.
"""

import contextlib
import os
import ssl
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, cast

import requests
import truststore
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter

load_dotenv()

# Refresh slightly before expiry so in-flight requests do not use a dying token.
_OPENTOKEN_REFRESH_SKEW_SECONDS = 60
_DEFAULT_OPENTOKEN_TTL_SECONDS = int(
    os.getenv("CLOUDABILITY_OPENTOKEN_TTL_SECONDS", "3600")
)


class _TruststoreHTTPAdapter(HTTPAdapter):
    """Use the OS certificate store (e.g. corporate CAs) for HTTPS requests."""

    def init_poolmanager(
        self,
        connections: int,
        maxsize: int,
        block: bool = False,
        **pool_kwargs: Any,
    ) -> Any:
        ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return super().init_poolmanager(
            connections, maxsize, block, ssl_context=ctx, **pool_kwargs
        )


@dataclass(frozen=True)
class _OpentokenCacheEntry:
    token: str
    expires_at: float  # Unix timestamp (seconds)


_cached_opentoken: _OpentokenCacheEntry | None = None


def invalidate_opentoken_cache() -> None:
    """Clear the cached Frontdoor apptio-opentoken (used by tests and 401 retry)."""
    global _cached_opentoken
    _cached_opentoken = None


def _env_api_keys_configured() -> bool:
    return bool(
        os.getenv("CLOUDABILITY_KEY_ACCESS") and os.getenv("CLOUDABILITY_KEY_SECRET")
    )


def _expires_from_response(response: requests.Response) -> float:
    """Derive token expiry from cookies, headers, or configured default TTL."""
    for cookie in response.cookies:
        if cookie.name == "apptio-opentoken" and cookie.expires is not None:
            return float(cookie.expires)

    for header_name in (
        "apptio-opentoken-expires",
        "apptio-token-expires",
        "x-apptio-opentoken-expires",
    ):
        header_value = response.headers.get(header_name)
        if not header_value:
            continue
        try:
            return float(header_value)
        except ValueError:
            try:
                return parsedate_to_datetime(header_value).timestamp()
            except (TypeError, ValueError, OverflowError):
                continue

    return time.time() + _DEFAULT_OPENTOKEN_TTL_SECONDS


def _is_cache_valid(entry: _OpentokenCacheEntry) -> bool:
    return time.time() < (entry.expires_at - _OPENTOKEN_REFRESH_SKEW_SECONDS)


def _is_frontdoor_url(url: str) -> bool:
    return url.startswith(CLOUDABILITY_FRONTDOOR_URL.rstrip("/"))


def _should_retry_cloudability_auth(
    url: str, headers: dict[str, str] | None, status_code: int
) -> bool:
    if status_code != 401:
        return False
    if _is_frontdoor_url(url):
        return False
    if not _env_api_keys_configured():
        return False
    return bool(headers and "apptio-opentoken" in headers)


class _CloudabilitySession(requests.Session):
    """HTTP session that refreshes env-sourced opentokens after 401 responses."""

    def request(  # type: ignore[override]
        self, method: str, url: str, **kwargs: Any
    ) -> requests.Response:
        response = super().request(method, url, **kwargs)
        headers = kwargs.get("headers")
        if not _should_retry_cloudability_auth(url, headers, response.status_code):
            return response

        invalidate_opentoken_cache()
        new_authorization = resolve_authorization(None)
        merged_headers = dict(headers or {})
        merged_headers.update(get_auth_headers(new_authorization))
        kwargs["headers"] = merged_headers
        return super().request(method, url, **kwargs)


_http_session = _CloudabilitySession()
_http_session.mount("https://", _TruststoreHTTPAdapter())

CLOUDABILITY_API_URL = os.getenv("CLOUDABILITY_API_URL", "https://api.cloudability.com/v3")
CLOUDABILITY_FRONTDOOR_URL = os.getenv(
    "CLOUDABILITY_FRONTDOOR_URL",
    "https://frontdoor.apptio.com/service/apikeylogin",
)


def _response_json(response: requests.Response) -> dict[str, Any]:
    return cast(dict[str, Any], response.json())


def _raise_for_status_with_body(response: requests.Response) -> None:
    """Raise HTTPError including the API response body when available."""
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text.strip()
        if detail:
            with contextlib.suppress(ValueError):
                detail = str(response.json())
            raise requests.HTTPError(
                f"{exc}; response body: {detail}",
                response=response,
            ) from exc
        raise


def _validate_containers_report_filters(filters: list[str] | None) -> None:
    if not filters:
        return
    for filter_expr in filters:
        if filter_expr.startswith("clusterName=="):
            raise ValueError(
                f'Invalid filter "{filter_expr}": cluster filters must use '
                "cluster==<uuid> from list_clusters, not clusterName. "
                "Example: cluster==0db407e4-e9e4-4fd1-bd2b-dea2c3585706"
            )


def _remap_containers_report_kpi(
    widget_type: str,
    group: list[str] | None,
    filters: list[str] | None,
) -> tuple[str, list[str] | None, bool]:
    """Translate kpi to top because the Cloudability API returns HTTP 400 for kpi."""
    if widget_type != "kpi":
        return widget_type, group, False

    remapped_group = group
    if not group and filters and any(
        filter_expr.startswith("cluster==") for filter_expr in filters
    ):
        remapped_group = ["cluster"]
    return "top", remapped_group, True


def fetch_apptio_opentoken(force_refresh: bool = False) -> str:
    """Exchange Frontdoor API keys for an apptio-opentoken."""
    global _cached_opentoken

    if (
        not force_refresh
        and _cached_opentoken is not None
        and _is_cache_valid(_cached_opentoken)
    ):
        return _cached_opentoken.token

    key_access = os.getenv("CLOUDABILITY_KEY_ACCESS")
    key_secret = os.getenv("CLOUDABILITY_KEY_SECRET")
    if not key_access or not key_secret:
        raise ValueError(
            "CLOUDABILITY_KEY_ACCESS and CLOUDABILITY_KEY_SECRET are required "
            "to obtain an apptio-opentoken"
        )

    response = _http_session.post(
        CLOUDABILITY_FRONTDOOR_URL,
        json={"keyAccess": key_access, "keySecret": key_secret},
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()

    token = response.headers.get("apptio-opentoken")
    if not token:
        token = response.cookies.get("apptio-opentoken")
    if not token:
        try:
            body = response.json()
            token = body.get("token") or body.get("apptio-opentoken")
        except ValueError:
            pass

    if not token:
        raise ValueError("Failed to obtain apptio-opentoken from Frontdoor login")

    _cached_opentoken = _OpentokenCacheEntry(
        token=token,
        expires_at=_expires_from_response(response),
    )
    return token


def resolve_authorization(authorization: str | None) -> str:
    """Resolve authorization from an explicit value or env-based API keys."""
    if authorization:
        return authorization

    key_access = os.getenv("CLOUDABILITY_KEY_ACCESS")
    key_secret = os.getenv("CLOUDABILITY_KEY_SECRET")
    if key_access and key_secret:
        return f"Bearer {fetch_apptio_opentoken()}"

    raise ValueError(
        "Authorization token is required. Provide authorization or set "
        "CLOUDABILITY_KEY_ACCESS and CLOUDABILITY_KEY_SECRET environment variables."
    )


def get_auth_headers(authorization: str) -> dict[str, str]:
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
            "Accept": "application/json",
        }
    else:
        # Basic Auth with API key
        return {
            "Authorization": authorization,
            "Accept": "application/json",
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
) -> dict[str, Any]:
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
    authorization = resolve_authorization(authorization)

    if not kubernetes_version and not cluster_version:
        raise ValueError("Either kubernetes_version or cluster_version is required")

    if kubernetes_version and cluster_version:
        raise ValueError("Provide either kubernetes_version OR cluster_version, not both")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/provisioning"

    data: dict[str, Any] = {"clusterName": cluster_name}
    if kubernetes_version:
        data["kubernetesVersion"] = kubernetes_version
    if cluster_version:
        data["clusterVersion"] = cluster_version

    response = _http_session.post(url, json=data, headers=headers)
    response.raise_for_status()
    return _response_json(response)

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
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/provisioning/{cluster_id}/config"

    response = _http_session.get(url, headers=headers)
    response.raise_for_status()
    return response.text

def list_provisioned_clusters(
    view_id: str | None = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """
    Get list of all provisioned clusters.

    Args:
        view_id: Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted)
        authorization: Bearer token or Basic auth header

    Returns:
        List of provisioned clusters with their configurations
    """
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/provisioning"
    params: dict[str, Any] = {}
    _apply_view_id_param(params, view_id)

    response = _http_session.get(url, headers=headers, params=params or None)
    response.raise_for_status()
    return _response_json(response)

def update_provisioned_cluster(
    cluster_id: str,
    kubernetes_version: str | None = None,
    cluster_version: str | None = None,
    authorization: str | None = None
) -> dict[str, Any]:
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
    authorization = resolve_authorization(authorization)

    if not kubernetes_version and not cluster_version:
        raise ValueError("Either kubernetes_version or cluster_version is required")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/provisioning/{cluster_id}"

    data: dict[str, Any] = {}
    if kubernetes_version:
        data["kubernetesVersion"] = kubernetes_version
    if cluster_version:
        data["clusterVersion"] = cluster_version

    response = _http_session.put(url, json=data, headers=headers)
    response.raise_for_status()
    return _response_json(response)

# Enhanced Clusters API (v2)
def _resolve_view_id(view_id: str | None) -> str:
    if view_id is not None:
        return view_id
    default = os.getenv("CLOUDABILITY_DEFAULT_VIEW_ID")
    if default:
        return default
    raise ValueError(
        "view_id is required. Pass view_id or set CLOUDABILITY_DEFAULT_VIEW_ID."
    )


def _resolve_estimate_view_id(view_id: str | None) -> str:
    """Resolve viewId for /estimate and /forecast.

    When view_id is omitted, uses CLOUDABILITY_DEFAULT_VIEW_ID if set;
    otherwise falls back to \"0\" (all org cost data). Pass view_id=\"0\"
    explicitly to request org-wide data when a default view is configured.
    """
    if view_id is not None:
        return view_id
    default = os.getenv("CLOUDABILITY_DEFAULT_VIEW_ID")
    if default:
        return default
    return "0"


def _apply_view_id_param(params: dict[str, Any], view_id: str | None) -> None:
    """Attach viewId to container API query params when a view is known."""
    resolved = view_id if view_id is not None else os.getenv("CLOUDABILITY_DEFAULT_VIEW_ID")
    if resolved:
        params["viewId"] = resolved


def get_container_clusters(
    start_date: str,
    end_date: str,
    view_id: str | None = None,
    concise: bool = False,
    authorization: str | None = None,
) -> dict[str, Any]:
    """
    Get detailed information about clusters and their nodes.

    Args:
        start_date: Start date for cluster data window (YYYY-MM-DD)
        end_date: End date for cluster data window (YYYY-MM-DD)
        view_id: Cloudability view ID (required unless CLOUDABILITY_DEFAULT_VIEW_ID is set)
        concise: When True, omit per-node details from the response
        authorization: Bearer token or Basic auth header

    Returns:
        Detailed cluster information with nodes, timestamps, and metadata
    """
    return get_clusters(
        start_date=start_date,
        end_date=end_date,
        view_id=view_id,
        concise=concise,
        authorization=authorization,
    )


def get_clusters(
    start_date: str,
    end_date: str,
    view_id: str | None = None,
    concise: bool = True,
    authorization: str | None = None,
) -> dict[str, Any]:
    """Get Kubernetes clusters from the Cloudability containers v2 API."""
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/v2/clusters"

    params: dict[str, Any] = {
        "start": start_date,
        "end": end_date,
        "viewId": _resolve_view_id(view_id),
        "concise": str(concise).lower(),
    }

    response = _http_session.get(url, headers=headers, params=params)
    response.raise_for_status()
    return _response_json(response)


def get_containers_report(
    start_date: str,
    end_date: str,
    cost_type: str = "adjusted",
    metrics: list[str] | None = None,
    group: list[str] | None = None,
    count: list[str] | None = None,
    filters: list[str] | None = None,
    widget_type: str = "top",
    limit: int = 50,
    sort: list[dict[str, str]] | None = None,
    view_id: str | None = None,
    pagination_token: str | None = None,
    authorization: str | None = None
) -> dict[str, Any]:
    """
    Get containers cost and usage report from Cloudability.

    view_id is required unless CLOUDABILITY_DEFAULT_VIEW_ID is set.

    total_cost is fairshare-allocated workload cost, not billing/invoiced cost.
    Use run_cost_report (execute_cost_report) for unblended_cost, idle overhead,
    and amortized billing metrics.

    widget_type kpi is remapped to top because the API returns HTTP 400 for kpi.
    """
    authorization = resolve_authorization(authorization)

    _validate_containers_report_filters(filters)
    widget_type, group, kpi_remapped = _remap_containers_report_kpi(
        widget_type, group, filters
    )

    headers = get_auth_headers(authorization)

    if metrics is None:
        metrics = ["total_cost", "total_cost_efficiency"]

    request_body: dict[str, Any] = {
        "start": start_date,
        "end": end_date,
        "costType": cost_type,
        "metrics": metrics,
        "widgetType": widget_type,
        "limit": limit,
    }

    if group:
        request_body["group"] = group
    if count:
        request_body["count"] = count
    if filters:
        request_body["filters"] = filters
    if sort:
        request_body["sort"] = sort
    if pagination_token:
        request_body["paginationToken"] = pagination_token

    url = f"{CLOUDABILITY_API_URL}/containers/report"
    params = {"viewId": _resolve_view_id(view_id)}

    response = _http_session.post(url, json=request_body, headers=headers, params=params)
    _raise_for_status_with_body(response)
    result = _response_json(response)
    if kpi_remapped:
        result["_kpi_remapped_to_top"] = True
    return result

# Container Usage API
def get_container_usage(
    start_date: str,
    end_date: str,
    metrics: list[str] | None = None,
    filters: list[str] | None = None,
    view_id: str | None = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """
    Get daily resource usage data for containers.

    Reports resource allocation percentages and average values by day
    over the specified time range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        metrics: Metrics to report (e.g., ["cpu/reserved", "filesystem/usage"])
        filters: Filter expressions to scope the data
        view_id: Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted)
        authorization: Bearer token or Basic auth header

    Returns:
        Daily usage data with allocation percentages and resource values
    """
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/usage"

    params: dict[str, Any] = {
        "start": start_date,
        "end": end_date,
    }
    _apply_view_id_param(params, view_id)

    if metrics:
        params["metrics"] = ",".join(metrics)
    if filters:
        for filter_expr in filters:
            params.setdefault("filters", []).append(filter_expr)

    response = _http_session.get(url, headers=headers, params=params)
    response.raise_for_status()
    return _response_json(response)

# Container Labels API
def get_container_labels(
    start_date: str,
    end_date: str,
    filters: list[str] | None = None,
    view_id: str | None = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """
    Get list of Kubernetes label keys observed in the specified timeframe.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        filters: Filter expressions to scope the data
        view_id: Cloudability view ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted)
        authorization: Bearer token or Basic auth header

    Returns:
        List of label keys with their display names
    """
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/containers/labels"

    params: dict[str, Any] = {
        "start": start_date,
        "end": end_date,
    }
    _apply_view_id_param(params, view_id)

    if filters:
        for filter_expr in filters:
            params.setdefault("filters", []).append(filter_expr)

    response = _http_session.get(url, headers=headers, params=params)
    response.raise_for_status()
    return _response_json(response)

# ============================================================================
# BUDGETS API
# ============================================================================

def get_budgets(authorization: str | None = None) -> dict[str, Any]:
    """Get list of all budgets."""
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/budgets"

    response = _http_session.get(url, headers=headers)
    response.raise_for_status()
    return _response_json(response)

def get_budget_details(budget_id: str, authorization: str | None = None) -> dict[str, Any]:
    """Get details for a specific budget."""
    authorization = resolve_authorization(authorization)
    
    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/budgets/{budget_id}"
    
    response = _http_session.get(url, headers=headers)
    response.raise_for_status()
    return _response_json(response)

# ============================================================================
# VENDOR ACCOUNTS API
# ============================================================================

# Cloudability uses mixed casing in vendor path segments (e.g. AWS vs azure).
_VENDOR_ACCOUNT_SEGMENTS: dict[str, str] = {
    "aws": "AWS",
    "azure": "azure",
    "gcp": "gcp",
    "ibm": "ibm",
    "oci": "oci",
}


def get_vendor_accounts(
    vendor: str,
    view_id: str | None = None,
    authorization: str | None = None,
) -> dict[str, Any]:
    """
    Get list of cloud vendor credential accounts from Cloudability.

    Args:
        vendor: Vendor key (aws, azure, gcp, ibm, oci)
        view_id: Cloudability view ID (defaults to \"0\" for all org accounts)
        authorization: Bearer token or Basic auth header

    Returns:
        Cloudability v3 envelope with vendor credential accounts under ``result``
    """
    authorization = resolve_authorization(authorization)

    segment = _VENDOR_ACCOUNT_SEGMENTS.get(vendor.lower())
    if not segment:
        supported = ", ".join(sorted(_VENDOR_ACCOUNT_SEGMENTS))
        raise ValueError(f"Unsupported vendor {vendor!r}. Supported: {supported}")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/vendors/{segment}/accounts"
    params: dict[str, Any] = {"viewId": view_id if view_id is not None else "0"}

    response = _http_session.get(url, headers=headers, params=params)
    response.raise_for_status()
    return _response_json(response)

# ============================================================================
# BUDGETS & FORECASTING API
# ============================================================================

def get_estimate(
    view_id: str | None = None,
    basis: str = "cash",
    authorization: str | None = None
) -> dict[str, Any]:
    """
    Generate a spending estimate for the current month.

    Args:
        view_id: View ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted; \"0\" = all cost data)
        basis: Cost basis - "cash", "amortized", "adjusted", "adjustedAmortized", "list"
        authorization: Bearer token or Basic auth header

    Returns:
        Cloudability v3 envelope ``{"result": {...}}`` where ``result`` contains
        ``estimatedSpend``, ``previousMonthSpend``, ``cumulativeMtdSpend``, and
        ``details`` (service-level spending drivers).
    """
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    params: dict[str, Any] = {
        "viewId": _resolve_estimate_view_id(view_id),
        "basis": basis
    }

    url = f"{CLOUDABILITY_API_URL}/estimate"
    response = _http_session.get(url, headers=headers, params=params)
    response.raise_for_status()
    return _response_json(response)

def get_forecast(
    view_id: str | None = None,
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

    Args:
        view_id: View ID (uses CLOUDABILITY_DEFAULT_VIEW_ID if omitted; \"0\" = all cost data)
        basis: Cost basis - "cash", "amortized", "adjusted", "adjustedAmortized", "list"
        months_back: Months of history to use (3-24)
        months_forward: Months to forecast (1-24)
        use_current_estimate: Include current month estimate in model
        remove_credits: Remove credits from spending model
        remove_one_time_charges: Remove one-time charges from model
        authorization: Bearer token or Basic auth header

    Returns:
        Cloudability v3 envelope ``{"result": {...}}`` with forecast, actual,
        and detail arrays nested under ``result``.
    """
    authorization = resolve_authorization(authorization)

    # Validate parameters
    if not (3 <= months_back <= 24):
        raise ValueError("months_back must be between 3 and 24")
    if not (1 <= months_forward <= 24):
        raise ValueError("months_forward must be between 1 and 24")

    headers = get_auth_headers(authorization)
    params: dict[str, Any] = {
        "viewId": _resolve_estimate_view_id(view_id),
        "basis": basis,
        "monthsBack": months_back,
        "monthsForward": months_forward,
        "useCurrentEstimate": use_current_estimate,
        "removeCredits": remove_credits,
        "removeOneTimeCharges": remove_one_time_charges
    }

    url = f"{CLOUDABILITY_API_URL}/forecast"
    response = _http_session.get(url, headers=headers, params=params)
    response.raise_for_status()
    return _response_json(response)

def create_budget(
    name: str,
    basis: str,
    view_id: str = "0",
    months: list[dict[str, Any]] | None = None,
    authorization: str | None = None
) -> dict[str, Any]:
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
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)

    budget_data: dict[str, Any] = {
        "name": name,
        "basis": basis,
        "viewId": view_id,
        "months": months or []
    }

    url = f"{CLOUDABILITY_API_URL}/budgets"
    response = _http_session.post(url, json=budget_data, headers=headers)
    response.raise_for_status()
    return _response_json(response)

def update_budget(
    budget_id: str,
    name: str | None = None,
    basis: str | None = None,
    view_id: str | None = None,
    months: list[dict[str, Any]] | None = None,
    authorization: str | None = None
) -> dict[str, Any]:
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
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)

    # Build update data with only provided fields
    budget_data: dict[str, Any] = {}
    if name is not None:
        budget_data["name"] = name
    if basis is not None:
        budget_data["basis"] = basis
    if view_id is not None:
        budget_data["viewId"] = view_id
    if months is not None:
        budget_data["months"] = months

    url = f"{CLOUDABILITY_API_URL}/budgets/{budget_id}"
    response = _http_session.put(url, json=budget_data, headers=headers)
    response.raise_for_status()
    return _response_json(response)

def delete_budget(budget_id: str, authorization: str | None = None) -> bool:
    """
    Delete a budget.

    Args:
        budget_id: UUID of the budget to delete
        authorization: Bearer token or Basic auth header

    Returns:
        True if deletion was successful
    """
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/budgets/{budget_id}"

    response = _http_session.delete(url, headers=headers)
    response.raise_for_status()
    return True

def create_budget_subscription(
    budget_id: str,
    notify_exceeded: bool = False,
    notify_expected: bool = False,
    authorization: str | None = None
) -> dict[str, Any]:
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
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)

    subscription_data: dict[str, Any] = {
        "budgetId": budget_id,
        "notifyExceeded": notify_exceeded,
        "notifyExpected": notify_expected
    }

    url = f"{CLOUDABILITY_API_URL}/budget-subscriptions"
    response = _http_session.post(url, json=subscription_data, headers=headers)
    response.raise_for_status()
    return _response_json(response)

def get_budget_subscription(
    subscription_id: str,
    authorization: str | None = None
) -> dict[str, Any]:
    """
    Get a specific budget subscription.

    Args:
        subscription_id: UUID of the subscription
        authorization: Bearer token or Basic auth header

    Returns:
        Budget subscription object
    """
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/budget-subscriptions/{subscription_id}"

    response = _http_session.get(url, headers=headers)
    response.raise_for_status()
    return _response_json(response)

def list_budget_subscriptions(authorization: str | None = None) -> dict[str, Any]:
    """
    Get list of all budget subscriptions.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of budget subscription objects
    """
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/budget-subscriptions"

    response = _http_session.get(url, headers=headers)
    response.raise_for_status()
    return _response_json(response)

def update_budget_subscription(
    subscription_id: str,
    budget_id: str | None = None,
    notify_exceeded: bool | None = None,
    notify_expected: bool | None = None,
    authorization: str | None = None
) -> dict[str, Any]:
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
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)

    # Build update data with only provided fields
    subscription_data: dict[str, Any] = {}
    if budget_id is not None:
        subscription_data["budgetId"] = budget_id
    if notify_exceeded is not None:
        subscription_data["notifyExceeded"] = notify_exceeded
    if notify_expected is not None:
        subscription_data["notifyExpected"] = notify_expected

    url = f"{CLOUDABILITY_API_URL}/budget-subscriptions/{subscription_id}"
    response = _http_session.put(url, json=subscription_data, headers=headers)
    response.raise_for_status()
    return _response_json(response)

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
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/budget-subscriptions/{subscription_id}"

    response = _http_session.delete(url, headers=headers)
    response.raise_for_status()
    return True

# ============================================================================
# COST REPORTING API
# ============================================================================

def list_cost_reports(authorization: str | None = None) -> dict[str, Any]:
    """
    Get list of saved cost reports owned by or shared with the user/org.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of cost report objects with metadata and configurations
    """
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/reporting/reports/cost"

    response = _http_session.get(url, headers=headers)
    response.raise_for_status()
    return _response_json(response)

def get_cost_measures(
    apply_allocations: bool | None = None,
    authorization: str | None = None
) -> dict[str, Any]:
    """
    Get list of available cost reporting measures (dimensions and metrics).

    Args:
        apply_allocations: If true, only measures supported by cost sharing are listed
        authorization: Bearer token or Basic auth header

    Returns:
        List of available measures with metadata (dimensions and metrics)
    """
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/reporting/cost/measures"

    params: dict[str, Any] = {}
    if apply_allocations is not None:
        params["apply_allocations"] = str(apply_allocations).lower()

    response = _http_session.get(url, headers=headers, params=params)
    response.raise_for_status()
    return _response_json(response)

def get_cost_filter_operators(authorization: str | None = None) -> dict[str, Any]:
    """
    Get list of available filter operators for cost reporting.

    Args:
        authorization: Bearer token or Basic auth header

    Returns:
        List of filter operators (==, !=, >, <, =@, etc.)
    """
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/reporting/cost/filters"

    response = _http_session.get(url, headers=headers)
    response.raise_for_status()
    return _response_json(response)

def _apply_sort(params: dict[str, Any], sort: list[str] | None) -> None:
    """Map a sort expression to the params Cloudability actually accepts.

    The /reporting/cost/run endpoint expects ``sort_by=<field>`` plus an
    optional ``order=asc|desc``. Sending ``sort=<field>`` returns
    HTTP 422 "Invalid sort direction". Accept the documented
    ``"<field>ASC"`` / ``"<field>DESC"`` expression form (or a bare field
    name) and split it; order defaults to ``desc``.
    """
    if not sort:
        return
    expr = sort[0].strip()
    order = "desc"
    upper = expr.upper()
    if upper.endswith("ASC"):
        expr, order = expr[:-3], "asc"
    elif upper.endswith("DESC"):
        expr, order = expr[:-4], "desc"
    params["sort_by"] = expr
    params["order"] = order


def run_cost_report(
    start_date: str,
    end_date: str,
    dimensions: list[str],
    metrics: list[str],
    filters: list[str] | None = None,
    sort: list[str] | None = None,
    limit: int | None = None,
    offset: int | None = None,
    chart: bool = False,
    view_id: str | None = None,
    apply_allocations: bool | None = None,
    token: str | None = None,
    authorization: str | None = None
) -> dict[str, Any]:
    """
    Execute a cost report with flexible filtering, sorting, and pagination.

    Args:
        start_date: Start date (YYYY-MM-DD or relative date like "beginning of last month")
        end_date: End date (YYYY-MM-DD or relative date like "end of last month")
        dimensions: List of dimensions (max 15, e.g., ["vendor", "region"])
        metrics: List of metrics (max 8, e.g., ["total_amortized_cost", "usage_hours"])
        filters: List of filter expressions (e.g., ["transaction_type==usage"])
        sort: Sort expression as ["<field>"] or ["<field>ASC"]/["<field>DESC"]
            (order defaults to desc), e.g. ["total_amortized_costDESC"].
            Sent to the API as sort_by + order.
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
    authorization = resolve_authorization(authorization)

    # Validate limits
    if len(dimensions) > 15:
        raise ValueError("Maximum 15 dimensions allowed")
    if len(metrics) > 8:
        raise ValueError("Maximum 8 metrics allowed")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/reporting/cost/run"

    params: dict[str, Any] = {
        "start_date": start_date,
        "end_date": end_date,
        "dimensions": ",".join(dimensions),
        "metrics": ",".join(metrics)
    }

    # Add optional parameters
    if filters:
        for filter_expr in filters:
            params.setdefault("filters", []).append(filter_expr)
    _apply_sort(params, sort)
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

    response = _http_session.get(url, headers=headers, params=params)
    response.raise_for_status()
    return _response_json(response)

def enqueue_cost_report(
    start_date: str,
    end_date: str,
    dimensions: list[str],
    metrics: list[str],
    filters: list[str] | None = None,
    sort: list[str] | None = None,
    limit: int | None = None,
    offset: int | None = None,
    chart: bool = False,
    view_id: str | None = None,
    apply_allocations: bool | None = None,
    authorization: str | None = None
) -> dict[str, Any]:
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
        sort: Sort expression as ["<field>"] or ["<field>ASC"]/["<field>DESC"]
            (order defaults to desc); sent to the API as sort_by + order
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
    authorization = resolve_authorization(authorization)

    # Validate limits
    if len(dimensions) > 15:
        raise ValueError("Maximum 15 dimensions allowed")
    if len(metrics) > 8:
        raise ValueError("Maximum 8 metrics allowed")

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/reporting/cost/enqueue"

    params: dict[str, Any] = {
        "start_date": start_date,
        "end_date": end_date,
        "dimensions": ",".join(dimensions),
        "metrics": ",".join(metrics)
    }

    # Add optional parameters
    if filters:
        for filter_expr in filters:
            params.setdefault("filters", []).append(filter_expr)
    _apply_sort(params, sort)
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

    response = _http_session.get(url, headers=headers, params=params)
    response.raise_for_status()
    return _response_json(response)

def get_report_state(
    report_id: str,
    authorization: str | None = None
) -> dict[str, Any]:
    """
    Check the processing state of an enqueued cost report.

    Args:
        report_id: ID returned from enqueue_cost_report
        authorization: Bearer token or Basic auth header

    Returns:
        Object with status: "enqueued", "running", "errored", or "finished"
    """
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/reporting/reports/{report_id}/state"

    response = _http_session.get(url, headers=headers)
    response.raise_for_status()
    return _response_json(response)

def get_report_results(
    report_id: str,
    token: str | None = None,
    authorization: str | None = None
) -> dict[str, Any]:
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
    authorization = resolve_authorization(authorization)

    headers = get_auth_headers(authorization)
    url = f"{CLOUDABILITY_API_URL}/reporting/reports/{report_id}/results"

    params: dict[str, Any] = {}
    if token:
        params["token"] = token

    response = _http_session.get(url, headers=headers, params=params)
    response.raise_for_status()
    return _response_json(response)
