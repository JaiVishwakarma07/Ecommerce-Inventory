"""Contract tests for products-api.yaml (GET /products slice)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "specs/002-product-catalog/contracts/products-api.yaml"
)

PRODUCT_REQUIRED_FIELDS = frozenset(
    {
        "id",
        "name",
        "description",
        "sku",
        "price",
        "quantity",
        "category",
        "image_url",
        "created_at",
        "updated_at",
    }
)


@pytest.fixture
def products_contract() -> dict:
    with CONTRACT_PATH.open(encoding="utf-8") as contract_file:
        return yaml.safe_load(contract_file)


@pytest.mark.anyio
async def test_get_products_path_exists_in_contract(products_contract: dict) -> None:
    paths = products_contract["paths"]
    assert "/products" in paths
    assert "get" in paths["/products"]


@pytest.mark.anyio
async def test_get_products_has_no_security_requirement(products_contract: dict) -> None:
    get_operation = products_contract["paths"]["/products"]["get"]
    assert get_operation.get("security") == []


@pytest.mark.anyio
async def test_get_products_response_is_array_of_product(products_contract: dict) -> None:
    schema = (
        products_contract["paths"]["/products"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
    )
    assert schema["type"] == "array"
    assert schema["items"]["$ref"] == "#/components/schemas/Product"


@pytest.mark.anyio
async def test_product_schema_required_fields(products_contract: dict) -> None:
    product_schema = products_contract["components"]["schemas"]["Product"]
    write_required = set(
        products_contract["components"]["schemas"]["ProductWrite"]["required"]
    )
    response_required = set(product_schema["allOf"][1]["required"])
    required = write_required | response_required
    assert PRODUCT_REQUIRED_FIELDS <= required


@pytest.mark.anyio
async def test_product_schema_image_url_default_is_empty_string(products_contract: dict) -> None:
    image_url = products_contract["components"]["schemas"]["ProductWrite"]["properties"][
        "image_url"
    ]
    assert image_url["type"] == "string"
    assert image_url.get("default") == ""
    assert "nullable" not in image_url or image_url.get("nullable") is not True


@pytest.mark.anyio
async def test_get_product_by_id_path_exists_in_contract(products_contract: dict) -> None:
    paths = products_contract["paths"]
    assert "/products/{product_id}" in paths
    assert "get" in paths["/products/{product_id}"]


@pytest.mark.anyio
async def test_get_product_by_id_has_no_security_requirement(products_contract: dict) -> None:
    get_operation = products_contract["paths"]["/products/{product_id}"]["get"]
    assert get_operation.get("security") == []


@pytest.mark.anyio
async def test_get_product_by_id_response_is_product_schema(products_contract: dict) -> None:
    schema = (
        products_contract["paths"]["/products/{product_id}"]["get"]["responses"]["200"][
            "content"
        ]["application/json"]["schema"]
    )
    assert schema["$ref"] == "#/components/schemas/Product"


@pytest.mark.anyio
async def test_get_product_by_id_404_uses_not_found_response(products_contract: dict) -> None:
    not_found = products_contract["paths"]["/products/{product_id}"]["get"]["responses"]["404"]
    assert not_found["$ref"] == "#/components/responses/NotFound"


def _operation_requires_bearer_auth(
    products_contract: dict,
    *,
    path: str,
    method: str,
) -> None:
    operation = products_contract["paths"][path][method]
    operation_security = operation.get("security")
    if operation_security is None:
        security_requirements = products_contract.get("security", [])
    elif operation_security == []:
        raise AssertionError(f"{method.upper()} {path} is explicitly public")
    else:
        security_requirements = operation_security

    assert any("bearerAuth" in requirement for requirement in security_requirements)


@pytest.mark.anyio
async def test_post_products_requires_bearer_auth(products_contract: dict) -> None:
    _operation_requires_bearer_auth(
        products_contract,
        path="/products",
        method="post",
    )


@pytest.mark.anyio
async def test_put_products_by_id_requires_bearer_auth(products_contract: dict) -> None:
    _operation_requires_bearer_auth(
        products_contract,
        path="/products/{product_id}",
        method="put",
    )


@pytest.mark.anyio
async def test_delete_products_by_id_requires_bearer_auth(products_contract: dict) -> None:
    _operation_requires_bearer_auth(
        products_contract,
        path="/products/{product_id}",
        method="delete",
    )


@pytest.mark.anyio
async def test_post_products_request_body_is_product_write(products_contract: dict) -> None:
    schema = (
        products_contract["paths"]["/products"]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]
    )
    assert schema["$ref"] == "#/components/schemas/ProductWrite"


@pytest.mark.anyio
async def test_put_products_request_body_is_product_write(products_contract: dict) -> None:
    schema = (
        products_contract["paths"]["/products/{product_id}"]["put"]["requestBody"]["content"][
            "application/json"
        ]["schema"]
    )
    assert schema["$ref"] == "#/components/schemas/ProductWrite"


@pytest.mark.anyio
async def test_post_products_201_response_is_product(products_contract: dict) -> None:
    schema = (
        products_contract["paths"]["/products"]["post"]["responses"]["201"]["content"][
            "application/json"
        ]["schema"]
    )
    assert schema["$ref"] == "#/components/schemas/Product"


@pytest.mark.anyio
async def test_product_write_schema_required_fields(products_contract: dict) -> None:
    required = set(
        products_contract["components"]["schemas"]["ProductWrite"]["required"]
    )
    assert required == {
        "name",
        "description",
        "sku",
        "price",
        "quantity",
        "category",
        "image_url",
    }
