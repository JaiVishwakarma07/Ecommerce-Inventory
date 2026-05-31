"""Sequential single-endpoint load tests for auth, products, and orders.

No /api/v1/auth/* routes — canonical paths under /auth only.

Run one endpoint:

    set LOCUST_TARGET=auth-login
    locust -f tests/locustfile.py --headless -u 10 -r 2 --run-time 30s \\
        --host http://localhost:8000

Run all endpoints in sequence:

    powershell -File tests/run_perf_baselines.ps1

LOCUST_TARGET values:
    auth-register | auth-login | auth-me
    products-list | products-get | products-create | products-update | products-delete
    orders-create | orders-me | orders-get | orders-list | orders-status

Environment variables:
    LOCUST_ADMIN_EMAIL      Default: admin@inventory.com
    LOCUST_ADMIN_PASSWORD   Default: AdminPass123!
    LOCUST_CUSTOMER_EMAIL   Default: locust-customer@example.com
    LOCUST_CUSTOMER_PASSWORD Default: LoadTest1!Pass
"""

from __future__ import annotations

import os
import uuid

from locust import HttpUser, between, events, task

ADMIN_EMAIL = os.environ.get("LOCUST_ADMIN_EMAIL", "admin@inventory.com")
ADMIN_PASSWORD = os.environ.get("LOCUST_ADMIN_PASSWORD", "AdminPass123!")
CUSTOMER_EMAIL = os.environ.get("LOCUST_CUSTOMER_EMAIL", "locust-customer@example.com")
CUSTOMER_PASSWORD = os.environ.get("LOCUST_CUSTOMER_PASSWORD", "LoadTest1!Pass")
TARGET = os.environ.get("LOCUST_TARGET", "auth-login")

STAT_NAMES: dict[str, str] = {
    "auth-register": "POST /auth/register",
    "auth-login": "POST /auth/login",
    "auth-me": "GET /auth/me",
    "products-list": "GET /products",
    "products-get": "GET /products/{product_id}",
    "products-create": "POST /products",
    "products-update": "PUT /products/{product_id}",
    "products-delete": "DELETE /products/{product_id}",
    "orders-create": "POST /orders",
    "orders-me": "GET /orders/me",
    "orders-get": "GET /orders/{order_id}",
    "orders-list": "GET /orders",
    "orders-status": "PATCH /orders/{order_id}/status",
}

TARGET_ORDER: tuple[str, ...] = tuple(STAT_NAMES.keys())

_summary_printed = False


def _format_row(label: str, entry) -> str:
    p50 = int(entry.median_response_time or 0)
    p95 = int(entry.get_response_time_percentile(0.95) or 0)
    p99 = int(entry.get_response_time_percentile(0.99) or 0)
    rps = entry.total_rps or 0.0
    return (
        f"{label:<36} {entry.num_requests:>9} {rps:>9.2f} "
        f"{p50:>9} {p95:>9} {p99:>9}"
    )


def _print_summary(environment) -> None:
    global _summary_printed
    if _summary_printed:
        return
    _summary_printed = True

    stat_name = STAT_NAMES.get(TARGET)
    if stat_name is None:
        print(f"\n[locustfile] Unknown LOCUST_TARGET: {TARGET}")
        return

    stats = environment.stats
    entry = None
    for name, _method in stats.entries:
        if name == stat_name:
            entry = stats.entries[(name, _method)]
            break

    if entry is None or entry.num_requests == 0:
        print(f"\n[locustfile] No requests recorded for {stat_name}.")
        return

    p50 = int(entry.median_response_time or 0)
    p95 = int(entry.get_response_time_percentile(0.95) or 0)
    p99 = int(entry.get_response_time_percentile(0.99) or 0)
    rps = entry.total_rps or 0.0
    fails = entry.num_failures

    print("\n" + "=" * 86)
    print(f"LOAD TEST — {stat_name}")
    print("=" * 86)
    print(
        f"{'Endpoint':<36} {'Requests':>9} {'Req/s':>9} "
        f"{'P50 ms':>9} {'P95 ms':>9} {'P99 ms':>9}"
    )
    print("-" * 86)
    print(_format_row(stat_name, entry))
    print("=" * 86)
    print(
        f"LOCUST_PERF_RESULT|{stat_name}|{p50}|{p95}|{p99}|{rps:.2f}|"
        f"{entry.num_requests}|{fails}|{TARGET}"
    )


@events.quitting.add_listener
def _on_quitting(environment, **_kwargs) -> None:
    _print_summary(environment)


class _Session:
    admin_token: str | None = None
    customer_token: str | None = None
    product_id: int | None = None
    order_id: int | None = None
    admin_ready = False
    customer_ready = False
    catalog_ready = False
    order_ready = False


class ApiUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        if TARGET.startswith("auth-"):
            if TARGET == "auth-me":
                self._ensure_admin_token()
            return

        if TARGET.startswith("products-"):
            self._ensure_admin_token()
            if TARGET in {"products-get", "products-update", "products-delete"}:
                self._ensure_catalog_product()
            if TARGET == "products-update":
                self._ensure_update_product()
            return

        if TARGET.startswith("orders-"):
            self._ensure_customer_token()
            if TARGET in {"orders-create", "orders-get", "orders-status"}:
                self._ensure_stock_product()
            if TARGET in {"orders-get", "orders-status"}:
                self._ensure_sample_order()
            if TARGET == "orders-list":
                self._ensure_admin_token()
            return

    @task
    def hit_target(self) -> None:
        dispatch = {
            "auth-register": self._auth_register,
            "auth-login": self._auth_login,
            "auth-me": self._auth_me,
            "products-list": self._products_list,
            "products-get": self._products_get,
            "products-create": self._products_create,
            "products-update": self._products_update,
            "products-delete": self._products_delete,
            "orders-create": self._orders_create,
            "orders-me": self._orders_me,
            "orders-get": self._orders_get,
            "orders-list": self._orders_list,
            "orders-status": self._orders_status,
        }
        handler = dispatch.get(TARGET)
        if handler:
            handler()

    def _setup_post(self, path: str, **kwargs):
        return self.client.post(path, name="(setup)", catch_response=True, **kwargs)

    def _setup_get(self, path: str, **kwargs):
        return self.client.get(path, name="(setup)", catch_response=True, **kwargs)

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _ensure_admin_token(self) -> None:
        if _Session.admin_token:
            return
        if not _Session.admin_ready:
            _Session.admin_ready = True
            with self._setup_post(
                "/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            ) as response:
                if response.status_code == 200:
                    _Session.admin_token = response.json()["access_token"]

    def _ensure_customer_token(self) -> None:
        if _Session.customer_token:
            return
        if not _Session.customer_ready:
            _Session.customer_ready = True
            with self._setup_post(
                "/auth/login",
                json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD},
            ) as response:
                if response.status_code == 200:
                    _Session.customer_token = response.json()["access_token"]
                    return

            with self._setup_post(
                "/auth/register",
                json={
                    "email": CUSTOMER_EMAIL,
                    "full_name": "Locust Customer",
                    "password": CUSTOMER_PASSWORD,
                },
            ) as response:
                if response.status_code not in (200, 409):
                    response.failure(f"register failed: HTTP {response.status_code}")

            with self._setup_post(
                "/auth/login",
                json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD},
            ) as response:
                if response.status_code == 200:
                    _Session.customer_token = response.json()["access_token"]

    def _ensure_catalog_product(self) -> None:
        if _Session.product_id or not _Session.admin_token:
            return
        if not _Session.catalog_ready:
            _Session.catalog_ready = True
            with self._setup_get(
                "/products",
                headers=self._auth_headers(_Session.admin_token),
            ) as response:
                if response.status_code == 200:
                    products = response.json()
                    if products:
                        _Session.product_id = products[0]["id"]

    def _ensure_update_product(self) -> None:
        if _Session.product_id or not _Session.admin_token:
            return
        suffix = uuid.uuid4().hex[:8]
        with self._setup_post(
            "/products",
            json={
                "name": "Locust Update Target",
                "description": "update baseline",
                "sku": f"LOC-UPD-{suffix}",
                "price": 9.99,
                "quantity": 5,
                "category": "general",
            },
            headers=self._auth_headers(_Session.admin_token),
        ) as response:
            if response.status_code == 201:
                _Session.product_id = response.json()["id"]

    def _ensure_stock_product(self) -> None:
        if _Session.product_id:
            return
        self._ensure_admin_token()
        if not _Session.admin_token:
            return
        with self._setup_get("/products") as response:
            if response.status_code == 200:
                for product in response.json():
                    if product.get("quantity", 0) > 0:
                        _Session.product_id = product["id"]
                        return
        suffix = uuid.uuid4().hex[:8]
        with self._setup_post(
            "/products",
            json={
                "name": "Locust Stock Product",
                "description": "order baseline",
                "sku": f"LOC-STK-{suffix}",
                "price": 5.99,
                "quantity": 500,
                "category": "general",
            },
            headers=self._auth_headers(_Session.admin_token),
        ) as response:
            if response.status_code == 201:
                _Session.product_id = response.json()["id"]

    def _ensure_sample_order(self) -> None:
        if _Session.order_id or not _Session.customer_token:
            return
        if not _Session.order_ready:
            _Session.order_ready = True
            with self._setup_get(
                "/orders/me",
                headers=self._auth_headers(_Session.customer_token),
            ) as response:
                if response.status_code == 200:
                    orders = response.json()
                    if orders:
                        _Session.order_id = orders[0]["id"]
                        return
            self._ensure_stock_product()
            if not _Session.product_id:
                return
            with self._setup_post(
                "/orders",
                json={
                    "shipping_address": "1 Load Test Lane",
                    "items": [{"product_id": _Session.product_id, "quantity": 1}],
                },
                headers=self._auth_headers(_Session.customer_token),
            ) as response:
                if response.status_code == 201:
                    _Session.order_id = response.json()["id"]

    def _auth_register(self) -> None:
        suffix = uuid.uuid4().hex[:12]
        with self.client.post(
            "/auth/register",
            json={
                "email": f"locust-{suffix}@example.com",
                "full_name": "Locust User",
                "password": "LoadTest1!Pass",
            },
            name=STAT_NAMES["auth-register"],
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 409):
                response.failure(f"register failed: HTTP {response.status_code}")

    def _auth_login(self) -> None:
        with self.client.post(
            "/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            name=STAT_NAMES["auth-login"],
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"login failed: HTTP {response.status_code}")

    def _auth_me(self) -> None:
        if not _Session.admin_token:
            return
        with self.client.get(
            "/auth/me",
            headers=self._auth_headers(_Session.admin_token),
            name=STAT_NAMES["auth-me"],
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"me failed: HTTP {response.status_code}")

    def _products_list(self) -> None:
        with self.client.get(
            "/products",
            name=STAT_NAMES["products-list"],
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"list failed: HTTP {response.status_code}")

    def _products_get(self) -> None:
        if not _Session.product_id:
            return
        with self.client.get(
            f"/products/{_Session.product_id}",
            name=STAT_NAMES["products-get"],
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"get failed: HTTP {response.status_code}")

    def _products_create(self) -> None:
        if not _Session.admin_token:
            return
        suffix = uuid.uuid4().hex[:8]
        with self.client.post(
            "/products",
            json={
                "name": f"Locust Product {suffix}",
                "description": "load test",
                "sku": f"LOC-{suffix}",
                "price": 12.99,
                "quantity": 1,
                "category": "general",
            },
            headers=self._auth_headers(_Session.admin_token),
            name=STAT_NAMES["products-create"],
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"create failed: HTTP {response.status_code}")

    def _products_update(self) -> None:
        if not _Session.admin_token or not _Session.product_id:
            return
        suffix = uuid.uuid4().hex[:8]
        with self.client.put(
            f"/products/{_Session.product_id}",
            json={
                "name": "Locust Update Target",
                "description": "updated",
                "sku": f"LOC-UPD-{_Session.product_id}-{suffix}",
                "price": 10.99,
                "quantity": 5,
                "category": "general",
            },
            headers=self._auth_headers(_Session.admin_token),
            name=STAT_NAMES["products-update"],
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"update failed: HTTP {response.status_code}")

    def _products_delete(self) -> None:
        if not _Session.admin_token:
            return
        suffix = uuid.uuid4().hex[:8]
        product_id = None
        with self._setup_post(
            "/products",
            json={
                "name": "Locust Delete Target",
                "description": "delete baseline",
                "sku": f"LOC-DEL-{suffix}",
                "price": 1.99,
                "quantity": 1,
                "category": "general",
            },
            headers=self._auth_headers(_Session.admin_token),
        ) as response:
            if response.status_code == 201:
                product_id = response.json()["id"]
        if not product_id:
            return
        with self.client.delete(
            f"/products/{product_id}",
            headers=self._auth_headers(_Session.admin_token),
            name=STAT_NAMES["products-delete"],
            catch_response=True,
        ) as response:
            if response.status_code != 204:
                response.failure(f"delete failed: HTTP {response.status_code}")

    def _orders_create(self) -> None:
        if not _Session.customer_token or not _Session.product_id:
            return
        with self.client.post(
            "/orders",
            json={
                "shipping_address": "1 Load Test Lane",
                "items": [{"product_id": _Session.product_id, "quantity": 1}],
            },
            headers=self._auth_headers(_Session.customer_token),
            name=STAT_NAMES["orders-create"],
            catch_response=True,
        ) as response:
            if response.status_code not in (201, 409):
                response.failure(f"checkout failed: HTTP {response.status_code}")

    def _orders_me(self) -> None:
        if not _Session.customer_token:
            return
        with self.client.get(
            "/orders/me",
            headers=self._auth_headers(_Session.customer_token),
            name=STAT_NAMES["orders-me"],
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"list failed: HTTP {response.status_code}")

    def _orders_get(self) -> None:
        if not _Session.customer_token or not _Session.order_id:
            return
        with self.client.get(
            f"/orders/{_Session.order_id}",
            headers=self._auth_headers(_Session.customer_token),
            name=STAT_NAMES["orders-get"],
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"get failed: HTTP {response.status_code}")

    def _orders_list(self) -> None:
        if not _Session.admin_token:
            return
        with self.client.get(
            "/orders",
            headers=self._auth_headers(_Session.admin_token),
            name=STAT_NAMES["orders-list"],
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"admin list failed: HTTP {response.status_code}")

    def _orders_status(self) -> None:
        if not _Session.admin_token or not _Session.order_id:
            return
        with self.client.patch(
            f"/orders/{_Session.order_id}/status",
            json={"status": "processing"},
            headers=self._auth_headers(_Session.admin_token),
            name=STAT_NAMES["orders-status"],
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"status patch failed: HTTP {response.status_code}")
