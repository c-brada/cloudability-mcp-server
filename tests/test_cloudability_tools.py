import pytest
import sys
import os
from pathlib import Path

# Add the parent directory to the Python path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import responses
from cloudability_tools import (
    get_containers_report,
    get_clusters,
    get_budgets,
    get_budget_details,
    get_billing_accounts,
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
    CLOUDABILITY_API_URL
)

# Set up environment for Bearer token tests
@pytest.fixture(autouse=True)
def setup_environment():
    """Set up environment variables for testing."""
    os.environ["CLOUDABILITY_ENVIRONMENT_ID"] = "test-env-id"
    yield
    # Clean up after tests
    if "CLOUDABILITY_ENVIRONMENT_ID" in os.environ:
        del os.environ["CLOUDABILITY_ENVIRONMENT_ID"]

@pytest.fixture
def cloudability_url():
    return CLOUDABILITY_API_URL

@pytest.fixture
def auth_token():
    return "Bearer test-token"

@pytest.fixture
def basic_auth():
    return "Basic test-api-key:"

# ============================================================================
# CONTAINERS API TESTS
# ============================================================================

@responses.activate
def test_get_containers_report_success(cloudability_url, auth_token):
    """Test successful containers report request."""
    responses.add(
        responses.POST,
        f"{cloudability_url}/containers/report",
        json={
            "result": {
                "data": [
                    {
                        "dimensions": {"namespace": "kube-system"},
                        "metrics": {
                            "total_cost": {
                                "unit": "currency",
                                "values": [100.50]
                            }
                        }
                    }
                ],
                "pagination": {
                    "hasNext": False,
                    "nextToken": None
                }
            }
        },
        status=200,
    )

    result = get_containers_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
        metrics=["total_cost"],
        group=["namespace"],
        authorization=auth_token
    )

    assert "result" in result
    assert "data" in result["result"]
    assert len(result["result"]["data"]) == 1
    assert result["result"]["data"][0]["dimensions"]["namespace"] == "kube-system"

@responses.activate
def test_get_containers_report_with_filters(cloudability_url, auth_token):
    """Test containers report with filters."""
    responses.add(
        responses.POST,
        f"{cloudability_url}/containers/report",
        json={"result": {"data": []}},
        status=200,
    )

    result = get_containers_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
        filters=["cluster==test-cluster-uuid", "namespace==production"],
        authorization=auth_token
    )

    # Verify the request was made with correct filters
    request_body = responses.calls[0].request.body
    assert b'"filters": ["cluster==test-cluster-uuid", "namespace==production"]' in request_body

@responses.activate
def test_get_clusters_success(cloudability_url, auth_token):
    """Test successful clusters list request."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/containers/clusters",
        json={
            "result": [
                {
                    "id": "cluster-uuid-1",
                    "name": "production-cluster",
                    "provider": "aws"
                },
                {
                    "id": "cluster-uuid-2", 
                    "name": "staging-cluster",
                    "provider": "gcp"
                }
            ]
        },
        status=200,
    )

    result = get_clusters(authorization=auth_token)
    
    assert "result" in result
    assert len(result["result"]) == 2
    assert result["result"][0]["name"] == "production-cluster"

# ============================================================================
# BUDGETS API TESTS
# ============================================================================

@responses.activate
def test_get_budgets_success(cloudability_url, basic_auth):
    """Test successful budgets list request."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/budgets",
        json={
            "result": [
                {
                    "id": "budget-1",
                    "name": "Monthly AWS Budget",
                    "amount": 10000.00,
                    "period": "monthly"
                }
            ]
        },
        status=200,
    )

    result = get_budgets(authorization=basic_auth)
    
    assert "result" in result
    assert len(result["result"]) == 1
    assert result["result"][0]["name"] == "Monthly AWS Budget"

@responses.activate
def test_get_budget_details_success(cloudability_url, basic_auth):
    """Test successful budget details request."""
    budget_id = "budget-123"
    responses.add(
        responses.GET,
        f"{cloudability_url}/budgets/{budget_id}",
        json={
            "result": {
                "id": budget_id,
                "name": "Q1 Budget",
                "amount": 50000.00,
                "spent": 35000.00,
                "remaining": 15000.00
            }
        },
        status=200,
    )

    result = get_budget_details(budget_id, authorization=basic_auth)
    
    assert "result" in result
    assert result["result"]["id"] == budget_id
    assert result["result"]["spent"] == 35000.00

# ============================================================================
# BILLING ACCOUNTS API TESTS
# ============================================================================

