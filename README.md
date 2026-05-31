# ECOM_OPPO — E-commerce Inventory

Full-stack inventory storefront: **FastAPI** backend + **React/Vite** frontend.

| Service | Local URL |
|---------|-----------|
| API | `http://127.0.0.1:8000` · [Swagger docs](http://127.0.0.1:8000/docs) |
| Frontend | `http://localhost:5173` |

Architecture details: [`docs/architecture.md`](docs/architecture.md)

---

## Prerequisites

- **Python 3.12+**
- **Node.js 18+**
- Two terminal sessions (one for backend, one for frontend)

---

## Backend setup

All backend commands run from the `backend/` directory.

### 1. Virtual environment

```bash
cd backend

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements-dev.txt
```

> Use `requirements-dev.txt` for local dev (includes pytest). Use `requirements.txt` for production-only installs.

### 2. Seed data

SQLite database: `./data/ecom_oppo.db` (created automatically on first startup).

```bash
python -m app.scripts.seed_admin      # admin user (required for product CRUD)
python -m app.scripts.seed_products   # optional sample products
```

### 3. Start the API

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify: `curl http://127.0.0.1:8000/` → `{"status":"ok","service":"ecom-oppo-api"}`

### Backend environment variables

Prefix: `ECOM_OPPO_` (see `backend/app/config.py`).

| Variable | Default | Description |
|----------|---------|-------------|
| `ECOM_OPPO_APP_ENV` | `development` | Set to `test` in pytest |
| `ECOM_OPPO_SQLITE_DEV_DB_PATH` | `./data/ecom_oppo.db` | Relative to `backend/` CWD |
| `ECOM_OPPO_DATABASE_URL` | *(empty)* | PostgreSQL URL for production |
| `ECOM_OPPO_JWT_SECRET_KEY` | dev default | **Required** outside development |
| `ECOM_OPPO_ADMIN_PASSWORD` | `AdminPass123!` | Used by `seed_admin` script only |

---

## Frontend setup

```bash
cd frontend
npm install
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
npm run dev
```

Open `http://localhost:5173`. The backend must be running at `http://127.0.0.1:8000`.

### Frontend environment

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://127.0.0.1:8000` | Backend base URL |

### Frontend features

- **Public** — Browse and search products
- **Customer** — Register/login, cart (localStorage), checkout, view orders
- **Admin** — Product CRUD, view all orders, update status (cancel restocks inventory), insights dashboard

### Frontend routes

| Path | Role | Purpose |
|------|------|---------|
| `/`, `/products`, `/products/:id` | Public | Catalog |
| `/login`, `/register` | Guest | Authentication |
| `/cart`, `/orders`, `/orders/:id` | Customer | Cart & orders |
| `/admin/products`, `/admin/orders`, `/admin/insights` | Admin | Management |

---

## Default dev credentials

| Role | Email | Password | How to create |
|------|-------|----------|---------------|
| Admin | `admin@inventory.com` | `AdminPass123!` | `python -m app.scripts.seed_admin` (from `backend/`) |
| Customer | *(your choice)* | *(your choice)* | Register in the UI or `POST /auth/register` |

Override admin password when seeding:

```bash
cd backend
export ECOM_OPPO_ADMIN_PASSWORD="YourSecurePass1!"
python -m app.scripts.seed_admin
```

---

## Run tests

### Backend (pytest)

From the **project root** with the backend venv active:

```bash
cd backend && source .venv/bin/activate && cd ..
pytest -q
```

Example (orders slice):

```bash
pytest tests/contract/test_orders_contract.py \
  tests/integration/test_orders.py \
  -k "patch_order or patch_cancel" -v
```

### Frontend (Vitest)

From the `frontend/` directory:

```bash
cd frontend
npm install
npm test
```

Frontend tests live in `tests/frontend/` and cover utilities, cart state, and route guards.

---

## API overview

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | Public | Health check |
| POST | `/auth/register` | Public | Register customer |
| POST | `/auth/login` | Public | Login (JSON) |
| GET | `/auth/me` | Bearer | Current user |
| GET | `/products` | Public | List/search catalog |
| GET | `/products/{id}` | Public | Product detail |
| POST | `/products` | Admin | Create product |
| PUT | `/products/{id}` | Admin | Update product |
| DELETE | `/products/{id}` | Admin | Delete product |
| POST | `/orders` | Customer | Checkout |
| GET | `/orders/me` | Bearer | My orders |
| GET | `/orders/{id}` | Bearer | Order detail (own or admin) |
| GET | `/orders` | Admin | List/filter orders |
| PATCH | `/orders/{id}/status` | Admin | Update order status |

---

## Project layout

```
project-root/
├── README.md              ← you are here
├── .cursor/               # Cursor skills, agents, rules
├── .specify/              # Spec Kit configuration
├── specs/                 # Feature specs and plans
├── openspec/changes/      # OpenSpec change records
├── docs/                  # Architecture, AGENTS.md, harness traces
├── backend/               # FastAPI (Python)
│   ├── app/
│   └── data/
├── frontend/              # React + Vite
└── tests/                 # pytest
```

---

## Further reading

- [`docs/architecture.md`](docs/architecture.md) — System design (frontend + backend)
- [`docs/AGENTS.md`](docs/AGENTS.md) — Agent and development conventions
- [`specs/002-product-catalog/quickstart.md`](specs/002-product-catalog/quickstart.md) — Product catalog
- [`specs/003-orders-checkout/quickstart.md`](specs/003-orders-checkout/quickstart.md) — Orders & checkout
