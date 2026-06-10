"""
MCP reference resources for the Cloudability server.

Exposes stable discovery data (measures, filter operators, saved reports, config)
with short-lived in-memory caching to limit API churn.
"""

from __future__ import annotations

import os
import time
from typing import Any, cast
from collections.abc import Callable

from fastmcp import FastMCP

from cloudability_tools import (
    CLOUDABILITY_API_URL,
    CLOUDABILITY_FRONTDOOR_URL,
    _env_api_keys_configured,
    get_cost_filter_operators,
    get_cost_measures,
    list_cost_reports,
)

_RESOURCE_CACHE_TTL_SECONDS = int(
    os.getenv("CLOUDABILITY_RESOURCE_CACHE_TTL_SECONDS", "900")
)

_resource_cache: dict[str, tuple[float, Any]] = {}


def invalidate_resource_cache() -> None:
    """Clear cached reference resource payloads (for tests)."""
    _resource_cache.clear()


def _get_cached[T](cache_key: str, fetch: Callable[[], T]) -> T:
    now = time.time()
    entry = _resource_cache.get(cache_key)
    if entry is not None:
        expires_at, data = entry
        if now < expires_at:
            return cast(T, data)

    data = fetch()
    _resource_cache[cache_key] = (now + _RESOURCE_CACHE_TTL_SECONDS, data)
    return data


def get_server_config_resource() -> dict[str, Any]:
    """Non-secret server configuration for MCP clients."""
    if _env_api_keys_configured():
        auth_mode = "frontdoor_api_keys"
    elif os.getenv("CLOUDABILITY_ENVIRONMENT_ID"):
        auth_mode = "bearer_or_basic_explicit"
    else:
        auth_mode = "explicit_only"

    return {
        "api_url": CLOUDABILITY_API_URL,
        "frontdoor_url": CLOUDABILITY_FRONTDOOR_URL,
        "default_view_id": os.getenv("CLOUDABILITY_DEFAULT_VIEW_ID"),
        "environment_id_configured": bool(os.getenv("CLOUDABILITY_ENVIRONMENT_ID")),
        "frontdoor_api_keys_configured": _env_api_keys_configured(),
        "auth_mode": auth_mode,
        "resource_cache_ttl_seconds": _RESOURCE_CACHE_TTL_SECONDS,
        "resource_uris": [
            "cloudability://config",
            "cloudability://measures",
            "cloudability://measures/allocated",
            "cloudability://filter-operators",
            "cloudability://saved-reports",
        ],
    }


def get_measures_resource(
    *,
    apply_allocations: bool,
    authorization: str | None = None,
) -> dict[str, Any]:
    cache_key = f"measures:apply_allocations={apply_allocations}"

    def fetch() -> dict[str, Any]:
        measures = get_cost_measures(
            apply_allocations=True if apply_allocations else None,
            authorization=authorization,
        )
        return {"result": measures}

    if authorization is not None:
        return fetch()
    return _get_cached(cache_key, fetch)


def get_filter_operators_resource(
    authorization: str | None = None,
) -> dict[str, Any]:
    def fetch() -> dict[str, Any]:
        operators = get_cost_filter_operators(authorization=authorization)
        return {"result": operators}

    if authorization is not None:
        return fetch()
    return _get_cached("filter-operators", fetch)


def get_saved_reports_resource(authorization: str | None = None) -> dict[str, Any]:
    def fetch() -> dict[str, Any]:
        reports = list_cost_reports(authorization=authorization)
        return {"result": reports}

    if authorization is not None:
        return fetch()
    return _get_cached("saved-reports", fetch)


def register_resources(mcp: FastMCP) -> None:
    """Register Cloudability reference resources on the MCP server."""

    @mcp.resource(
        uri="cloudability://config",
        name="CloudabilityServerConfig",
        description=(
            "Non-secret Cloudability MCP server configuration: API region URL, "
            "default view ID, and authentication mode."
        ),
        mime_type="application/json",
        tags={"reference", "config"},
    )
    def resource_config() -> dict[str, Any]:
        return get_server_config_resource()

    @mcp.resource(
        uri="cloudability://measures",
        name="CostReportingMeasures",
        description=(
            "Catalog of cost reporting dimensions and metrics for building "
            "execute_cost_report queries."
        ),
        mime_type="application/json",
        tags={"reference", "cost-reporting"},
    )
    def resource_measures() -> dict[str, Any]:
        return get_measures_resource(apply_allocations=False)

    @mcp.resource(
        uri="cloudability://measures/allocated",
        name="CostReportingMeasuresAllocated",
        description=(
            "Cost reporting measures supported when apply_allocations is enabled "
            "on cost reports."
        ),
        mime_type="application/json",
        tags={"reference", "cost-reporting", "allocations"},
    )
    def resource_measures_allocated() -> dict[str, Any]:
        return get_measures_resource(apply_allocations=True)

    @mcp.resource(
        uri="cloudability://filter-operators",
        name="CostReportingFilterOperators",
        description=(
            "Filter operators for cost report filters (==, !=, >, =@, []=, etc.)."
        ),
        mime_type="application/json",
        tags={"reference", "cost-reporting"},
    )
    def resource_filter_operators() -> dict[str, Any]:
        return get_filter_operators_resource()

    @mcp.resource(
        uri="cloudability://saved-reports",
        name="SavedCostReports",
        description=(
            "Saved cost report definitions owned by or shared with the user, "
            "including dimensions, metrics, and filters."
        ),
        mime_type="application/json",
        tags={"reference", "cost-reporting"},
    )
    def resource_saved_reports() -> dict[str, Any]:
        return get_saved_reports_resource()
