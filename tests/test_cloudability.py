import pytest
import sys
from pathlib import Path

# Add the parent directory to the Python path so we can import main
sys.path.insert(0, str(Path(__file__).parent.parent))

import responses
from main import _get_cost_reports, _get_usage_data
from cloudability_tools import CLOUDABILITY_API_URL

@pytest.fixture
def cloudability_url():
    return CLOUDABILITY_API_URL

@responses.activate
def test_get_cost_reports(cloudability_url):
    responses.add(
        responses.GET,
        f"{cloudability_url}/reports/cost/run",
        json={"results": [{"cost": 100}]},
        status=200,
    )

    result = _get_cost_reports(
        start_date="2024-01-01",
        end_date="2024-01-31",
        dimensions=["service"],
        authorization="Basic testtoken:"
    )

    assert result == {"results": [{"cost": 100}]}

@responses.activate
def test_get_usage_data(cloudability_url):
    responses.add(
        responses.GET,
        f"{cloudability_url}/reports/usage/run",
        json={"results": [{"usage": 500}]},
        status=200,
    )

    result = _get_usage_data(
        period="last_30_days",
        authorization="Basic testtoken:"
    )

    assert result == {"usage_records": [{"usage": 500}]}

def test_missing_auth_header():
    with pytest.raises(ValueError, match="Authorization token is required"):
        _get_cost_reports(
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