@responses.activate
def test_get_billing_accounts_success(cloudability_url, auth_token):
    """Test successful billing accounts list request."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/billing-accounts",
        json={
            "result": [
                {
                    "id": "account-1",
                    "name": "Production AWS Account",
                    "provider": "aws",
                    "account_id": "123456789012"
                }
            ]
        },
        status=200,
    )

    result = get_billing_accounts(authorization=auth_token)
    
    assert "result" in result
    assert len(result["result"]) == 1
    assert result["result"][0]["provider"] == "aws"

# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

def test_missing_authorization():
    """Test that missing authorization raises ValueError."""
    with pytest.raises(ValueError, match="Authorization token is required"):
        get_containers_report("2024-01-01", "2024-01-31")

    with pytest.raises(ValueError, match="Authorization token is required"):
        get_clusters()

    with pytest.raises(ValueError, match="Authorization token is required"):
        get_budgets()

@responses.activate
def test_api_error_handling(cloudability_url, auth_token):
    """Test API error handling."""
    responses.add(
        responses.POST,
        f"{cloudability_url}/containers/report",
        json={"error": "Invalid request"},
        status=400,
    )

    with pytest.raises(Exception):  # requests.HTTPError
        get_containers_report(
            start_date="2024-01-01",
            end_date="2024-01-31",
            authorization=auth_token
        )

# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

def test_bearer_token_headers():
    """Test Bearer token authentication header generation."""
    import os
    from cloudability_tools import get_auth_headers
    
    # Mock environment variable
    os.environ["CLOUDABILITY_ENVIRONMENT_ID"] = "test-env-id"
    
    headers = get_auth_headers("Bearer test-token")
    
    assert headers["apptio-opentoken"] == "test-token"
    assert headers["apptio-environmentid"] == "test-env-id"
    assert headers["Content-Type"] == "application/json"

def test_basic_auth_headers():
    """Test Basic auth header generation."""
    from cloudability_tools import get_auth_headers
    
    headers = get_auth_headers("Basic test-api-key:")
    
    assert headers["Authorization"] == "Basic test-api-key:"
    assert headers["Content-Type"] == "application/json"

def test_missing_environment_id_for_bearer():
    """Test that Bearer token without environment ID raises error."""
    import os
    from cloudability_tools import get_auth_headers

    # Remove environment variable if it exists
    if "CLOUDABILITY_ENVIRONMENT_ID" in os.environ:
        del os.environ["CLOUDABILITY_ENVIRONMENT_ID"]

    with pytest.raises(ValueError, match="CLOUDABILITY_ENVIRONMENT_ID is required"):
        get_auth_headers("Bearer test-token")

# ============================================================================
# BUDGETS & FORECASTING API TESTS
# ============================================================================

@responses.activate
def test_get_estimate_success(cloudability_url, basic_auth):
    """Test successful estimate request."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/estimate",
        json={
            "result": {
                "estimatedSpend": 138429.32,
                "previousMonthSpend": 142252.16,
                "previousMonthFinalized": True,
                "currentDate": "2024-01-15",
                "cumulativeMtdSpend": [
                    {"date": "2024-01-01", "spend": 10418.50},
                    {"date": "2024-01-02", "spend": 14226.97}
                ]
            },
            "details": [
                {
                    "serviceName": "AWS EC2",
                    "estimatedSpend": 54638.37,
                    "mtdSpend": 23101.28,
                    "previousMonthSpend": 56600.28,
                    "usageFamily": "Instance Usage"
                }
            ]
        },
        status=200,
    )

    result = get_estimate(view_id="123", basis="cash", authorization=basic_auth)

    assert "result" in result
    assert result["result"]["estimatedSpend"] == 138429.32
    assert result["result"]["previousMonthFinalized"] is True
    assert len(result["details"]) == 1
    assert result["details"][0]["serviceName"] == "AWS EC2"

