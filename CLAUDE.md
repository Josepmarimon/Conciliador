# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Quick Start](#quick-start)
4. [Architecture](#architecture)
5. [Core Algorithms](#core-algorithms)
6. [API Reference](#api-reference)
7. [Data Structures](#data-structures)
8. [Frontend Components](#frontend-components)
9. [Configuration](#configuration)
10. [Development Guidelines](#development-guidelines)
11. [SaaS Conversion Roadmap](#saas-conversion-roadmap)

---

## Project Overview

**Conciliador** is a sophisticated accounting reconciliation tool designed for Assessoria Egara. It automatically matches invoices with payments using a **5-phase Waterfall Reconciliation** algorithm.

### Core Value Proposition

| Feature | Description |
|---------|-------------|
| **Automatic Matching** | 5-phase algorithm handles routine reconciliation |
| **Human Control** | Surfaces problematic cases for professional review |
| **Confidence Scoring** | Each match rated 0-100% reliability |
| **Multi-format Support** | Handles various Excel schemas from accounting software |

### Primary Use Cases

1. **Accounts Receivable (Clientes)** - Track customer invoice payments
2. **Accounts Payable (Proveedores)** - Track supplier invoice payments
3. **Aged Analysis** - Identify overdue invoices by days outstanding
4. **Audit Trail** - Document decisions on unmatched payments

### Target Users

- Accounting professionals at Assessoria Egara
- Bookkeepers managing client accounts
- Financial controllers reviewing reconciliation reports

---

## Tech Stack

### Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  React 19 + Vite 7 + Axios + Lucide Icons                   │
│  Deployment: Render.com Static Site                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS (REST API)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                               │
│  FastAPI + Pandas + NumPy + OpenPyXL + xlsxwriter           │
│  Deployment: Render.com Web Service                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     EXTERNAL SERVICES                        │
│  CountAPI.xyz (anonymous usage stats)                        │
└─────────────────────────────────────────────────────────────┘
```

### Dependencies

**Backend** (`backend/requirements.txt`):
```
fastapi          # Web framework
uvicorn          # ASGI server
pandas           # Data manipulation
numpy            # Numerical operations
openpyxl         # Excel reading
xlsxwriter       # Excel writing with formatting
python-multipart # File upload handling
requests         # HTTP client for stats
```

**Frontend** (`frontend/package.json`):
```json
{
  "dependencies": {
    "axios": "^1.13.2",
    "lucide-react": "^0.554.0",
    "react": "^19.2.0",
    "react-dom": "^19.2.0"
  }
}
```

---

## Quick Start

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev  # Opens http://localhost:5173
```

### CLI Processing

```bash
cd backend
python conciliador_fifo.py input.xlsx \
  -o output.xlsx \
  --ar-prefix 43 \
  --ap-prefix 40 \
  --tol 0.01
```

---

## Architecture

### File Structure

```
conciliador/
├── backend/
│   ├── main.py                 # FastAPI app, endpoints
│   ├── reconciliation.py       # Core engine (1,900+ lines)
│   ├── stats.py                # Usage tracking via CountAPI
│   ├── conciliador_fifo.py     # CLI tool
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Main application (1,400+ lines)
│   │   ├── HelpModal.jsx       # Educational modal (466 lines)
│   │   ├── api.js              # Axios API client
│   │   └── main.jsx            # React entry point
│   ├── package.json
│   └── vite.config.js
└── CLAUDE.md                   # This file
```

### Backend Modules

#### `main.py` - API Server

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check, returns total reconciliations |
| `/stats` | GET | Usage statistics |
| `/conciliate` | POST | Main reconciliation endpoint |

#### `reconciliation.py` - Core Engine

**Key Classes:**

```python
class Reconciler:
    """Maintains state of open invoices per tercero (third party).

    Attributes:
        open_invoices: List[dict] - Invoices awaiting payment
        tolerance: float - Amount tolerance for matching

    Methods:
        add_invoice(row) - Register new invoice
        process_payment(row) - Match payment against open invoices
    """
```

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `find_header_row(df)` | Locate header row in Excel (scans first 30 rows) |
| `detect_schema(df)` | Map column names to internal schema |
| `extract_company_name(df)` | Get company name from pre-header rows |
| `extract_period(df)` | Get period (e.g., "1T 2025") from metadata |
| `reconcile_fifo(df, tol)` | Main reconciliation algorithm |
| `generate_reconciliation_data(...)` | Full pipeline orchestration |
| `build_human_format_excel(...)` | Create human-readable Excel output |

#### `stats.py` - Usage Tracking

```python
def increment_reconciliation_count(rows_processed: int) -> None:
    """Increment usage counters via CountAPI.xyz"""

def get_stats() -> dict:
    """Returns: {"total_reconciliations": int, "total_rows_processed": int}"""
```

### Frontend Components

#### Component Hierarchy

```
App.jsx
├── Header (sticky)
│   ├── Company name + Period
│   └── Logo
├── Sidebar (collapsible)
│   ├── FileUpload
│   ├── Settings (tolerance, prefixes)
│   ├── ActionButton (Conciliar)
│   └── StatsCard
├── MainContent
│   ├── MetricsGrid (4 cards)
│   └── ReconciliationDetails
│       ├── TabNavigation (Clientes/Proveedores)
│       ├── FilterBar
│       ├── MatchesList
│       │   ├── TerceroCard (collapsible)
│       │   │   ├── InvoiceRow
│       │   │   │   └── PaymentRow (expandable)
│       │   │   └── UnmatchedPaymentRow
│       │   │       └── JustificationDropdown
│       └── PendingList (table)
└── HelpModal (modal overlay)
```

### Data Flow

```
1. User uploads Excel
   ↓
2. POST /conciliate (multipart/form-data)
   ↓
3. Backend Processing:
   a) find_header_row() → Locate header
   b) detect_schema() → Map columns
   c) extract_company_name() + extract_period()
   d) Split by account prefix (43=AR, 40=AP)
   e) For each tercero:
      - Sort chronologically
      - Run 5-phase matching:
        Phase 1: Reference Match (fuzzy)
        Phase 2: Exact Amount Match
        Phase 3: Combined Amount (2-3 invoices)
        Phase 4: Date Proximity Match
        Phase 5: FIFO Fallback
      - Calculate residuals
      - Assign confidence scores
   f) Generate output sheets
   g) Serialize to JSON + base64 Excel
   ↓
4. Frontend receives response
   ↓
5. Display metrics + interactive tables
   ↓
6. User reviews, justifies, downloads
```

---

## Core Algorithms

### 5-Phase Waterfall Reconciliation

The algorithm processes payments in priority order, stopping at the first successful match:

#### Phase 1: Reference Match (Confidence: 80-100%)

Searches for invoice document numbers in payment concept field using fuzzy matching.

```python
# Extract references from document and concept fields
invoice_refs = extract_invoice_references("INV-2024-001")
# Returns: ['2024001', '001', 'INV-2024-001', ...]

payment_refs = extract_invoice_references("Pago fact. 2024-001")
# Returns: ['2024001', '001', ...]

# Fuzzy match with 70% threshold
for inv_ref in invoice_refs:
    for pay_ref in payment_refs:
        score = fuzzy_match_score(inv_ref, pay_ref)
        if score >= 0.7:
            return match  # Confidence: 80 + (score * 20)
```

#### Phase 2: Exact Amount Match (Confidence: 80-90%)

Finds single invoice with remaining amount exactly equal to payment.

```python
for invoice in open_invoices:
    if abs(invoice.remaining - payment_amount) <= tolerance:
        # Prefer invoices closer in date
        days_diff = abs(payment_date - invoice_date).days
        confidence = 90 if days_diff <= 30 else 85 if days_diff <= 60 else 80
        return match
```

#### Phase 3: Combined Amount Match (Confidence: 80-85%)

Attempts to match payment against 2-3 invoices that sum to payment amount.

```python
# Try combinations of 2-3 invoices
for combo in combinations(open_invoices, 2):
    if abs(sum(inv.remaining for inv in combo) - payment) <= tolerance:
        return match  # Confidence: 85%

for combo in combinations(open_invoices, 3):
    if abs(sum(inv.remaining for inv in combo) - payment) <= tolerance:
        return match  # Confidence: 80%
```

#### Phase 4: Date Proximity Match (Confidence: 65-75%)

Matches when payment date is 0-45 days after invoice and amount is within 20%.

```python
for invoice in open_invoices:
    days_after = (payment_date - invoice_date).days
    amount_ratio = payment / invoice.remaining

    if 0 <= days_after <= 45 and 0.80 <= amount_ratio <= 1.20:
        confidence = 75 if days_after <= 15 else 70 if days_after <= 30 else 65
        return match
```

#### Phase 5: FIFO Fallback (Confidence: 45-75%)

Chronologically matches oldest invoices first with dynamic confidence scoring.

```python
for idx, invoice in enumerate(open_invoices):
    take = min(invoice.remaining, payment_left)

    # Base confidence
    confidence = 45

    # Coverage ratio bonus (+5 to +15)
    coverage = take / invoice.remaining
    if 0.90 <= coverage <= 1.10:
        confidence += 15
    elif 0.80 <= coverage <= 1.20:
        confidence += 10
    elif coverage >= 0.40:
        confidence += 5

    # Date proximity bonus (+5 to +20)
    days = (payment_date - invoice_date).days
    if days <= 45: confidence += 20
    elif days <= 75: confidence += 15
    elif days <= 120: confidence += 10
    elif days <= 180: confidence += 5

    # Position bonus
    if idx == 0: confidence += 5

    # Clean allocation bonus
    if fully_allocates: confidence += 5

    confidence = min(confidence, 75)  # Cap at 75%
```

### Confidence Score Summary

| Match Method | Confidence Range | Description |
|--------------|------------------|-------------|
| **Reference** | 80-100% | Document number found in concept |
| **Exact** | 80-90% | Amount matches exactly |
| **CombinedAmount** | 80-85% | 2-3 invoices sum to payment |
| **DateProximity** | 65-75% | Date/amount within range |
| **FIFO** | 45-75% | Oldest first with scoring |
| **Unallocated** | 0% | No matching invoice |
| **Open** | 0% | Unpaid invoice |
| **PreReconciled** | 100% | Already matched in input |

### Pre-Reconciled Items

Items marked with "Sí" in the `Punt.` column are passed through without re-matching:

```python
if row.get('punt', '').lower() in ['sí', 'si', 'yes', 'x']:
    return {
        'MatchMethod': 'PreReconciled',
        'Confidence': 100,
        # ... preserve original data
    }
```

---

## API Reference

### POST /conciliate

Main reconciliation endpoint.

**Request:**

```http
POST /conciliate HTTP/1.1
Content-Type: multipart/form-data

file: <binary .xlsx file>          # Required
tol: 0.01                          # Tolerance (default: 0.01)
ar_prefix: 43                      # AR account prefix (default: 43)
ap_prefix: 40                      # AP account prefix (default: 40)
justifications: {"key": "reason"}  # JSON string of justifications
output_format: human               # "human" or "detailed"
```

**Response (200 OK):**

```json
{
  "summary": [
    {
      "Bloque": "Clientes",
      "Asignado": 15234.50,
      "Pagos_sin_factura": -234.50,
      "Docs_pendientes": 3
    },
    {
      "Bloque": "Proveedores",
      "Asignado": 8900.00,
      "Pagos_sin_factura": 0.00,
      "Docs_pendientes": 1
    }
  ],
  "meta": [],
  "details": {
    "Clientes_Detalle": [...],
    "Pendientes_Clientes": [...],
    "Proveedores_Detalle": [...],
    "Pendientes_Proveedores": [...]
  },
  "company_name": "EMPRESA S.L.",
  "period": "1T 2025",
  "filename": "original_conciliado.xlsx",
  "file_b64": "UEsDBBQAB..."
}
```

**Error Response (400/500):**

```json
{
  "detail": "Invalid file format. Please upload an Excel file (.xlsx)."
}
```

### GET /stats

Usage statistics.

**Response:**

```json
{
  "total_reconciliations": 42,
  "total_rows_processed": 15234
}
```

### GET /

Health check.

**Response:**

```json
{
  "message": "Conciliador FIFO API is running",
  "total_reconciliations": 42
}
```

---

## Data Structures

### Excel Input Schema

The system auto-detects columns using these patterns:

| Internal Name | Detected Patterns |
|---------------|-------------------|
| `fecha` | fecha, data, date, fec |
| `cuenta` | cuenta, compte, account, cta |
| `debe` | debe, deure, debit |
| `haber` | haber, haver, credit |
| `saldo` | saldo, balanç, balance |
| `tercero` | descripción, tercero, cliente, proveedor, nom |
| `documento` | documento, factura, invoice, doc |
| `concepto` | concepto, glosa, detalle, descripció |
| `punt` | punt, punteado, check, conciliado |

**Fallback Schema** (positional):

| Position | Column |
|----------|--------|
| 0 | Cuenta |
| 1 | Tercero |
| 2 | Punt. |
| 3 | Fecha |
| 4 | Concepto |
| 5 | Documento |
| 6 | Debe |
| 7 | Haber |
| 8 | Saldo |

### Detail Row Structure

```json
{
  "SetID": 0,
  "Tercero": "ACME Corp",
  "Fecha_doc": "2025-01-15",
  "Fecha_pago": "2025-01-20",
  "DocKey": "ACME Corp | INV-001 | 4300 | +1500.00",
  "PagoKey": "ACME Corp | CHK-001 | 4300 | -1500.00",
  "Asignado": 1500.00,
  "ResidualFacturaTras": 0.00,
  "MatchMethod": "Exact",
  "Confidence": 90.0,
  "Cuenta_doc": "4300",
  "Documento_doc": "INV-001",
  "Concepto_doc": "Invoice for services",
  "Cuenta_pago": "4300",
  "Documento_pago": "CHK-001",
  "Concepto_pago": "Check payment"
}
```

### Pending Row Structure

```json
{
  "Tercero": "XYZ Ltd",
  "DocKey": "XYZ Ltd | INV-005 | 4300 | +2000.00",
  "ImportePendiente": 500.00,
  "Fecha": "2025-01-10",
  "Dias": 25
}
```

### Justification Options

```javascript
const JUSTIFICATION_OPTIONS = [
  { value: 'previous_quarter', label: 'Factura trimestre anterior' },
  { value: 'next_quarter', label: 'Factura trimestre siguiente' },
  { value: 'advance_payment', label: 'Pago anticipado' },
  { value: 'credit_note', label: 'Nota de crédito' },
  { value: 'other', label: 'Otro' }
];
```

---

## Frontend Components

### Color Scheme

```css
:root {
  --color-accent-blue: #3B82F6;
  --color-accent-green: #10B981;
  --color-accent-purple: #A855F7;
  --color-accent-red: #EF4444;
  --color-accent-orange: #F59E0B;
}
```

### Status Colors

| Status | Color | Condition |
|--------|-------|-----------|
| Totalmente Pagado | Green `#10B981` | All invoices fully paid |
| Pago Parcial | Orange `#F59E0B` | Residual > 0.01 |
| Sin Factura | Red `#EF4444` | Unmatched payment |
| Justificado | Green `#10B981` | Unmatched + justified |
| Pre-Conciliado | Blue `#3B82F6` | From input `Punt.` column |

### Match Method Badges

| Method | Icon | Color |
|--------|------|-------|
| Reference | 🔗 | Green |
| Exact | 💯 | Green |
| CombinedAmount | ➕ | Green |
| DateProximity | 📅 | Purple |
| FIFO | ⏰ | Purple |
| Unallocated | ❌ | Red |
| PreReconciled | ✓ | Blue |

### Aging Colors (Pending List)

| Days Outstanding | Color |
|------------------|-------|
| < 60 | Green |
| 60-90 | Orange |
| > 90 | Red |

---

## Configuration

### Current Settings

| Setting | Location | Default |
|---------|----------|---------|
| API URL | `frontend/src/api.js` | `https://conciliador-awct.onrender.com` |
| AR Prefix | User input | `43` |
| AP Prefix | User input | `40` |
| Tolerance | User input | `0.01` |
| CORS | `backend/main.py` | `["*"]` |

### Deployment (Render.com)

**Current Setup:**

| Service | Type | Directory |
|---------|------|-----------|
| Backend | Web Service | `backend/` |
| Frontend | Static Site | `frontend/` |

**SaaS Setup (`render.yaml` - Infrastructure as Code):**

```yaml
# render.yaml - Place at repository root
services:
  # Frontend
  - type: web
    name: conciliador-frontend
    env: static
    rootDir: frontend
    buildCommand: npm install && npm run build
    staticPublishPath: dist
    headers:
      - path: /*
        name: Cache-Control
        value: public, max-age=31536000
    routes:
      - type: rewrite
        source: /*
        destination: /index.html

  # API Backend
  - type: web
    name: conciliador-api
    env: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: conciliador-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: conciliador-redis
          type: redis
          property: connectionString
      - key: ENVIRONMENT
        value: production
      - key: CORS_ORIGINS
        sync: false  # Set manually per environment

  # Background Worker (Celery)
  - type: worker
    name: conciliador-worker
    env: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A tasks worker --loglevel=info
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: conciliador-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: conciliador-redis
          type: redis
          property: connectionString

databases:
  - name: conciliador-db
    plan: starter  # $7/month, 1GB storage
    postgresMajorVersion: 16

# Redis for job queue and caching
  - type: redis
    name: conciliador-redis
    plan: starter  # $10/month, 25MB
    maxmemoryPolicy: allkeys-lru
```

**Environment Variables (to configure manually):**

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key | `openssl rand -hex 32` |
| `STRIPE_SECRET_KEY` | Stripe API key | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing | `whsec_...` |
| `R2_ACCESS_KEY` | Cloudflare R2 access | From R2 dashboard |
| `R2_SECRET_KEY` | Cloudflare R2 secret | From R2 dashboard |
| `R2_BUCKET` | R2 bucket name | `conciliador-files` |
| `SENTRY_DSN` | Error tracking | From Sentry |
| `CLERK_SECRET_KEY` | Auth provider | From Clerk |

---

## Development Guidelines

### Design Principles

1. **Functionality > Aesthetics**: Clear data presentation over visual polish
2. **Information Density**: Show all critical fields without scrolling
3. **Status at a Glance**: Color coding instantly understandable
4. **Human Control**: Surface problems, don't hide them
5. **Audit Trail**: Document all decisions

### Adding New Match Methods

1. Add phase in `Reconciler.process_payment()` before FIFO
2. Assign unique `MatchMethod` string
3. Calculate appropriate confidence (consider date, amount, source)
4. Update frontend badge in `App.jsx` `MatchesList`
5. Add explanation to `HelpModal.jsx`

### Modifying Column Detection

1. Edit patterns in `detect_schema()` (`reconciliation.py`)
2. Test with diverse Excel formats
3. Ensure fallback schema still works
4. Add detected columns to `Meta` sheet for debugging

### Testing

```bash
# CLI testing
cd backend
python conciliador_fifo.py test_file.xlsx -o output.xlsx

# Check Meta sheet for detection diagnostics
# Verify SetID grouping (invoices + payments should balance)
```

---

## SaaS Conversion Roadmap

### Current Limitations

| Area | Current State | SaaS Requirement |
|------|---------------|------------------|
| **Auth** | None | Multi-tenant with roles |
| **Database** | None (stateless) | PostgreSQL + ORM |
| **Storage** | In-memory only | S3/Cloud Storage |
| **Config** | Hardcoded | Per-tenant settings |
| **Billing** | None | Subscription + usage |
| **Monitoring** | Basic CountAPI | Full observability |

### Phase 1: Foundation (Weeks 1-4)

#### 1.1 Authentication & Authorization

```python
# New file: backend/auth.py

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """Validate JWT token and return user info."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return {
            "user_id": payload["sub"],
            "tenant_id": payload["tenant_id"],
            "role": payload["role"]
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
```

**Implementation:**
- [ ] JWT-based authentication
- [ ] OAuth2 providers (Google, Microsoft)
- [ ] Role-based access control (Admin, Accountant, Viewer)
- [ ] API key authentication for programmatic access

#### 1.2 Database Schema

```sql
-- Core multi-tenant schema

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'free',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'accountant',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE reconciliations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    company_name VARCHAR(255),
    period VARCHAR(50),
    filename VARCHAR(255),
    ar_total DECIMAL(15,2),
    ap_total DECIMAL(15,2),
    pending_ar INTEGER,
    pending_ap INTEGER,
    status VARCHAR(50) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE reconciliation_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_id UUID REFERENCES reconciliations(id),
    file_type VARCHAR(50), -- 'input' or 'output'
    storage_key VARCHAR(500),
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE justifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reconciliation_id UUID REFERENCES reconciliations(id),
    user_id UUID REFERENCES users(id),
    set_id INTEGER,
    pago_key TEXT,
    reason VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Row-level security
ALTER TABLE reconciliations ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON reconciliations
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
```

**Implementation:**
- [ ] SQLAlchemy ORM models
- [ ] Alembic migrations
- [ ] Row-level security for tenant isolation
- [ ] Connection pooling

#### 1.3 File Storage

```python
# New file: backend/storage.py

import boto3
from botocore.config import Config

class S3Storage:
    def __init__(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket = settings.S3_BUCKET

    async def upload_file(
        self,
        tenant_id: str,
        file_id: str,
        content: bytes,
        content_type: str = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ) -> str:
        """Upload file to S3 with tenant isolation."""
        key = f"{tenant_id}/{file_id}.xlsx"
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type
        )
        return key

    async def get_download_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate pre-signed URL for download."""
        return self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': key},
            ExpiresIn=expires_in
        )
```

**Implementation:**
- [ ] S3 bucket per environment
- [ ] Tenant-prefixed storage keys
- [ ] Pre-signed URLs for secure downloads
- [ ] Automatic cleanup of old files

### Phase 2: Multi-Tenancy (Weeks 5-8)

#### 2.1 Tenant Configuration

```python
# New file: backend/models/tenant.py

from sqlalchemy import Column, String, JSON
from sqlalchemy.dialects.postgresql import UUID

class Tenant(Base):
    __tablename__ = 'tenants'

    id = Column(UUID, primary_key=True)
    name = Column(String(255))
    slug = Column(String(100), unique=True)
    plan = Column(String(50), default='free')
    settings = Column(JSON, default={
        'ar_prefix': '43',
        'ap_prefix': '40',
        'default_tolerance': 0.01,
        'schema_mappings': {},
        'branding': {
            'logo_url': None,
            'primary_color': '#3B82F6'
        }
    })
```

**Per-Tenant Features:**
- [ ] Custom account prefixes
- [ ] Custom schema mappings
- [ ] Custom branding (logo, colors)
- [ ] Custom report templates

#### 2.2 API Updates

```python
# Updated main.py

@app.post("/api/v1/conciliate")
async def conciliate(
    file: UploadFile,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant = await get_tenant(db, current_user["tenant_id"])

    # Apply tenant settings
    settings = tenant.settings
    ar_prefix = settings.get('ar_prefix', '43')
    ap_prefix = settings.get('ap_prefix', '40')
    tolerance = settings.get('default_tolerance', 0.01)

    # Process reconciliation
    result = await process_reconciliation(
        file, ar_prefix, ap_prefix, tolerance
    )

    # Store in database
    reconciliation = Reconciliation(
        tenant_id=tenant.id,
        user_id=current_user["user_id"],
        **result
    )
    db.add(reconciliation)
    db.commit()

    return result
```

### Phase 3: Async Processing (Weeks 9-12)

#### 3.1 Job Queue

```python
# New file: backend/tasks.py

from celery import Celery
from celery.result import AsyncResult

celery = Celery(
    'conciliador',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

@celery.task(bind=True)
def process_reconciliation_task(
    self,
    file_key: str,
    tenant_id: str,
    user_id: str,
    settings: dict
):
    """Background task for large file processing."""
    try:
        # Download file from S3
        file_content = storage.download_file(file_key)

        # Process
        result = generate_reconciliation_data(
            file_content,
            **settings
        )

        # Upload output
        output_key = storage.upload_file(
            tenant_id,
            f"{self.request.id}_output",
            result['excel']
        )

        # Update database
        update_reconciliation_status(
            self.request.id,
            status='completed',
            output_key=output_key
        )

        # Send webhook/notification
        notify_completion(tenant_id, user_id, self.request.id)

        return {'status': 'completed', 'output_key': output_key}

    except Exception as e:
        update_reconciliation_status(
            self.request.id,
            status='failed',
            error=str(e)
        )
        raise
```

**Implementation:**
- [ ] Celery + Redis job queue
- [ ] Webhook callbacks on completion
- [ ] Progress tracking for large files
- [ ] Retry logic with exponential backoff

#### 3.2 Updated API for Async

```python
@app.post("/api/v1/conciliate/async")
async def conciliate_async(
    file: UploadFile,
    webhook_url: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Start async reconciliation job."""

    # Upload to temporary storage
    file_key = await storage.upload_file(
        current_user["tenant_id"],
        f"temp_{uuid4()}",
        await file.read()
    )

    # Queue task
    task = process_reconciliation_task.delay(
        file_key=file_key,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        settings=get_tenant_settings(current_user["tenant_id"])
    )

    return {
        "job_id": task.id,
        "status": "processing",
        "status_url": f"/api/v1/jobs/{task.id}"
    }

@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Check job status."""
    result = AsyncResult(job_id)
    return {
        "job_id": job_id,
        "status": result.status,
        "result": result.result if result.ready() else None
    }
```

### Phase 4: Billing & Subscriptions (Weeks 13-16)

#### 4.1 Subscription Plans

```python
PLANS = {
    'free': {
        'name': 'Free',
        'price_monthly': 0,
        'limits': {
            'reconciliations_per_month': 5,
            'rows_per_file': 1000,
            'storage_mb': 100,
            'users': 1
        }
    },
    'professional': {
        'name': 'Professional',
        'price_monthly': 29,
        'limits': {
            'reconciliations_per_month': 100,
            'rows_per_file': 50000,
            'storage_mb': 5000,
            'users': 5
        }
    },
    'enterprise': {
        'name': 'Enterprise',
        'price_monthly': 99,
        'limits': {
            'reconciliations_per_month': -1,  # Unlimited
            'rows_per_file': -1,
            'storage_mb': 50000,
            'users': -1
        }
    }
}
```

#### 4.2 Stripe Integration

```python
# New file: backend/billing.py

import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

async def create_subscription(
    tenant_id: str,
    plan: str,
    payment_method_id: str
):
    """Create Stripe subscription for tenant."""
    tenant = await get_tenant(tenant_id)

    # Create or get Stripe customer
    if not tenant.stripe_customer_id:
        customer = stripe.Customer.create(
            email=tenant.billing_email,
            name=tenant.name
        )
        tenant.stripe_customer_id = customer.id

    # Attach payment method
    stripe.PaymentMethod.attach(
        payment_method_id,
        customer=tenant.stripe_customer_id
    )

    # Create subscription
    subscription = stripe.Subscription.create(
        customer=tenant.stripe_customer_id,
        items=[{'price': STRIPE_PRICES[plan]}],
        default_payment_method=payment_method_id
    )

    # Update tenant
    tenant.plan = plan
    tenant.stripe_subscription_id = subscription.id
    await save_tenant(tenant)

    return subscription
```

### Phase 5: Monitoring & Observability (Weeks 17-20)

#### 5.1 Logging

```python
# New file: backend/logging_config.py

import structlog
from opentelemetry import trace

def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory()
    )

# Usage in reconciliation.py
logger = structlog.get_logger()

def reconcile_fifo(df, tol):
    logger.info(
        "reconciliation_started",
        rows=len(df),
        tolerance=tol
    )
    # ...
    logger.info(
        "reconciliation_completed",
        matched=matched_count,
        unmatched=unmatched_count,
        duration_ms=duration
    )
```

#### 5.2 Metrics (Render + Custom)

Render provides built-in metrics for CPU, memory, and request latency. For business metrics:

```python
# New file: backend/metrics.py

import structlog
from datetime import datetime

logger = structlog.get_logger()

class MetricsCollector:
    """Custom metrics stored in PostgreSQL for analytics."""

    async def record_reconciliation(
        self,
        db: Session,
        tenant_id: str,
        rows: int,
        duration_ms: float,
        status: str
    ):
        """Record reconciliation metrics."""
        metric = ReconciliationMetric(
            tenant_id=tenant_id,
            rows_processed=rows,
            duration_ms=duration_ms,
            status=status,
            created_at=datetime.utcnow()
        )
        db.add(metric)

        # Also log for Render's log aggregation
        logger.info(
            "reconciliation_completed",
            tenant_id=tenant_id,
            rows=rows,
            duration_ms=duration_ms,
            status=status
        )

# Dashboard queries
async def get_tenant_usage(db: Session, tenant_id: str, period: str):
    """Get usage stats for billing."""
    return db.execute("""
        SELECT
            COUNT(*) as total_reconciliations,
            SUM(rows_processed) as total_rows,
            AVG(duration_ms) as avg_duration
        FROM reconciliation_metrics
        WHERE tenant_id = :tenant_id
        AND created_at >= NOW() - INTERVAL :period
    """, {"tenant_id": tenant_id, "period": period})
```

#### 5.3 Error Tracking (Sentry)

```python
# backend/sentry_config.py

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

def init_sentry():
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            CeleryIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
        # Add tenant context to errors
        before_send=add_tenant_context
    )

def add_tenant_context(event, hint):
    """Add tenant info to Sentry events."""
    if hasattr(g, 'tenant_id'):
        event['tags']['tenant_id'] = g.tenant_id
    return event
```

### Architecture Evolution (Render.com)

```
┌─────────────────────────────────────────────────────────────────┐
│                        RENDER.COM                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ Static Site  │    │ Web Service  │    │ Background   │       │
│  │   Frontend   │───▶│   FastAPI    │◀──▶│   Worker     │       │
│  │ React + Vite │    │  API + Auth  │    │   Celery     │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                              │                   │               │
│                              │                   │               │
│                    ┌─────────┴───────────────────┘               │
│                    │                                             │
│          ┌─────────┼─────────┐                                  │
│          ▼         ▼         ▼                                  │
│  ┌────────────┐ ┌────────┐ ┌────────────────┐                   │
│  │ PostgreSQL │ │ Redis  │ │ Persistent Disk│                   │
│  │  Managed   │ │Managed │ │  (temp files)  │                   │
│  └────────────┘ └────────┘ └────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Cloudflare R2  │
                    │  (File Storage) │
                    └─────────────────┘
```

### Implementation Checklist

#### Phase 1: Foundation
- [ ] Set up Render PostgreSQL database
- [ ] Create SQLAlchemy models
- [ ] Implement JWT authentication
- [ ] Add OAuth2 providers (Google, Microsoft)
- [ ] Set up Cloudflare R2 file storage
- [ ] Create basic tenant CRUD

#### Phase 2: Multi-Tenancy
- [ ] Implement row-level security
- [ ] Add per-tenant configuration
- [ ] Update API for tenant isolation
- [ ] Add custom branding support
- [ ] Implement schema template system

#### Phase 3: Async Processing
- [ ] Set up Render Redis + Celery worker
- [ ] Implement job queue
- [ ] Add webhook notifications
- [ ] Create job status API
- [ ] Add progress tracking

#### Phase 4: Billing
- [ ] Integrate Stripe
- [ ] Implement subscription management
- [ ] Add usage tracking
- [ ] Create billing portal
- [ ] Implement usage limits

#### Phase 5: Observability
- [ ] Configure structured logging (JSON format)
- [ ] Enable Render Metrics dashboard
- [ ] Integrate Sentry for error tracking
- [ ] Create admin dashboard (tenant management)
- [ ] Add usage analytics per tenant

### Recommended Tech Stack for SaaS (Render.com)

| Component | Recommendation | Alternative |
|-----------|----------------|-------------|
| **Hosting** | Render.com (all-in-one) | Railway, Fly.io |
| **Database** | Render PostgreSQL | Neon, Supabase |
| **Cache/Queue** | Render Redis | Upstash |
| **Auth** | Clerk | Auth0, custom JWT |
| **Storage** | Cloudflare R2 | AWS S3, Backblaze B2 |
| **Billing** | Stripe | Paddle |
| **Monitoring** | Sentry + Render Metrics | Datadog |
| **Frontend** | Render Static Site | (ja inclòs) |

### Render.com Pricing Estimate (SaaS)

| Service | Plan | Monthly Cost |
|---------|------|--------------|
| Static Site (Frontend) | Free | $0 |
| Web Service (API) | Starter | $7 |
| Background Worker | Starter | $7 |
| PostgreSQL | Starter (1GB) | $7 |
| Redis | Starter (25MB) | $10 |
| **Total base** | | **$31/month** |

**Scaling costs:**
- PostgreSQL Pro (64GB): $95/month
- Web Service Standard (4GB RAM): $25/month
- Additional workers: $7-25/month each

### Pricing Strategy Recommendation

| Plan | Target | Price | Features |
|------|--------|-------|----------|
| **Free** | Trial users | €0/mo | 5 reconciliations, 1000 rows |
| **Starter** | Freelancers | €19/mo | 50 reconciliations, 10K rows |
| **Professional** | Small firms | €49/mo | Unlimited, 50K rows, 5 users |
| **Enterprise** | Large firms | €149/mo | Unlimited, API access, SSO |

### Revenue Projections

Based on Assessoria Egara's network:
- 50 potential customers × €49/mo = €2,450 MRR
- With enterprise clients: €5,000-10,000 MRR potential

---

## Appendix

### Glossary

| Term | Description |
|------|-------------|
| **Tercero** | Third party (customer or supplier) |
| **AR (Clientes)** | Accounts Receivable |
| **AP (Proveedores)** | Accounts Payable |
| **SetID** | Group identifier for related transactions |
| **DocKey** | Unique identifier: `Tercero \| Doc \| Account \| Amount` |
| **Residual** | Remaining balance after partial payment |
| **Punt.** | Pre-reconciled indicator column |

### Error Codes

| Code | Description |
|------|-------------|
| `INVALID_FILE` | Not a valid Excel file |
| `NO_HEADER` | Could not detect header row |
| `NO_DATA` | No data rows found |
| `SCHEMA_ERROR` | Required columns not found |

### Support

- GitHub Issues: https://github.com/[repo]/issues
- Documentation: [Coming with SaaS]
- Email: [Coming with SaaS]
