# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Conciliador** is a tool designed to help accounting professionals at Assessoria Egara identify and control unmatched financial movements. It uses a **3-phase Waterfall Reconciliation** algorithm (Reference → Exact Amount → FIFO) to automatically match invoices with payments in AR (Accounts Receivable/Clientes) and AP (Accounts Payable/Proveedores) accounts.

### Primary Purpose: Human Control of Uncontrolled Movements

This tool exists to **assist humans in their work of controlling movements that are not automatically matched**. The reconciliation algorithm handles routine matches, but the real value lies in surfacing problematic cases for human review:

- **Unmatched payments** (payments without corresponding invoices)
- **Partial payments** (invoices not fully paid)
- **Aged receivables/payables** (pending invoices by days outstanding)

The interface prioritizes **functionality and understanding of complex data** over aesthetics. Every design decision should serve the goal of making it easier for accounting professionals to:
1. Quickly identify problematic movements
2. Understand why a match was or wasn't made
3. Document decisions about unmatched items
4. Extract actionable insights for follow-up

## Tech Stack

- **Backend**: FastAPI (Python 3.10+) with Pandas, NumPy, OpenPyXL
- **Frontend**: React 19 + Vite (no TypeScript)
- **Deployment**: Render.com (backend web service + frontend static site)

## Common Commands