@responses.activate
def test_get_forecast_success(cloudability_url, basic_auth):
    """Test successful forecast request."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/forecast",
        json={
            "result": {
                "parameters": {
                    "viewId": "0",
                    "monthsForward": 6,
                    "monthsBack": 6,
                    "basis": "cash",
                    "useCurrentEstimate": False,
                    "removeOneTimeCharges": False,
                    "removeCredits": False
                },
                "currentMonth": "2024-01",
                "currentEstimate": 169444.38,
                "forecastTotal": 1972164.15,
                "actualTotal": 1518.72,
                "forecast": [
                    {
                        "month": "2024-02",
                        "lowerBound": 152748.68,
                        "spend": 204665.67,
                        "upperBound": 256582.65
                    }
                ],
                "forecastDetail": [
                    {
                        "month": "2024-02",
                        "spend": 1244.31,
                        "serviceName": "AWS EC2",
                        "usageFamily": "Instance Usage"
                    }
                ]
            }
        },
        status=200,
    )

    result = get_forecast(
        view_id="0",
        basis="cash",
        months_back=6,
        months_forward=6,
        authorization=basic_auth
    )

    assert "result" in result
    assert result["result"]["currentMonth"] == "2024-01"
    assert result["result"]["forecastTotal"] == 1972164.15
    assert len(result["result"]["forecast"]) == 1
    assert result["result"]["forecast"][0]["month"] == "2024-02"

def test_forecast_parameter_validation():
    """Test forecast parameter validation."""
    with pytest.raises(ValueError, match="months_back must be between 3 and 24"):
        get_forecast(months_back=2, authorization="Basic test:")

    with pytest.raises(ValueError, match="months_back must be between 3 and 24"):
        get_forecast(months_back=25, authorization="Basic test:")

    with pytest.raises(ValueError, match="months_forward must be between 1 and 24"):
        get_forecast(months_forward=0, authorization="Basic test:")

    with pytest.raises(ValueError, match="months_forward must be between 1 and 24"):
        get_forecast(months_forward=25, authorization="Basic test:")

@responses.activate
def test_create_budget_success(cloudability_url, basic_auth):
    """Test successful budget creation."""
    budget_data = {
        "name": "Q1 Budget",
        "basis": "cash",
        "viewId": "0",
        "months": [
            {"month": "2024-01", "threshold": 10000},
            {"month": "2024-02", "threshold": 12000}
        ]
    }

    responses.add(
        responses.POST,
        f"{cloudability_url}/budgets",
        json={
            "result": {
                "id": "budget-123",
                "viewId": "0",
                "name": "Q1 Budget",
                "basis": "cash",
                "ownerId": "user-456",
                "months": budget_data["months"]
            }
        },
        status=201,
    )

    result = create_budget(
        name="Q1 Budget",
        basis="cash",
        view_id="0",
        months=budget_data["months"],
        authorization=basic_auth
    )

    assert "result" in result
    assert result["result"]["id"] == "budget-123"
    assert result["result"]["name"] == "Q1 Budget"
    assert len(result["result"]["months"]) == 2

@responses.activate
def test_update_budget_success(cloudability_url, basic_auth):
    """Test successful budget update."""
    budget_id = "budget-123"
    responses.add(
        responses.PUT,
        f"{cloudability_url}/budgets/{budget_id}",
        json={
            "result": {
                "id": budget_id,
                "viewId": "0",
                "name": "Updated Q1 Budget",
                "basis": "amortized",
                "ownerId": "user-456",
                "months": [{"month": "2024-01", "threshold": 15000}]
            }
        },
        status=200,
    )

    result = update_budget(
        budget_id=budget_id,
        name="Updated Q1 Budget",
        basis="amortized",
        months=[{"month": "2024-01", "threshold": 15000}],
        authorization=basic_auth
    )

    assert "result" in result
    assert result["result"]["name"] == "Updated Q1 Budget"
    assert result["result"]["basis"] == "amortized"

@responses.activate
def test_delete_budget_success(cloudability_url, basic_auth):
    """Test successful budget deletion."""
    budget_id = "budget-123"
    responses.add(
        responses.DELETE,
        f"{cloudability_url}/budgets/{budget_id}",
        status=204,
    )

    result = delete_budget(budget_id=budget_id, authorization=basic_auth)
    assert result is True

@responses.activate
def test_create_budget_subscription_success(cloudability_url, basic_auth):
    """Test successful budget subscription creation."""
    responses.add(
        responses.POST,
        f"{cloudability_url}/budget-subscriptions",
        json={
            "result": {
                "id": "subscription-123",
                "budgetId": "budget-456",
                "notifyExceeded": True,
                "notifyExpected": False
            }
        },
        status=201,
    )

    result = create_budget_subscription(
        budget_id="budget-456",
        notify_exceeded=True,
        notify_expected=False,
        authorization=basic_auth
    )

    assert "result" in result
    assert result["result"]["id"] == "subscription-123"
    assert result["result"]["notifyExceeded"] is True
    assert result["result"]["notifyExpected"] is False

@responses.activate
def test_get_budget_subscription_success(cloudability_url, basic_auth):
    """Test successful budget subscription retrieval."""
    subscription_id = "subscription-123"
    responses.add(
        responses.GET,
        f"{cloudability_url}/budget-subscriptions/{subscription_id}",
        json={
            "result": {
                "id": subscription_id,
                "budgetId": "budget-456",
                "notifyExceeded": False,
                "notifyExpected": True
            }
        },
        status=200,
    )

    result = get_budget_subscription(subscription_id=subscription_id, authorization=basic_auth)

    assert "result" in result
    assert result["result"]["id"] == subscription_id
    assert result["result"]["budgetId"] == "budget-456"

@responses.activate
def test_list_budget_subscriptions_success(cloudability_url, basic_auth):
    """Test successful budget subscriptions list."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/budget-subscriptions",
        json={
            "result": [
                {
                    "id": "subscription-123",
                    "budgetId": "budget-456",
                    "notifyExceeded": True,
                    "notifyExpected": False
                },
                {
                    "id": "subscription-789",
                    "budgetId": "budget-101",
                    "notifyExceeded": False,
                    "notifyExpected": True
                }
            ]
        },
        status=200,
    )

    result = list_budget_subscriptions(authorization=basic_auth)

    assert "result" in result
    assert len(result["result"]) == 2
    assert result["result"][0]["id"] == "subscription-123"
    assert result["result"][1]["id"] == "subscription-789"

