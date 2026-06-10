"""
Live integration tests for the Cloudability MCP server.

Uses FastMCP's in-memory transport (real MCP protocol, no subprocess) while
calling the real Cloudability API when credentials are configured.

Run unit tests only (default):
    uv run pytest tests/ -v -m "not integration"

Run live integration tests:
    cp .env.example .env   # then fill in credentials
    uv run pytest tests/test_mcp_integration.py -v -m integration
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest
from fastmcp.exceptions import ToolError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cloudability_tools
from fastmcp import Client
from main import mcp

from tests.conftest import requires_live_cloudability

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_CONTAINER_START = "2026-04-01"
_CONTAINER_END = "2026-04-30"

# Read-only tools expected to work for most authenticated tenants.
CORE_READ_ONLY_LIVE_TOOLS: list[tuple[str, dict[str, Any], str]] = [
    ("list_budgets", {}, "result_dict"),
    ("list_saved_cost_reports", {}, "saved_reports"),
    ("list_budget_alerts", {}, "result_dict"),
    ("get_available_measures", {}, "wrapped_list"),
    ("get_filter_operators", {}, "wrapped_list"),
    ("get_spending_estimate", {"basis": "cash"}, "result_dict"),
    ("get_spending_forecast", {"basis": "cash", "months_back": 3, "months_forward": 1}, "result_dict"),
    (
        "execute_cost_report",
        {
            "start_date": "beginning of last month",
            "end_date": "end of last month",
            "dimensions": ["vendor"],
            "metrics": ["total_amortized_cost"],
            "limit": 10,
        },
        "cost_report",
    ),
    (
        "list_clusters",
        {"start_date": _CONTAINER_START, "end_date": _CONTAINER_END},
        "result_dict",
    ),
    (
        "get_detailed_cluster_info",
        {"start_date": _CONTAINER_START, "end_date": _CONTAINER_END},
        "result_dict",
    ),
    (
        "containers_report",
        {
            "start_date": _CONTAINER_START,
            "end_date": _CONTAINER_END,
            "metrics": ["total_cost"],
            "group": ["cluster"],
            "limit": 5,
        },
        "result_dict",
    ),
    (
        "discover_container_labels",
        {"start_date": _CONTAINER_START, "end_date": _CONTAINER_END},
        "result_dict",
    ),
]

# May 404/401/403/422 depending on tenant features and permissions; skipped on those codes.
OPTIONAL_READ_ONLY_LIVE_TOOLS: list[tuple[str, dict[str, Any], str]] = [
    ("list_aws_accounts", {}, "result_dict"),
    ("list_azure_accounts", {}, "result_dict"),
    ("list_all_provisioned_clusters", {}, "result_dict"),
    (
        "get_container_resource_usage",
        {
            "start_date": _CONTAINER_START,
            "end_date": _CONTAINER_END,
            "metrics": ["cpu/reserved"],
        },
        "result_dict",
    ),
]

TOOLS_REQUIRING_VIEW_ID = frozenset(
    {
        "list_clusters",
        "get_detailed_cluster_info",
        "containers_report",
        "get_spending_estimate",
        "get_spending_forecast",
        "list_all_provisioned_clusters",
        "get_container_resource_usage",
    }
)

EXPECTED_READ_ONLY_TOOLS = {
    name for name, _, _ in CORE_READ_ONLY_LIVE_TOOLS + OPTIONAL_READ_ONLY_LIVE_TOOLS
}

EXPECTED_REFERENCE_RESOURCE_URIS = frozenset(
    {
        "cloudability://config",
        "cloudability://measures",
        "cloudability://measures/allocated",
        "cloudability://filter-operators",
        "cloudability://saved-reports",
    }
)

_SKIP_OPTIONAL_HTTP_CODES = ("401", "403", "404", "422")


@pytest.fixture
def reset_opentoken_cache() -> None:
    """Avoid reusing a token obtained under different credentials."""
    cloudability_tools.invalidate_opentoken_cache()
    yield
    cloudability_tools.invalidate_opentoken_cache()


def _tool_payload(result) -> object:
    assert not result.is_error, getattr(result, "content", result)
    return result.data


def _assert_payload_shape(payload: object, shape: str) -> None:
    if shape == "result_dict":
        assert isinstance(payload, dict)
        assert "result" in payload
    elif shape == "wrapped_list":
        assert isinstance(payload, dict)
        assert isinstance(payload["result"], list)
        assert len(payload["result"]) > 0
    elif shape == "saved_reports":
        assert isinstance(payload, dict)
        reports = payload["result"]
        assert isinstance(reports, list)
        if reports:
            assert "id" in reports[0]
            assert "title" in reports[0]
    elif shape == "cost_report":
        assert isinstance(payload, dict)
        assert "results" in payload
        assert isinstance(payload["results"], list)
    else:
        raise AssertionError(f"Unknown payload shape: {shape}")


def _resolve_tool_args(tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
    args = dict(tool_args)
    if tool_name in TOOLS_REQUIRING_VIEW_ID:
        view_id = os.getenv("CLOUDABILITY_DEFAULT_VIEW_ID")
        if not view_id:
            pytest.skip(f"{tool_name} requires CLOUDABILITY_DEFAULT_VIEW_ID")
        args.setdefault("view_id", view_id)
    return args


async def _call_and_assert(
    tool_name: str,
    tool_args: dict[str, Any],
    payload_shape: str,
    *,
    allow_optional_skip: bool,
) -> None:
    args = _resolve_tool_args(tool_name, tool_args)
    try:
        async with Client(mcp) as client:
            result = await client.call_tool(tool_name, args)
        _assert_payload_shape(_tool_payload(result), payload_shape)
    except ToolError as exc:
        if allow_optional_skip and any(code in str(exc) for code in _SKIP_OPTIONAL_HTTP_CODES):
            pytest.skip(str(exc))
        raise


async def test_mcp_server_registers_expected_tools() -> None:
    """Verify the MCP server exposes the core tool surface (no network)."""
    async with Client(mcp) as client:
        tools = await client.list_tools()

    names = {tool.name for tool in tools}
    assert len(names) >= 28
    assert EXPECTED_READ_ONLY_TOOLS.issubset(names)


async def test_mcp_server_registers_reference_resources() -> None:
    """Verify reference resources are exposed (no network)."""
    async with Client(mcp) as client:
        resources = await client.list_resources()

    uris = {str(resource.uri) for resource in resources}
    assert uris == set(EXPECTED_REFERENCE_RESOURCE_URIS)


@requires_live_cloudability
@pytest.mark.parametrize(
    "uri",
    sorted(EXPECTED_REFERENCE_RESOURCE_URIS - {"cloudability://config"}),
)
async def test_read_reference_resource_via_mcp_live_api(
    uri: str,
    reset_opentoken_cache,
) -> None:
    """Read reference resources against the live Cloudability API."""
    async with Client(mcp) as client:
        contents = await client.read_resource(uri)

    assert contents
    text = contents[0].text
    assert text
    if uri != "cloudability://config":
        import json

        payload = json.loads(text)
        assert "result" in payload


@requires_live_cloudability
@pytest.mark.parametrize(
    ("tool_name", "tool_args", "payload_shape"),
    CORE_READ_ONLY_LIVE_TOOLS,
)
async def test_read_only_tool_via_mcp_live_api(
    tool_name: str,
    tool_args: dict[str, Any],
    payload_shape: str,
    reset_opentoken_cache,
) -> None:
    """Exercise read-only MCP tools against the live Cloudability API."""
    await _call_and_assert(
        tool_name, tool_args, payload_shape, allow_optional_skip=False
    )


@requires_live_cloudability
@pytest.mark.parametrize(
    ("tool_name", "tool_args", "payload_shape"),
    OPTIONAL_READ_ONLY_LIVE_TOOLS,
)
async def test_optional_read_only_tool_via_mcp_live_api(
    tool_name: str,
    tool_args: dict[str, Any],
    payload_shape: str,
    reset_opentoken_cache,
) -> None:
    """Exercise tenant-specific tools; skip when the API is unavailable for this org."""
    await _call_and_assert(
        tool_name, tool_args, payload_shape, allow_optional_skip=True
    )


@requires_live_cloudability
async def test_get_budget_via_mcp_live_api(reset_opentoken_cache) -> None:
    """Fetch a budget ID from list_budgets, then call get_budget for that ID."""
    async with Client(mcp) as client:
        listed = await client.call_tool("list_budgets", {})
        list_payload = _tool_payload(listed)

    assert isinstance(list_payload, dict)
    budgets = list_payload["result"]
    if not budgets:
        pytest.skip("No budgets in this environment to fetch details for")

    budget_id = budgets[0]["id"]

    async with Client(mcp) as client:
        detail = await client.call_tool("get_budget", {"budget_id": budget_id})

    detail_payload = _tool_payload(detail)
    assert isinstance(detail_payload, dict)
    assert "result" in detail_payload
    assert detail_payload["result"]["id"] == budget_id
