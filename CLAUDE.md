# Swiss Property Management Accounting Platform (ImmoManager)

## Overview

A full-stack AI-powered accounting, revenue-sharing, payroll, banking, and bookkeeping platform for small Swiss property management companies operated by multiple property managers.

## Architecture

```
├── frontend/          # Next.js 14 + TypeScript + Tailwind CSS
├── backend/           # Django 4.2 + Django REST Framework
├── docker-compose.yml # Full local development stack
└── .env.example       # Environment variable template
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Radix UI, Recharts |
| Backend | Django 4.2, Django REST Framework, Celery |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis 7 |
| Storage | Local media / AWS S3 / Cloudflare R2 |
| Auth | JWT (djangorestframework-simplejwt) |
| OCR | Tesseract (local) / Azure Cognitive Services / GPT-4 Vision |
| Banking | bLink by SIX, UBS Open Banking, ISO 20022 |

## Backend Apps

| App | Description |
|-----|-------------|
| `apps.accounts` | User management, JWT auth, company settings |
| `apps.properties` | Property management, revenue calculation engine |
| `apps.expenses` | Expense tracking, AI OCR, document management |
| `apps.banking` | Open Banking integration, transaction reconciliation |
| `apps.payroll` | Swiss payroll (AHV/IV/EO/ALV/NBU/BVG), Lohnausweis |
| `apps.accounting` | Fiscal year management, accounting entries, year-end closing |
| `apps.reports` | Excel/PDF/CSV export, dashboard analytics |
| `apps.documents` | Document archiving, audit trails |

## Key Business Logic

### Revenue Calculation (apps/properties/services.py)

```python
# First year (prorated):
# Annual fee / 12 × months remaining in year
# e.g., CHF 3,000 fee, April 1 start → 3000/12 × 9 = CHF 2,250

# Subsequent years: full annual fee
```

### Expense Allocation Methods

1. **MANAGER_A** / **MANAGER_B** — 100% to one manager
2. **FIFTY_FIFTY** — Equal split (50/50)
3. **REVENUE_BASED** — Proportional to yearly revenue share (recalculates dynamically)

### Swiss Payroll Rates (2024)

| Deduction | Employee | Employer |
|-----------|----------|----------|
| AHV | 5.30% | 5.30% |
| IV | 0.70% | 0.70% |
| EO | 0.25% | 0.25% |
| ALV | 1.10% | 1.10% |
| NBU | ~0.17% | — |

## Development Setup

### Prerequisites
- Docker + Docker Compose
- Node.js 20+ (for frontend dev)
- Python 3.12+ (for backend dev)

### Quick Start with Docker

```bash
cp .env.example .env
# Edit .env with your values

docker compose up -d db redis
docker compose up backend frontend
```

### Local Development (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**Frontend:**
```bash
cd frontend
npm install
cp ../.env.example .env.local
npm run dev
```

### API Documentation

With backend running:
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- Django Admin: http://localhost:8000/admin/

## Document ID Format

All entities use auto-generated unique IDs:
- Properties: `PROP-2026-000001`
- Expenses: `EXP-2026-000145`
- Invoices: `INV-2026-000032`
- Transactions: `TRX-2026-000001`
- Accounting entries: `ACC-2026-000001`
- Documents: `DOC-2026-000001`

## Audit Trail

All changes are logged immutably:
- Who changed what, when
- Old value → New value
- IP address recorded
- Changes cannot be deleted

## Year-End Closing

When a fiscal year is closed:
1. Revenue percentages snapshot is saved
2. All expense allocations are finalized
3. Payroll is confirmed
4. Historical data becomes read-only
5. Settlement report is generated

## Open Banking

Supports Swiss Open Banking standards:
- **bLink by SIX**: PSD2-compliant account access
- **UBS Open Banking**: Direct UBS business account integration
- **ISO 20022**: Swiss payment message standard

## Security

- JWT authentication with refresh tokens
- Role-based permissions (MANAGER, ADMIN)
- Encrypted document storage
- Immutable audit logs
- 10-year document retention compliance
- Swiss-compliant digital archiving

## Future Roadmap

- Swissdec integration (payroll data exchange)
- Direct salary payment initiation
- Automatic VAT reporting
- AI bookkeeping assistant
- Cashflow forecasting
- Native iOS/Android apps
- Multi-company support