@responses.activate
def test_update_budget_subscription_success(cloudability_url, basic_auth):
    """Test successful budget subscription update."""
    subscription_id = "subscription-123"
    responses.add(
        responses.PUT,
        f"{cloudability_url}/budget-subscriptions/{subscription_id}",
        json={
            "result": {
                "id": subscription_id,
                "budgetId": "budget-456",
                "notifyExceeded": True,
                "notifyExpected": True
            }
        },
        status=200,
    )

    result = update_budget_subscription(
        subscription_id=subscription_id,
        notify_exceeded=True,
        notify_expected=True,
        authorization=basic_auth
    )

    assert "result" in result
    assert result["result"]["notifyExceeded"] is True
    assert result["result"]["notifyExpected"] is True

@responses.activate
def test_delete_budget_subscription_success(cloudability_url, basic_auth):
    """Test successful budget subscription deletion."""
    subscription_id = "subscription-123"
    responses.add(
        responses.DELETE,
        f"{cloudability_url}/budget-subscriptions/{subscription_id}",
        status=204,
    )

    result = delete_budget_subscription(subscription_id=subscription_id, authorization=basic_auth)
    assert result is True

# ============================================================================
# BUDGETS & FORECASTING ERROR TESTS
# ============================================================================

def test_budgets_forecasting_missing_authorization():
    """Test that missing authorization raises ValueError for all endpoints."""
    with pytest.raises(ValueError, match="Authorization token is required"):
        get_estimate()

    with pytest.raises(ValueError, match="Authorization token is required"):
        get_forecast()

    with pytest.raises(ValueError, match="Authorization token is required"):
        create_budget("Test Budget", "cash")

    with pytest.raises(ValueError, match="Authorization token is required"):
        update_budget("budget-123")

    with pytest.raises(ValueError, match="Authorization token is required"):
        delete_budget("budget-123")

    with pytest.raises(ValueError, match="Authorization token is required"):
        create_budget_subscription("budget-123")

    with pytest.raises(ValueError, match="Authorization token is required"):
        get_budget_subscription("subscription-123")

    with pytest.raises(ValueError, match="Authorization token is required"):
        list_budget_subscriptions()

    with pytest.raises(ValueError, match="Authorization token is required"):
        update_budget_subscription("subscription-123")

    with pytest.raises(ValueError, match="Authorization token is required"):
        delete_budget_subscription("subscription-123")

# ============================================================================
# COST REPORTING API TESTS
# ============================================================================

@responses.activate
def test_list_cost_reports_success(cloudability_url, basic_auth):
    """Test successful cost reports list request."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/reports/cost",
        json=[
            {
                "id": 1,
                "category": "Cost Summary",
                "custom": False,
                "description": "A breakdown of last month's costs by vendor.",
                "title": "Costs by Vendor Last Month",
                "dimensions": [
                    {
                        "name": "vendor",
                        "label": "Vendor",
                        "description": "The cloud vendor associated with the cost item.",
                        "data_type": "string",
                        "type": "dimension"
                    }
                ],
                "metrics": [
                    {
                        "name": "unblended_cost",
                        "label": "Cost (Total)",
                        "description": "Default cost metric throughout Cloudability.",
                        "data_type": "currency",
                        "type": "metric"
                    }
                ],
                "start_date": "beginning of last month",
                "end_date": "end of last month"
            }
        ],
        status=200,
    )

    result = list_cost_reports(authorization=basic_auth)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["id"] == 1
    assert result[0]["title"] == "Costs by Vendor Last Month"
    assert len(result[0]["dimensions"]) == 1
    assert result[0]["dimensions"][0]["name"] == "vendor"

@responses.activate
def test_get_cost_measures_success(cloudability_url, basic_auth):
    """Test successful cost measures request."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/cost/measures",
        json=[
            {
                "data_type": "currency",
                "description": "Total cost including taxes and credits",
                "group": {
                    "key": "billing",
                    "name": "Billing"
                },
                "label": "Total Invoiced Costs",
                "name": "invoiced_cost",
                "sub_group": {
                    "key": "costs",
                    "name": "Costs"
                },
                "type": "metric"
            },
            {
                "data_type": "string",
                "description": "The account name for a linked account",
                "group": {
                    "key": "billing",
                    "name": "Billing"
                },
                "label": "Linked Account Name",
                "name": "linked_account_name",
                "sub_group": {
                    "key": "vendor",
                    "name": "Vendor"
                },
                "type": "dimension"
            }
        ],
        status=200,
    )

    result = get_cost_measures(authorization=basic_auth)

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["name"] == "invoiced_cost"
    assert result[0]["type"] == "metric"
    assert result[1]["name"] == "linked_account_name"
    assert result[1]["type"] == "dimension"