### Backend Development
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
npm run build
npm run lint
```

### Command-line Processing
```bash
cd backend
python conciliador_fifo.py <input.xlsx> [-o output.xlsx] [--sheet SHEET_NAME] [--ar-prefix 43] [--ap-prefix 40] [--tol 0.01]
```

## Architecture

### Backend Architecture (`backend/`)

**Core Reconciliation Engine** (`reconciliation.py`):
- `reconcile_fifo()`: Main waterfall reconciliation algorithm with 3 phases:
  1. **Reference Match**: Searches for invoice document numbers in payment concept field
  2. **Exact Amount Match**: Finds single invoice with exact remaining payment amount
  3. **FIFO Fallback**: Chronologically matches oldest invoices first
- `Reconciler` class: Maintains state of open invoices and processes payments row-by-row
- `detect_schema()`: Auto-detects column mappings from Excel headers (handles both labeled and positional columns)
- `find_header_row()`: Automatically locates the header row in Excel files with pre-header metadata
- `extract_company_name()`: Extracts company name from rows before the header for display
- `generate_reconciliation_data()`: Orchestrates the full pipeline (read → detect → reconcile → summarize)

**API Endpoint** (`main.py`):
- `POST /conciliate`: Accepts Excel file + parameters (tolerance, AR/AP prefixes), returns JSON summary + base64-encoded Excel
- CORS configured for local dev and production frontend

**Data Flow**:
1. Excel uploaded → Auto-detect header row and company name
2. Schema detection (account, date, debit/credit, document, concept columns)
3. Split by AR (prefix `43`) / AP (prefix `40`) accounts
4. Normalize amounts (AR: invoice>0, payment<0; AP: inverted signs)
5. Group by tercero (third party), sort chronologically
6. Apply waterfall reconciliation per tercero
7. Generate output sheets: `AR_Detalle`, `AP_Detalle`, `Pendientes_AR`, `Pendientes_AP`, `Resumen`, `Meta`

### Frontend Architecture (`frontend/src/`)

**Main Components**:
- `App.jsx`: Main application container with sidebar (settings + file upload) and main content area (results dashboard)
- `HelpModal.jsx`: Modal explaining the 3-phase reconciliation methodology
- `api.js`: Axios wrapper for backend API calls

**Key UI Features** (Designed for Functionality & Data Comprehension):

1. **Critical Information First**:
   - Color-coded status borders (🔴 Red = Unmatched, 🟠 Orange = Partial, 🟢 Green = OK/Justified)
   - Large, readable metrics dashboard showing AR/AP totals and pending counts
   - Immediate visual distinction between problematic and resolved cases

2. **Human Review & Documentation Tools**:
   - **Justification dropdowns**: Required workflow for unmatched payments to document human decisions
     - Options: Previous quarter invoice, Next quarter invoice, Advance payment, Credit note, Other
     - Visual feedback: Red → Green when justified (helps track review progress)
   - **Collapsible match cards**: Reduces cognitive load by showing only headers by default
   - **Detailed tables**: Show all relevant data (dates, documents, amounts, residuals) for informed decisions

3. **Data Exploration & Navigation**:
   - **Tab navigation**: Switch between AR/AP and Matches/Pending views to focus workflow
   - **Interactive tolerance slider**: Test different matching thresholds in real-time
   - **Sorting/filtering**: Pending items sorted by days outstanding (most urgent first)

4. **Visual Cues for Understanding Match Logic**:
   - **Match method badges**: Reference 🔗 | Exact 💯 | FIFO ⏰ (helps understand algorithm decisions)
   - **Dual date display**: Invoice date vs Payment date in matches (spot timing issues)
   - **Running residual amounts**: Shows invoice balance after each payment (trace partial payment chains)

**Design Philosophy**:
- **Functionality over aesthetics**: Visual design (glassmorphism, gradients) is secondary to clear data presentation
- **Information density**: Tables show all critical fields without scrolling when possible
- **Status at a glance**: Color coding must be instantly understandable (red = action needed, green = resolved)
- **Preserve user work**: Justifications persist in state during session (consider adding export/persistence)

**State Management**:
- Local state with React hooks (no external state library)
- `justifications` state: Tracks user-provided explanations for unmatched payments (critical workflow data)
- Real-time recalculation on tolerance change (allows testing without re-upload)

### Reconciliation Output Format

The output is designed to support human review and decision-making:

**Detail Sheets** (`AR_Detalle`, `AP_Detalle`) - For Investigating Matches:
- `SetID`: Groups related invoices/payments (increments when no open invoices remain)
- `Tercero`: Third party (customer/supplier) - **Primary grouping for human review**
- `Fecha_doc` / `Fecha_pago`: Invoice/payment dates - **Spot timing mismatches**
- `DocKey` / `PagoKey`: Composite keys (tercero | document | account | amount) - **Unique identifiers**
- `Asignado`: Amount allocated in this match - **Negative values indicate unmatched payments requiring justification**
- `ResidualFacturaTras`: Invoice balance after this payment - **Positive values show partial payments needing follow-up**
- `MatchMethod`: Reference | Exact | FIFO | Unallocated | Open - **Understand how/why the match was made**

**Pending Sheets** (`Pendientes_AR`, `Pendientes_AP`) - For Priority Follow-up:
- Outstanding invoices with `ImportePendiente` > tolerance
- `Dias`: Days since invoice date - **Sorted by urgency for collection/payment prioritization**
- Color-coded by aging: 🟢 < 60 days, 🟠 60-90 days, 🔴 > 90 days

## Important Implementation Details

### Excel Schema Detection
- **Header Row Detection**: Scans first 30 rows for keywords (fecha, cuenta, debe, haber) to locate header
- **Column Mapping**: Uses regex patterns to find columns (flexible for different accounting systems)
- **Fallback Schema**: If headers not found, assumes positional columns (cuenta, tercero, fecha, concepto, documento, debe, haber, saldo)

### Account Classification
- **AR (Clientes)**: Accounts starting with prefix `43` (default, configurable)
- **AP (Proveedores)**: Accounts starting with prefix `40` (default, configurable)
- Sign normalization ensures invoices are always positive, payments negative in internal processing

### Tolerance Handling
- Default: `0.01` (1 cent)
- Used for floating-point comparisons (`remaining > tol` checks)
- Interactive slider in frontend allows real-time adjustment

### FIFO Logic
- Invoices and payments must be sorted by date (`fecha`) before processing
- Within each tercero, open invoices are maintained in chronological order
- FIFO only applies after Reference and Exact match phases fail

### JSON Serialization
- All Pandas/NumPy types sanitized to native Python types
- `NaT`/`NaN`/`Inf` → `None`
- Datetime columns → ISO string format (`YYYY-MM-DD`)

## Development Guidelines

### Core Principle: Functionality Enables Human Control

When making changes, always ask: **"Does this help users identify and understand uncontrolled movements faster?"**

### Adding New Match Methods
1. Add phase in `Reconciler.process_payment()` before FIFO fallback
2. Assign unique `MatchMethod` string
3. Update frontend badge rendering in `App.jsx` (MatchesList component)
4. **Critical**: Ensure the method name is immediately understandable to accounting professionals
5. Add explanation to `HelpModal.jsx` if method is non-obvious

### Improving Data Visibility
When adding UI features:
- **Prioritize information density**: Show more data rather than hiding it behind clicks
- **Use color meaningfully**: Red = requires action, Orange = warning/partial, Green = resolved/OK
- **Make status instantly clear**: Users should know if something needs attention within 1 second of viewing
- **Provide context**: Always show enough data for the user to make an informed decision without switching screens

### Modifying Column Detection
- Edit patterns in `detect_schema()` (`reconciliation.py`)
- Test with diverse Excel formats from real accounting software
- Ensure fallback schema still works for headless exports
- **Critical**: Add detected columns to `Meta` sheet so users can verify correct mapping

### Styling Changes
- CSS-in-JS used throughout frontend (no external CSS files)
- Color variables: `--color-accent-blue`, `--color-accent-green`, etc.
- Match method colors: Reference/Exact (green), FIFO (purple), Unallocated (red)
- **Design priority order**:
  1. Data clarity and readability
  2. Visual hierarchy (important info bigger/bolder)
  3. Aesthetic appeal (gradients, shadows, etc.)

### Testing with Real Data
- Use `conciliador_fifo.py` CLI for quick batch testing
- Check `Meta` sheet in output Excel for detection diagnostics
- Verify `SetID` grouping makes logical sense (invoices + payments = 0)
- **User testing**: Watch accounting professionals use the tool - where do they get confused? What do they need to click multiple times to understand?

### Adding Human Review Features
Consider these enhancements for better human control:
- Export justifications to Excel or PDF for audit trail
- Filter/search within matches (e.g., "show only unjustified payments")
- Notes field for complex cases requiring explanation
- History of tolerance adjustments and their effects
- Bulk operations for justifying similar cases

## Deployment Notes

- **Backend**: Render web service with `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Frontend**: Render static site, build outputs to `frontend/dist`
- **API URL**: Hardcoded in `frontend/src/api.js` as `https://conciliador-awct.onrender.com`
- **CORS**: Configured in `backend/main.py` to allow all origins (`"*"`)

## File Structure Notes

- `backend/temp.py`: Unused/temporary file (can be ignored)
- `frontend/src/HelpModal.jsx`: Self-contained modal, references 3-phase methodology
- No TypeScript: All frontend code is plain JavaScript/JSX
