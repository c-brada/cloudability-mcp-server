"""Tests for Cloudability MCP reference resources."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest
import responses

sys.path.insert(0, str(Path(__file__).parent.parent))

import cloudability_resources
from cloudability_resources import (
    get_filter_operators_resource,
    get_measures_resource,
    get_saved_reports_resource,
    get_server_config_resource,
    invalidate_resource_cache,
)
from fastmcp import Client
from main import mcp

from cloudability_tools import CLOUDABILITY_API_URL, CLOUDABILITY_FRONTDOOR_URL


@pytest.fixture(autouse=True)
def setup_environment() -> None:
    os.environ["CLOUDABILITY_ENVIRONMENT_ID"] = "test-env-id"
    yield
    os.environ.pop("CLOUDABILITY_ENVIRONMENT_ID", None)


@pytest.fixture
def cloudability_url() -> str:
    return CLOUDABILITY_API_URL


@pytest.fixture
def basic_auth() -> str:
    return "Basic test-api-key:"


@pytest.fixture(autouse=True)
def clear_resource_cache() -> None:
    invalidate_resource_cache()
    yield
    invalidate_resource_cache()


def test_get_server_config_resource_no_secrets() -> None:
    config = get_server_config_resource()
    assert config["api_url"]
    serialized = json.dumps(config).lower()
    assert "key_secret" not in serialized
    assert "key_access" not in serialized
    assert "cloudability://measures" in config["resource_uris"]


def _use_frontdoor_env_keys() -> None:
    os.environ["CLOUDABILITY_KEY_ACCESS"] = "test-public-key"
    os.environ["CLOUDABILITY_KEY_SECRET"] = "test-private-key"


def _clear_frontdoor_env_keys() -> None:
    os.environ.pop("CLOUDABILITY_KEY_ACCESS", None)
    os.environ.pop("CLOUDABILITY_KEY_SECRET", None)
    import cloudability_tools

    cloudability_tools.invalidate_opentoken_cache()
    invalidate_resource_cache()


@responses.activate
def test_measures_resource_uses_cache(cloudability_url) -> None:
    _use_frontdoor_env_keys()
    responses.add(
        responses.POST,
        CLOUDABILITY_FRONTDOOR_URL,
        json={"message": "ok"},
        headers={"apptio-opentoken": "token"},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/cost/measures",
        json=[{"name": "vendor", "type": "dimension"}],
        status=200,
    )

    try:
        first = get_measures_resource(apply_allocations=False)
        second = get_measures_resource(apply_allocations=False)

        assert first == second == {"result": [{"name": "vendor", "type": "dimension"}]}
        measure_calls = [
            c
            for c in responses.calls
            if c.request.url.startswith(f"{cloudability_url}/reporting/cost/measures")
        ]
        assert len(measure_calls) == 1
    finally:
        _clear_frontdoor_env_keys()


@responses.activate
def test_measures_resource_cache_expires(cloudability_url, monkeypatch) -> None:
    _use_frontdoor_env_keys()
    responses.add(
        responses.POST,
        CLOUDABILITY_FRONTDOOR_URL,
        json={"message": "ok"},
        headers={"apptio-opentoken": "token"},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/cost/measures",
        json=[{"name": "vendor", "type": "dimension"}],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/cost/measures",
        json=[{"name": "region", "type": "dimension"}],
        status=200,
    )

    monkeypatch.setattr(cloudability_resources, "_RESOURCE_CACHE_TTL_SECONDS", 1)

    try:
        get_measures_resource(apply_allocations=False)

        entry = cloudability_resources._resource_cache["measures:apply_allocations=False"]
        cloudability_resources._resource_cache["measures:apply_allocations=False"] = (
            time.time() - 1,
            entry[1],
        )

        refreshed = get_measures_resource(apply_allocations=False)
        assert refreshed["result"][0]["name"] == "region"
        measure_calls = [
            c
            for c in responses.calls
            if c.request.url.startswith(f"{cloudability_url}/reporting/cost/measures")
        ]
        assert len(measure_calls) == 2
    finally:
        _clear_frontdoor_env_keys()


@responses.activate
def test_filter_operators_resource(cloudability_url, basic_auth) -> None:
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/cost/filters",
        json=["==", "!=", "=@"],
        status=200,
    )

    payload = get_filter_operators_resource(authorization=basic_auth)
    assert payload == {"result": ["==", "!=", "=@"]}


@responses.activate
def test_saved_reports_resource(cloudability_url, basic_auth) -> None:
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/reports/cost",
        json=[{"id": 1, "title": "Costs by Vendor"}],
        status=200,
    )

    payload = get_saved_reports_resource(authorization=basic_auth)
    assert payload["result"][0]["title"] == "Costs by Vendor"


@pytest.mark.asyncio
async def test_mcp_lists_reference_resources() -> None:
    async with Client(mcp) as client:
        resources = await client.list_resources()

    uris = {str(resource.uri) for resource in resources}
    assert uris == {
        "cloudability://config",
        "cloudability://measures",
        "cloudability://measures/allocated",
        "cloudability://filter-operators",
        "cloudability://saved-reports",
    }


@responses.activate
@pytest.mark.asyncio
async def test_mcp_read_config_resource() -> None:
    async with Client(mcp) as client:
        contents = await client.read_resource("cloudability://config")

    assert contents
    payload = json.loads(contents[0].text)
    assert payload["auth_mode"] in {
        "frontdoor_api_keys",
        "bearer_or_basic_explicit",
        "explicit_only",
    }


@responses.activate
@pytest.mark.asyncio
async def test_mcp_read_measures_resource(cloudability_url) -> None:
    _use_frontdoor_env_keys()

    responses.add(
        responses.POST,
        CLOUDABILITY_FRONTDOOR_URL,
        json={"message": "ok"},
        headers={"apptio-opentoken": "token"},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/cost/measures",
        json=[{"name": "total_cost", "type": "metric"}],
        status=200,
    )

    try:
        async with Client(mcp) as client:
            contents = await client.read_resource("cloudability://measures")

        payload = json.loads(contents[0].text)
        assert payload["result"][0]["name"] == "total_cost"
    finally:
        _clear_frontdoor_env_keys()