@responses.activate
def test_get_cost_measures_with_allocations(cloudability_url, basic_auth):
    """Test cost measures request with apply_allocations parameter."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/cost/measures",
        json=[],
        status=200,
    )

    result = get_cost_measures(apply_allocations=True, authorization=basic_auth)

    # Verify the parameter was passed correctly
    assert len(responses.calls) == 1
    assert "apply_allocations=true" in responses.calls[0].request.url

@responses.activate
def test_get_cost_filter_operators_success(cloudability_url, basic_auth):
    """Test successful filter operators request."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/cost/filters",
        json=[
            "!=@",  # does not contain
            "!=",   # not equals
            "<=",   # less than or equals
            "<",    # less than
            "=@",   # contains
            "[]!=", # not in
            "[]=",  # in
            "==",   # equals
            ">",    # greater than
            "===",  # strictly equals
            "!==",  # strictly not equals
            ">="    # greater than or equals
        ],
        status=200,
    )

    result = get_cost_filter_operators(authorization=basic_auth)

    assert isinstance(result, list)
    assert "==" in result
    assert "!=" in result
    assert "=@" in result
    assert "[]=" in result
    assert len(result) == 12

@responses.activate
def test_run_cost_report_success(cloudability_url, basic_auth):
    """Test successful cost report execution."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/cost/run",
        json={
            "results": [
                {
                    "total_amortized_cost": "5334044.71",
                    "vendor": "Azure"
                },
                {
                    "total_amortized_cost": "593944.59",
                    "vendor": "Amazon"
                }
            ],
            "meta": {
                "dates": {
                    "start": "2022-02-01T00:00:00Z",
                    "end": "2022-02-28T00:00:00Z"
                },
                "filters": [
                    {
                        "comparator": "==",
                        "value": "usage",
                        "measure": {
                            "name": "transaction_type",
                            "label": "Transaction Type",
                            "type": "dimension"
                        }
                    }
                ],
                "metrics": [
                    {
                        "name": "total_amortized_cost",
                        "label": "Cost (Amortized)",
                        "type": "metric"
                    }
                ],
                "dimensions": [
                    {
                        "name": "vendor",
                        "label": "Vendor",
                        "type": "dimension"
                    }
                ],
                "aggregates": [
                    {
                        "name": "total_amortized_cost",
                        "value": "5927989.3"
                    }
                ]
            },
            "offset": 0,
            "pagination": {},
            "limit": 10000,
            "total_results": 2
        },
        status=200,
    )

    result = run_cost_report(
        start_date="2022-02-01",
        end_date="2022-02-28",
        dimensions=["vendor"],
        metrics=["total_amortized_cost"],
        filters=["transaction_type==usage"],
        sort=["total_amortized_costASC"],
        authorization=basic_auth
    )

    assert "results" in result
    assert len(result["results"]) == 2
    assert result["results"][0]["vendor"] == "Azure"
    assert result["meta"]["dates"]["start"] == "2022-02-01T00:00:00Z"
    assert result["total_results"] == 2

def test_run_cost_report_validation():
    """Test cost report parameter validation."""
    # Test too many dimensions
    with pytest.raises(ValueError, match="Maximum 15 dimensions allowed"):
        run_cost_report(
            start_date="2022-01-01",
            end_date="2022-01-31",
            dimensions=["dim" + str(i) for i in range(16)],  # 16 dimensions
            metrics=["total_cost"],
            authorization="Basic test:"
        )

    # Test too many metrics
    with pytest.raises(ValueError, match="Maximum 8 metrics allowed"):
        run_cost_report(
            start_date="2022-01-01",
            end_date="2022-01-31",
            dimensions=["vendor"],
            metrics=["metric" + str(i) for i in range(9)],  # 9 metrics
            authorization="Basic test:"
        )

@responses.activate
def test_enqueue_cost_report_success(cloudability_url, basic_auth):
    """Test successful cost report enqueue."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/cost/enqueue",
        json={"id": 31272850},
        status=200,
    )

    result = enqueue_cost_report(
        start_date="2022-02-01",
        end_date="2022-02-28",
        dimensions=["vendor"],
        metrics=["total_adjusted_amortized_cost"],
        authorization=basic_auth
    )

    assert "id" in result
    assert result["id"] == 31272850

