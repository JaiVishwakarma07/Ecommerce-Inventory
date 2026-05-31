"""Contract tests for orders-api.yaml (US1–US4 orders API)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "specs/003-orders-checkout/contracts/orders-api.yaml"
)

ORDER_REQUIRED_FIELDS = frozenset(
    {
        "id",
        "user_id",
        "status",
        "total_amount",
        "shipping_address",
        "created_at",
        "updated_at",
        "items",
    }
)

ORDER_LINE_ITEM_REQUIRED_FIELDS = frozenset(
    {
        "id",
        "product_id",
        "product_name",
        "quantity",
        "unit_price",
    }
)


@pytest.fixture
def orders_contract() -> dict:
    with CONTRACT_PATH.open(encoding="utf-8") as contract_file:
        return yaml.safe_load(contract_file)


def _operation_requires_bearer_auth(
    orders_contract: dict,
    *,
    path: str,
    method: str,
) -> None:
    operation = orders_contract["paths"][path][method]
    operation_security = operation.get("security")
    if operation_security is None:
        security_requirements = orders_contract.get("security", [])
    elif operation_security == []:
        raise AssertionError(f"{method.upper()} {path} is explicitly public")
    else:
        security_requirements = operation_security

    assert any("bearerAuth" in requirement for requirement in security_requirements)


@pytest.mark.anyio
async def test_post_orders_path_exists_in_contract(orders_contract: dict) -> None:
    paths = orders_contract["paths"]
    assert "/orders" in paths
    assert "post" in paths["/orders"]


@pytest.mark.anyio
async def test_post_orders_requires_bearer_security(orders_contract: dict) -> None:
    _operation_requires_bearer_auth(
        orders_contract,
        path="/orders",
        method="post",
    )


@pytest.mark.anyio
async def test_post_orders_request_schema_order_create(orders_contract: dict) -> None:
    schema = orders_contract["components"]["schemas"]["OrderCreate"]
    assert "shipping_address" in schema["required"]
    assert "items" in schema["required"]
    items_prop = schema["properties"]["items"]
    assert items_prop["type"] == "array"
    assert items_prop.get("minItems", 0) >= 1


@pytest.mark.anyio
async def test_post_orders_response_schema_is_order(orders_contract: dict) -> None:
    schema = (
        orders_contract["paths"]["/orders"]["post"]["responses"]["201"]["content"][
            "application/json"
        ]["schema"]
    )
    assert schema["$ref"] == "#/components/schemas/Order"


@pytest.mark.anyio
async def test_order_schema_required_fields(orders_contract: dict) -> None:
    order_schema = orders_contract["components"]["schemas"]["Order"]
    required = set(order_schema["required"])
    assert ORDER_REQUIRED_FIELDS <= required


@pytest.mark.anyio
async def test_order_schema_uses_items_not_line_items(orders_contract: dict) -> None:
    properties = orders_contract["components"]["schemas"]["Order"]["properties"]
    assert "items" in properties
    assert properties["items"]["type"] == "array"
    assert "line_items" not in properties


@pytest.mark.anyio
async def test_order_line_item_schema_snapshot_fields(orders_contract: dict) -> None:
    line_schema = orders_contract["components"]["schemas"]["OrderLineItem"]
    required = set(line_schema["required"])
    assert ORDER_LINE_ITEM_REQUIRED_FIELDS <= required


@pytest.mark.anyio
async def test_get_orders_me_path_exists_in_contract(orders_contract: dict) -> None:
    paths = orders_contract["paths"]
    assert "/orders/me" in paths
    assert "get" in paths["/orders/me"]


@pytest.mark.anyio
async def test_get_orders_me_requires_bearer_security(orders_contract: dict) -> None:
    _operation_requires_bearer_auth(
        orders_contract,
        path="/orders/me",
        method="get",
    )


@pytest.mark.anyio
async def test_get_orders_me_response_schema_is_order_array(orders_contract: dict) -> None:
    schema = (
        orders_contract["paths"]["/orders/me"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
    )
    assert schema["type"] == "array"
    assert schema["items"]["$ref"] == "#/components/schemas/Order"


@pytest.mark.anyio
async def test_get_orders_by_id_path_exists_in_contract(orders_contract: dict) -> None:
    paths = orders_contract["paths"]
    assert "/orders/{order_id}" in paths
    assert "get" in paths["/orders/{order_id}"]


@pytest.mark.anyio
async def test_get_orders_by_id_requires_bearer_security(orders_contract: dict) -> None:
    _operation_requires_bearer_auth(
        orders_contract,
        path="/orders/{order_id}",
        method="get",
    )


@pytest.mark.anyio
async def test_get_orders_by_id_response_schema_is_order(orders_contract: dict) -> None:
    schema = (
        orders_contract["paths"]["/orders/{order_id}"]["get"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]
    )
    assert schema["$ref"] == "#/components/schemas/Order"


@pytest.mark.anyio
async def test_get_orders_by_id_403_uses_error_detail_schema(orders_contract: dict) -> None:
    forbidden = orders_contract["paths"]["/orders/{order_id}"]["get"]["responses"]["403"]
    schema = forbidden["content"]["application/json"]["schema"]
    assert schema["$ref"] == "#/components/schemas/ErrorDetail"


@pytest.mark.anyio
async def test_get_orders_by_id_404_uses_not_found_response(orders_contract: dict) -> None:
    not_found = orders_contract["paths"]["/orders/{order_id}"]["get"]["responses"]["404"]
    assert not_found["$ref"] == "#/components/responses/NotFound"


def _get_admin_list_operation(orders_contract: dict) -> dict:
    return orders_contract["paths"]["/orders"]["get"]


def _get_admin_list_parameters(orders_contract: dict) -> list[dict]:
    return _get_admin_list_operation(orders_contract).get("parameters", [])


def _find_query_param(parameters: list[dict], name: str) -> dict:
    for parameter in parameters:
        if parameter.get("name") == name and parameter.get("in") == "query":
            return parameter
    raise AssertionError(f"query parameter {name!r} not found")


@pytest.mark.anyio
async def test_get_orders_admin_path_exists_in_contract(orders_contract: dict) -> None:
    paths = orders_contract["paths"]
    assert "/orders" in paths
    assert "get" in paths["/orders"]


@pytest.mark.anyio
async def test_get_orders_admin_requires_bearer_security(orders_contract: dict) -> None:
    _operation_requires_bearer_auth(
        orders_contract,
        path="/orders",
        method="get",
    )


@pytest.mark.anyio
async def test_get_orders_admin_has_status_query_param(orders_contract: dict) -> None:
    status_param = _find_query_param(_get_admin_list_parameters(orders_contract), "status")
    assert status_param["schema"]["$ref"] == "#/components/schemas/OrderStatus"


@pytest.mark.anyio
async def test_get_orders_admin_has_limit_query_param(orders_contract: dict) -> None:
    limit_param = _find_query_param(_get_admin_list_parameters(orders_contract), "limit")
    limit_schema = limit_param["schema"]
    assert limit_schema["type"] == "integer"
    assert limit_schema["minimum"] == 1
    assert limit_schema["maximum"] == 100


@pytest.mark.anyio
async def test_get_orders_admin_response_schema_is_order_array(orders_contract: dict) -> None:
    schema = (
        _get_admin_list_operation(orders_contract)["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
    )
    assert schema["type"] == "array"
    assert schema["items"]["$ref"] == "#/components/schemas/Order"


@pytest.mark.anyio
async def test_get_orders_admin_403_uses_forbidden_response(orders_contract: dict) -> None:
    forbidden = _get_admin_list_operation(orders_contract)["responses"]["403"]
    assert forbidden["$ref"] == "#/components/responses/Forbidden"


def _get_patch_order_status_operation(orders_contract: dict) -> dict:
    return orders_contract["paths"]["/orders/{order_id}/status"]["patch"]


@pytest.mark.anyio
async def test_patch_order_status_path_exists_in_contract(orders_contract: dict) -> None:
    paths = orders_contract["paths"]
    assert "/orders/{order_id}/status" in paths
    assert "patch" in paths["/orders/{order_id}/status"]


@pytest.mark.anyio
async def test_patch_order_status_requires_bearer_security(orders_contract: dict) -> None:
    _operation_requires_bearer_auth(
        orders_contract,
        path="/orders/{order_id}/status",
        method="patch",
    )


@pytest.mark.anyio
async def test_patch_order_status_request_schema_is_order_status_update(
    orders_contract: dict,
) -> None:
    schema = (
        _get_patch_order_status_operation(orders_contract)["requestBody"]["content"][
            "application/json"
        ]["schema"]
    )
    assert schema["$ref"] == "#/components/schemas/OrderStatusUpdate"


@pytest.mark.anyio
async def test_patch_order_status_response_schema_is_order(orders_contract: dict) -> None:
    schema = (
        _get_patch_order_status_operation(orders_contract)["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
    )
    assert schema["$ref"] == "#/components/schemas/Order"


@pytest.mark.anyio
async def test_patch_order_status_403_uses_forbidden_response(orders_contract: dict) -> None:
    forbidden = _get_patch_order_status_operation(orders_contract)["responses"]["403"]
    assert forbidden["$ref"] == "#/components/responses/Forbidden"


@pytest.mark.anyio
async def test_patch_order_status_404_uses_not_found_response(orders_contract: dict) -> None:
    not_found = _get_patch_order_status_operation(orders_contract)["responses"]["404"]
    assert not_found["$ref"] == "#/components/responses/NotFound"