@responses.activate
def test_get_report_state_success(cloudability_url, basic_auth):
    """Test successful report state check."""
    report_id = "31272850"
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/reports/{report_id}/state",
        json={"status": "running"},
        status=200,
    )

    result = get_report_state(report_id=report_id, authorization=basic_auth)

    assert "status" in result
    assert result["status"] == "running"

@responses.activate
def test_get_report_results_success(cloudability_url, basic_auth):
    """Test successful report results retrieval."""
    report_id = "31272850"
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/reports/{report_id}/results",
        json={
            "results": [
                {
                    "total_adjusted_amortized_cost": "586411.47",
                    "vendor": "Amazon"
                }
            ],
            "meta": {
                "dates": {
                    "start": "2022-02-01T00:00:00Z",
                    "end": "2022-02-28T00:00:00Z"
                }
            },
            "total_results": 1
        },
        status=200,
    )

    result = get_report_results(report_id=report_id, authorization=basic_auth)

    assert "results" in result
    assert len(result["results"]) == 1
    assert result["results"][0]["vendor"] == "Amazon"

@responses.activate
def test_get_report_results_with_token(cloudability_url, basic_auth):
    """Test report results retrieval with pagination token."""
    report_id = "31272850"
    token = "38bc18d0"
    responses.add(
        responses.GET,
        f"{cloudability_url}/reporting/reports/{report_id}/results",
        json={"results": [], "total_results": 0},
        status=200,
    )

    result = get_report_results(report_id=report_id, token=token, authorization=basic_auth)

    # Verify the token was passed correctly
    assert len(responses.calls) == 1
    assert f"token={token}" in responses.calls[0].request.url

# ============================================================================
# COST REPORTING ERROR TESTS
# ============================================================================

def test_cost_reporting_missing_authorization():
    """Test that missing authorization raises ValueError for all cost reporting endpoints."""
    with pytest.raises(ValueError, match="Authorization token is required"):
        list_cost_reports()

    with pytest.raises(ValueError, match="Authorization token is required"):
        get_cost_measures()

    with pytest.raises(ValueError, match="Authorization token is required"):
        get_cost_filter_operators()

    with pytest.raises(ValueError, match="Authorization token is required"):
        run_cost_report("2022-01-01", "2022-01-31", ["vendor"], ["total_cost"])

    with pytest.raises(ValueError, match="Authorization token is required"):
        enqueue_cost_report("2022-01-01", "2022-01-31", ["vendor"], ["total_cost"])

    with pytest.raises(ValueError, match="Authorization token is required"):
        get_report_state("12345")

    with pytest.raises(ValueError, match="Authorization token is required"):
        get_report_results("12345")

# ============================================================================
# CONTAINER API TESTS
# ============================================================================

@responses.activate
def test_provision_cluster_success(cloudability_url, basic_auth):
    """Test successful cluster provisioning."""
    responses.add(
        responses.POST,
        f"{cloudability_url}/containers/provisioning",
        json={
            "result": {
                "id": 1,
                "clusterName": "myTestCluster",
                "createdAt": "2018-05-18T15:40:23.29551Z",
                "kubernetesVersion": "1.11"
            }
        },
        status=200,
    )

    result = provision_cluster(
        cluster_name="myTestCluster",
        kubernetes_version="1.11",
        authorization=basic_auth
    )

    assert "result" in result
    assert result["result"]["id"] == 1
    assert result["result"]["clusterName"] == "myTestCluster"
    assert result["result"]["kubernetesVersion"] == "1.11"

def test_provision_cluster_validation():
    """Test cluster provisioning parameter validation."""
    # Test missing version parameters
    with pytest.raises(ValueError, match="Either kubernetes_version or cluster_version is required"):
        provision_cluster(
            cluster_name="test",
            authorization="Basic test:"
        )

    # Test both version parameters provided
    with pytest.raises(ValueError, match="Provide either kubernetes_version OR cluster_version, not both"):
        provision_cluster(
            cluster_name="test",
            kubernetes_version="1.25",
            cluster_version="kubernetes_1.25",
            authorization="Basic test:"
        )

@responses.activate
def test_get_cluster_deployment_config_success(cloudability_url, basic_auth):
    """Test successful deployment config retrieval."""
    yaml_content = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloudability-metrics-agent
  namespace: cloudability
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cloudability-metrics-agent
"""

    responses.add(
        responses.GET,
        f"{cloudability_url}/containers/provisioning/1/config",
        body=yaml_content,
        status=200,
    )

    result = get_cluster_deployment_config(cluster_id="1", authorization=basic_auth)

    assert "cloudability-metrics-agent" in result
    assert "apiVersion: apps/v1" in result

@responses.activate
def test_list_provisioned_clusters_success(cloudability_url, basic_auth):
    """Test successful provisioned clusters list."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/containers/provisioning",
        json={
            "result": [
                {
                    "id": 1,
                    "clusterName": "production-cluster",
                    "kubernetesVersion": "1.25",
                    "createdAt": "2023-01-15T10:30:00Z"
                },
                {
                    "id": 2,
                    "clusterName": "staging-cluster",
                    "kubernetesVersion": "1.24",
                    "createdAt": "2023-01-10T14:20:00Z"
                }
            ]
        },
        status=200,
    )

    result = list_provisioned_clusters(authorization=basic_auth)

    assert "result" in result
    assert len(result["result"]) == 2
    assert result["result"][0]["clusterName"] == "production-cluster"
    assert result["result"][1]["clusterName"] == "staging-cluster"

@responses.activate
def test_get_container_clusters_success(cloudability_url, basic_auth):
    """Test successful container clusters retrieval."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/containers/clusters",
        json={
            "result": {
                "clusters": [
                    {
                        "id": "f603489e-5bc0-4749-a61b-c5be59208355",
                        "name": "cluster-aws",
                        "firstSeen": "2018-07-26T00:00:00Z",
                        "lastSeen": "2018-11-02T00:00:00Z",
                        "provisionedAt": "2018-07-26T00:00:00Z",
                        "nodes": [
                            {
                                "vendor": "Amazon",
                                "resourceIdentifier": "i-05c3b8dcc15a2ecdb"
                            },
                            {
                                "vendor": "Amazon",
                                "resourceIdentifier": "i-0f58a6f23f21fddb9"
                            }
                        ]
                    }
                ],
                "meta": {
                    "orgHasProvisioned": True,
                    "orgHasData": True,
                    "firstSeenDate": "2018-04-13T00:00:00Z"
                }
            }
        },
        status=200,
    )

    result = get_container_clusters(
        start_date="2018-11-01",
        end_date="2018-11-05",
        authorization=basic_auth
    )

    assert "result" in result
    assert len(result["result"]["clusters"]) == 1
    assert result["result"]["clusters"][0]["name"] == "cluster-aws"
    assert len(result["result"]["clusters"][0]["nodes"]) == 2
    assert result["result"]["meta"]["orgHasProvisioned"] is True

@responses.activate
def test_get_container_allocations_success(cloudability_url, basic_auth):
    """Test successful container allocations analysis."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/containers/allocations",
        json={
            "result": {
                "allocations": [
                    {
                        "dimensions": [
                            {
                                "key": "namespace",
                                "value": "team-1"
                            }
                        ],
                        "metrics": [
                            {
                                "key": "cpu/reserved",
                                "allocation": 1,
                                "resource": {
                                    "mean": 674165746,
                                    "unit": "microcpu"
                                },
                                "fairShare": 0.9998232082752361
                            }
                        ],
                        "percentages": {
                            "allocation": 0.6989469052842922,
                            "fairShare": 0.9829955726607892
                        },
                        "costs": {
                            "fairShare": 1292.67,
                            "allocation": 919.14
                        }
                    }
                ],
                "unallocated": {
                    "metrics": [
                        {
                            "key": "memory/reserved_rss",
                            "allocation": 0.28594234634886845,
                            "resource": {
                                "mean": 58756565982,
                                "unit": "bytes"
                            }
                        }
                    ],
                    "percentages": {
                        "allocation": 0.29874400551866864
                    },
                    "cost": 392.86
                }
            }
        },
        status=200,
    )

    result = get_container_allocations(
        start_date="2018-11-01",
        end_date="2018-11-05",
        group=["namespace"],
        metrics=["cpu/reserved"],
        authorization=basic_auth
    )

    assert "result" in result
    assert len(result["result"]["allocations"]) == 1
    assert result["result"]["allocations"][0]["dimensions"][0]["value"] == "team-1"
    assert result["result"]["allocations"][0]["costs"]["allocation"] == 919.14

@responses.activate
def test_get_container_usage_success(cloudability_url, basic_auth):
    """Test successful container usage retrieval."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/containers/usage",
        json={
            "result": {
                "allocations": [
                    {
                        "metrics": [
                            {
                                "key": "cpu/reserved",
                                "allocation": [
                                    0.7987696152936873,
                                    0.8033224699512777,
                                    0.7962087739444434
                                ],
                                "resource": {
                                    "mean": [
                                        24871023,
                                        23591075,
                                        24485813
                                    ],
                                    "unit": "microcpu"
                                },
                                "available": {
                                    "mean": [
                                        31136666,
                                        29366881,
                                        30753006
                                    ],
                                    "unit": "microcpu"
                                }
                            }
                        ]
                    }
                ]
            }
        },
        status=200,
    )

    result = get_container_usage(
        start_date="2018-11-01",
        end_date="2018-11-05",
        metrics=["cpu/reserved"],
        authorization=basic_auth
    )

    assert "result" in result
    assert len(result["result"]["allocations"]) == 1
    assert len(result["result"]["allocations"][0]["metrics"][0]["allocation"]) == 3

@responses.activate
def test_get_container_labels_success(cloudability_url, basic_auth):
    """Test successful container labels discovery."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/containers/labels",
        json={
            "result": {
                "labels": [
                    {
                        "key": "cldy:labels:app",
                        "keyDisplay": "app"
                    },
                    {
                        "key": "cldy:labels:environment",
                        "keyDisplay": "environment"
                    },
                    {
                        "key": "cldy:labels:team",
                        "keyDisplay": "team"
                    }
                ]
            }
        },
        status=200,
    )

    result = get_container_labels(
        start_date="2018-11-01",
        end_date="2018-11-05",
        filters=["namespace==my-namespace"],
        authorization=basic_auth
    )

    assert "result" in result
    assert len(result["result"]["labels"]) == 3
    assert result["result"]["labels"][0]["keyDisplay"] == "app"
    assert result["result"]["labels"][2]["keyDisplay"] == "team"

@responses.activate
def test_get_container_counts_success(cloudability_url, basic_auth):
    """Test successful container counts retrieval."""
    responses.add(
        responses.GET,
        f"{cloudability_url}/containers/counts",
        json={
            "result": {
                "groups": [
                    {
                        "group": [
                            {
                                "key": "cluster",
                                "value": "e5ad2c07-2bd4-4e8f-afdf-6dbbcddc8cea"
                            }
                        ],
                        "counts": [
                            {
                                "key": "namespace",
                                "value": 9
                            },
                            {
                                "key": "service",
                                "value": 18
                            }
                        ]
                    }
                ]
            }
        },
        status=200,
    )

    result = get_container_counts(
        start_date="2018-11-01",
        end_date="2018-11-05",
        dimensions=["namespace", "service"],
        group=["cluster"],
        authorization=basic_auth
    )

    assert "result" in result
    assert len(result["result"]["groups"]) == 1
    assert len(result["result"]["groups"][0]["counts"]) == 2
    assert result["result"]["groups"][0]["counts"][0]["value"] == 9

# ============================================================================
# CONTAINER API ERROR TESTS
# ============================================================================

def test_container_apis_missing_authorization():
    """Test that missing authorization raises ValueError for all container endpoints."""
    with pytest.raises(ValueError, match="Authorization token is required"):
        provision_cluster("test-cluster", kubernetes_version="1.25")

    with pytest.raises(ValueError, match="Authorization token is required"):
        get_cluster_deployment_config("1")

    with pytest.raises(ValueError, match="Authorization token is required"):
        list_provisioned_clusters()

    with pytest.raises(ValueError, match="Authorization token is required"):
        update_provisioned_cluster("1", kubernetes_version="1.26")

    with pytest.raises(ValueError, match="Authorization token is required"):
        get_container_clusters("2023-01-01", "2023-01-31")

    with pytest.raises(ValueError, match="Authorization token is required"):
        get_container_allocations("2023-01-01", "2023-01-31")

    with pytest.raises(ValueError, match="Authorization token is required"):
        get_container_usage("2023-01-01", "2023-01-31")

    with pytest.raises(ValueError, match="Authorization token is required"):
        get_container_labels("2023-01-01", "2023-01-31")

    with pytest.raises(ValueError, match="Authorization token is required"):
        get_container_counts("2023-01-01", "2023-01-31", ["namespace"])
