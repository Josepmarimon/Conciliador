# Plan: Sistema de Histórico Multi-Trimestre con Encadenamiento de Facturas

**Versión:** 1.0
**Fecha:** 25 Noviembre 2025
**Estado:** Pendiente de Implementación

---

## 📋 Resumen Ejecutivo

Este documento describe la planificación completa para implementar un **sistema de histórico** que permita:

1. **Guardar reconciliaciones** de múltiples trimestres/períodos por empresa
2. **Encadenar facturas pendientes** entre períodos (ej: factura Q1 → se paga en Q2)
3. **Visualizar evolución temporal** de pagos y pendientes por empresa
4. **Detectar patrones** de pago recurrentes para mejor control

---

## 🎯 Problema Actual

**Situación:**
- Cada reconciliación es **independiente** (stateless)
- Facturas pendientes de Q1 2025 **no se arrastran** automáticamente a Q2 2025
- **No hay visibilidad histórica** de la evolución de pagos por empresa
- Imposible detectar patrones (ej: cliente que siempre paga en trimestre siguiente)

**Ejemplos Reales del Sistema:**
```
Archivo: MAYOR ALBA 1T 2025 SUMRRASSA, SL.xlsx
→ Resultado: 3 facturas pendientes (total: 5.200€)

Archivo: MAYOR ALBA 2T 2025 SUMRRASSA, SL.xlsx  ← Este trimestre aún no procesado
→ Problema: Las 3 facturas pendientes de Q1 NO aparecen
→ Solución: Sistema histórico las inyecta automáticamente
```

---

## 🏗️ Arquitectura Propuesta

### 1. Base de Datos

**Tecnología Recomendada:**
- **Desarrollo/Testing:** SQLite (sin configuración, archivo local)
- **Producción:** PostgreSQL (escalable, multi-usuario)

**Esquema de Tablas:**

```sql
-- 1. EMPRESAS (maestro)
CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,              -- "ALTO OCTANAJE 108, SL"
    normalized_name TEXT NOT NULL,          -- "altooctanaje108sl" (búsqueda)
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_reconciliation_date TIMESTAMP
);

-- 2. RECONCILIACIONES (histórico de procesos)
CREATE TABLE reconciliations (
    id INTEGER PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    period_quarter INTEGER NOT NULL,        -- 1, 2, 3, 4
    period_year INTEGER NOT NULL,           -- 2025
    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    original_filename TEXT,
    excel_output_path TEXT,                 -- Ruta al Excel generado

    -- Métricas del proceso
    total_ar_reconciled DECIMAL(10,2),
    total_ap_reconciled DECIMAL(10,2),
    num_pending_ar INTEGER,
    num_pending_ap INTEGER,

    metadata JSON,                          -- Info adicional flexible

    UNIQUE(company_id, period_quarter, period_year)
);

-- 3. FACTURAS PENDIENTES (arrastre entre períodos)
CREATE TABLE pending_invoices (
    id INTEGER PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id),
    reconciliation_id INTEGER REFERENCES reconciliations(id), -- Donde se originó

    -- Identificación de factura
    doc_key TEXT NOT NULL,                  -- Clave única (tercero|doc|cuenta|importe)
    invoice_date DATE,
    account_type TEXT,                      -- "AR" o "AP"
    tercero TEXT,

    -- Estado financiero
    original_amount DECIMAL(10,2),
    amount_pending DECIMAL(10,2),
    days_outstanding INTEGER,

    -- Trazabilidad
    origin_period TEXT,                     -- "Q1 2025"
    current_status TEXT,                    -- "pending", "paid_later", "written_off"
    resolution_reconciliation_id INTEGER,   -- ID que la resolvió (NULL si aún pendiente)
    resolution_date TIMESTAMP,

    -- Índices para búsquedas rápidas
    INDEX idx_company_status (company_id, current_status),
    INDEX idx_doc_key (doc_key)
);

-- 4. JUSTIFICACIONES (persistencia de decisiones humanas)
CREATE TABLE justifications (
    id INTEGER PRIMARY KEY,
    reconciliation_id INTEGER REFERENCES reconciliations(id),
    row_key TEXT NOT NULL,                  -- "SetID-PagoKey"
    justification_type TEXT,                -- "prev_quarter", "advance_payment", etc.
    notes TEXT,                             -- Notas adicionales del usuario
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT                         -- Usuario (futuro: multi-usuario)
);

-- 5. MATCH_HISTORY (auditoría de emparejamientos)
CREATE TABLE match_history (
    id INTEGER PRIMARY KEY,
    reconciliation_id INTEGER REFERENCES reconciliations(id),
    doc_key TEXT,
    pago_key TEXT,
    match_method TEXT,                      -- "Reference", "Exact", "DateProximity", etc.
    confidence DECIMAL(5,2),                -- 0-100
    amount_matched DECIMAL(10,2),
    match_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔄 Lógica de Encadenamiento

### Flujo al Procesar Nuevo Período

```python
def reconcile_with_history(
    file_content: bytes,
    company_id: int,
    period_quarter: int,
    period_year: int,
    tol: float,
    ar_prefix: str,
    ap_prefix: str
):
    """
    Procesa reconciliación con contexto histórico
    """

    # ═══════════════════════════════════════════════════════════
    # PASO 1: Cargar Facturas Pendientes de Períodos Anteriores
    # ═══════════════════════════════════════════════════════════
    previous_pending = db.get_pending_invoices(
        company_id=company_id,
        before_period=(period_quarter, period_year),
        status="pending"
    )

    print(f"📦 Cargadas {len(previous_pending)} facturas pendientes de períodos anteriores")

    # ═══════════════════════════════════════════════════════════
    # PASO 2: Procesar Excel Normal + Inyectar Facturas Previas
    # ═══════════════════════════════════════════════════════════

    # Procesar Excel normalmente
    out_sheets, summary, company_name = generate_reconciliation_data(
        file_content, tol, ar_prefix, ap_prefix
    )

    # Inyectar facturas pendientes en las hojas de detalle
    for sheet_name in ["AR_Detalle", "AP_Detalle"]:
        if sheet_name not in out_sheets:
            continue

        df = out_sheets[sheet_name]
        account_type = "AR" if "AR" in sheet_name else "AP"

        # Filtrar facturas pendientes de este tipo de cuenta
        pending_for_type = [
            p for p in previous_pending
            if p.account_type == account_type
        ]

        # Crear filas de "arrastre"
        carryforward_rows = []
        for pending in pending_for_type:
            carryforward_rows.append({
                "SetID": -1,  # ID especial para arrastres
                "Tercero": pending.tercero,
                "Fecha_doc": pending.invoice_date,
                "Fecha_pago": None,
                "DocKey": pending.doc_key,
                "PagoKey": None,
                "Asignado": 0.0,
                "ResidualFacturaTras": pending.amount_pending,
                "Hoja_doc": f"⬅️ Arrastre {pending.origin_period}",
                "Hoja_pago": None,
                "MatchMethod": "Carryforward",
                "Confidence": 0,
                "DaysOutstanding": pending.days_outstanding
            })

        # Añadir al inicio del DataFrame
        if carryforward_rows:
            df_carryforward = pd.DataFrame(carryforward_rows)
            out_sheets[sheet_name] = pd.concat([df_carryforward, df], ignore_index=True)

    # ═══════════════════════════════════════════════════════════
    # PASO 3: Identificar Facturas Previas que se Resolvieron
    # ═══════════════════════════════════════════════════════════

    resolved_docs = set()
    for sheet_name in ["AR_Detalle", "AP_Detalle"]:
        df = out_sheets[sheet_name]
        # Facturas que tienen pago (PagoKey no nulo) y saldo bajo
        resolved = df[
            (df["PagoKey"].notna()) &
            (df["ResidualFacturaTras"] < tol)
        ]["DocKey"].unique()
        resolved_docs.update(resolved)

    # Marcar como resueltas en BD
    for pending in previous_pending:
        if pending.doc_key in resolved_docs:
            db.update_pending_invoice_status(
                invoice_id=pending.id,
                status="paid_later",
                resolution_reconciliation_id=new_reconciliation_id
            )
            print(f"✅ Factura {pending.doc_key} resuelta en este período")

    # ═══════════════════════════════════════════════════════════
    # PASO 4: Guardar Nuevas Facturas Pendientes
    # ═══════════════════════════════════════════════════════════

    new_pending_invoices = []
    for sheet_name in ["AR_Detalle", "AP_Detalle"]:
        df = out_sheets[sheet_name]
        account_type = "AR" if "AR" in sheet_name else "AP"

        # Facturas con saldo pendiente
        pending = df[df["ResidualFacturaTras"] > tol]

        for _, row in pending.iterrows():
            if row["MatchMethod"] == "Carryforward":
                continue  # Ya está en BD

            new_pending_invoices.append({
                "company_id": company_id,
                "reconciliation_id": new_reconciliation_id,
                "doc_key": row["DocKey"],
                "invoice_date": row["Fecha_doc"],
                "account_type": account_type,
                "tercero": row["Tercero"],
                "original_amount": row["ResidualFacturaTras"],  # Simplificado
                "amount_pending": row["ResidualFacturaTras"],
                "origin_period": f"Q{period_quarter} {period_year}",
                "current_status": "pending"
            })

    db.save_pending_invoices(new_pending_invoices)

    # ═══════════════════════════════════════════════════════════
    # PASO 5: Guardar Reconciliación en BD
    # ═══════════════════════════════════════════════════════════

    reconciliation_record = {
        "company_id": company_id,
        "period_quarter": period_quarter,
        "period_year": period_year,
        "original_filename": original_filename,
        "excel_output_path": output_path,
        "total_ar_reconciled": summary[0]["Asignado"],
        "total_ap_reconciled": summary[1]["Asignado"],
        "num_pending_ar": len(out_sheets.get("Pendientes_AR", [])),
        "num_pending_ap": len(out_sheets.get("Pendientes_AP", [])),
        "metadata": json.dumps(summary)
    }

    new_reconciliation_id = db.save_reconciliation(reconciliation_record)

    return out_sheets, summary, company_name
```

---

## 🖥️ Cambios en Backend (API)

### Nuevos Endpoints

```python
# ═══════════════════════════════════════════════════════════
# 1. GESTIÓN DE EMPRESAS
# ═══════════════════════════════════════════════════════════

@app.get("/api/companies")
async def list_companies():
    """
    Lista todas las empresas con histórico

    Response: [
        {
            "id": 1,
            "name": "ALTO OCTANAJE 108, SL",
            "reconciliations_count": 4,
            "last_reconciliation": "Q1 2025",
            "pending_invoices": 3,
            "total_pending_amount": 5200.00
        },
        ...
    ]
    """
    pass

@app.post("/api/companies")
async def create_company(name: str):
    """
    Crear nueva empresa manualmente
    """
    pass

@app.get("/api/companies/{id}/history")
async def get_company_history(id: int):
    """
    Histórico completo de reconciliaciones de una empresa

    Response: {
        "company": {...},
        "reconciliations": [
            {
                "id": 1,
                "period": "Q1 2025",
                "processed_date": "2025-03-15",
                "total_ar": 25000,
                "total_ap": 18000,
                "pending_count": 3
            },
            ...
        ]
    }
    """
    pass

# ═══════════════════════════════════════════════════════════
# 2. RECONCILIACIÓN CON HISTÓRICO
# ═══════════════════════════════════════════════════════════

@app.post("/api/conciliate")
async def conciliate_with_history(
    file: UploadFile,
    company_name: str = None,  # Nuevo: nombre empresa
    company_id: int = None,    # O ID si ya existe
    period_quarter: int = None,
    period_year: int = None,
    auto_detect_period: bool = True,  # Detectar de filename
    include_carryforward: bool = True, # Incluir facturas previas
    tol: float = 0.01,
    ar_prefix: str = "43",
    ap_prefix: str = "40",
    justifications: str = None
):
    """
    Procesar reconciliación con contexto histórico
    """

    # Auto-detectar período del filename si está habilitado
    if auto_detect_period and not (period_quarter and period_year):
        period_quarter, period_year = extract_period_from_filename(file.filename)

    # Auto-detectar empresa del Excel si no se especificó
    if not company_id and not company_name:
        company_name = extract_company_name_from_excel(file_content)

    # Buscar o crear empresa
    if company_id:
        company = db.get_company(company_id)
    else:
        company = db.get_or_create_company(company_name)

    # Procesar con histórico
    result = reconcile_with_history(
        file_content,
        company.id,
        period_quarter,
        period_year,
        ...
    )

    return {
        "company": company.to_dict(),
        "period": f"Q{period_quarter} {period_year}",
        "carryforward_count": len(previous_pending),
        "summary": summary,
        "details": details,
        "file_b64": b64_file
    }

# ═══════════════════════════════════════════════════════════
# 3. GESTIÓN DE PENDIENTES
# ═══════════════════════════════════════════════════════════

@app.get("/api/companies/{id}/pending")
async def get_pending_invoices(
    id: int,
    status: str = "pending",  # pending, paid_later, written_off
    min_days: int = None,     # Filtrar por días pendientes
    account_type: str = None  # AR, AP
):
    """
    Obtener facturas pendientes de una empresa
    """
    pass

@app.put("/api/pending/{invoice_id}/status")
async def update_pending_status(
    invoice_id: int,
    status: str,
    notes: str = None
):
    """
    Cambiar estado de factura pendiente
    (ej: marcar como "escrita off" manualmente)
    """
    pass
```

---

## 🎨 Cambios en Frontend (UI)

### 1. Nueva Sección: Gestión de Empresas

**Ubicación:** Sidebar izquierdo (antes de "Configuración")

```jsx
<aside>
  {/* Sección EMPRESAS */}
  <div className="companies-section">
    <h3>📁 Empresas</h3>

    {companies.map(company => (
      <div
        className="company-item"
        onClick={() => selectCompany(company.id)}
        style={{
          background: selectedCompany?.id === company.id ? 'rgba(10,132,255,0.2)' : 'transparent',
          padding: '0.75rem',
          borderRadius: '0.5rem',
          cursor: 'pointer'
        }}
      >
        <div style={{ fontWeight: '600' }}>{company.name}</div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {company.reconciliations_count} reconciliaciones
        </div>

        {company.pending_invoices > 0 && (
          <div style={{
            fontSize: '0.7rem',
            color: '#EF4444',
            marginTop: '0.25rem'
          }}>
            ⚠️ {company.pending_invoices} pendientes ({company.total_pending_amount}€)
          </div>
        )}
      </div>
    ))}

    <button onClick={() => setShowNewCompanyModal(true)}>
      + Nueva Empresa
    </button>
  </div>

  {/* Configuración, etc... */}
</aside>
```

### 2. Modal: Selección de Período al Subir Archivo

```jsx
function PeriodSelectionModal({ file, onSubmit, onCancel }) {
  const [quarter, setQuarter] = useState(null);
  const [year, setYear] = useState(new Date().getFullYear());
  const [autoDetected, setAutoDetected] = useState(null);

  useEffect(() => {
    // Auto-detectar de filename
    const detected = extractPeriodFromFilename(file.name);
    if (detected) {
      setAutoDetected(detected);
      setQuarter(detected.quarter);
      setYear(detected.year);
    }
  }, [file]);

  return (
    <div className="modal">
      <h2>Seleccionar Período</h2>

      {autoDetected && (
        <div className="auto-detected-notice">
          ✓ Detectado automáticamente: Q{autoDetected.quarter} {autoDetected.year}
        </div>
      )}

      <div className="period-selector">
        <label>Trimestre:</label>
        <select value={quarter} onChange={e => setQuarter(e.target.value)}>
          <option value="">Seleccionar...</option>
          <option value="1">Q1 (Ene-Mar)</option>
          <option value="2">Q2 (Abr-Jun)</option>
          <option value="3">Q3 (Jul-Sep)</option>
          <option value="4">Q4 (Oct-Dic)</option>
        </select>

        <label>Año:</label>
        <input type="number" value={year} onChange={e => setYear(e.target.value)} />
      </div>

      <button onClick={() => onSubmit(quarter, year)}>
        Continuar
      </button>
    </div>
  );
}
```

### 3. Vista: Facturas Arrastradas (Pre-Procesamiento)

```jsx
function CarryforwardPreview({ companyId, period, onConfirm, onCancel }) {
  const [pendingInvoices, setPendingInvoices] = useState([]);
  const [selectedInvoices, setSelectedInvoices] = useState(new Set());

  useEffect(() => {
    // Cargar facturas pendientes
    fetch(`/api/companies/${companyId}/pending?before_period=${period}`)
      .then(res => res.json())
      .then(data => {
        setPendingInvoices(data);
        // Por defecto, todas seleccionadas
        setSelectedInvoices(new Set(data.map(inv => inv.id)));
      });
  }, [companyId, period]);

  return (
    <div className="carryforward-preview">
      <h3>⬅️ Facturas Pendientes de Períodos Anteriores</h3>

      <p>
        Se encontraron <strong>{pendingInvoices.length} facturas pendientes</strong> que
        se incluirán en la reconciliación de {period}.
      </p>

      <table>
        <thead>
          <tr>
            <th>Incluir</th>
            <th>Origen</th>
            <th>Tercero</th>
            <th>DocKey</th>
            <th>Pendiente</th>
            <th>Días</th>
          </tr>
        </thead>
        <tbody>
          {pendingInvoices.map(inv => (
            <tr key={inv.id} style={{
              background: inv.days_outstanding > 90 ? 'rgba(239,68,68,0.1)' : 'transparent'
            }}>
              <td>
                <input
                  type="checkbox"
                  checked={selectedInvoices.has(inv.id)}
                  onChange={e => toggleSelection(inv.id)}
                />
              </td>
              <td>{inv.origin_period}</td>
              <td>{inv.tercero}</td>
              <td>{inv.doc_key}</td>
              <td style={{ textAlign: 'right', fontWeight: '700' }}>
                {inv.amount_pending.toFixed(2)}€
              </td>
              <td style={{
                color: inv.days_outstanding > 90 ? '#EF4444' :
                       inv.days_outstanding > 60 ? '#F59E0B' : '#10B981'
              }}>
                {inv.days_outstanding} días
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="actions">
        <button onClick={() => onConfirm(Array.from(selectedInvoices))}>
          Procesar con {selectedInvoices.size} facturas arrastradas
        </button>
        <button onClick={onCancel}>
          Procesar solo período actual
        </button>
      </div>
    </div>
  );
}
```

### 4. Vista: Timeline Histórico

```jsx
function CompanyTimeline({ companyId }) {
  const [reconciliations, setReconciliations] = useState([]);

  useEffect(() => {
    fetch(`/api/companies/${companyId}/history`)
      .then(res => res.json())
      .then(data => setReconciliations(data.reconciliations));
  }, [companyId]);

  return (
    <div className="timeline">
      <h2>Histórico de Reconciliaciones</h2>

      <div className="timeline-container">
        {reconciliations.map((recon, i) => (
          <div key={recon.id} className="timeline-item">
            <div className="timeline-marker">
              <div className="period-label">
                Q{recon.period_quarter} {recon.period_year}
              </div>
            </div>

            <div className="timeline-content card">
              <div className="timeline-date">
                {new Date(recon.processed_date).toLocaleDateString()}
              </div>

              <div className="metrics">
                <div>AR: {recon.total_ar_reconciled}€</div>
                <div>AP: {recon.total_ap_reconciled}€</div>
                <div>Pendientes: {recon.num_pending_ar + recon.num_pending_ap}</div>
              </div>

              <button onClick={() => viewDetails(recon.id)}>
                Ver Detalles
              </button>
            </div>

            {i < reconciliations.length - 1 && (
              <div className="timeline-connector">
                {/* Mostrar facturas que pasaron al siguiente período */}
                <div className="carry-forward-indicator">
                  ⬇️ {recon.carried_forward_count} facturas arrastradas
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## 📝 Módulos Nuevos a Crear

### Backend

```
backend/
├── database.py          ← NUEVO: Conexión y operaciones BD
├── models.py            ← NUEVO: Modelos SQLAlchemy
├── period_utils.py      ← NUEVO: Utilidades de período (extract, compare)
├── reconciliation.py    ← MODIFICAR: Añadir lógica histórico
└── main.py              ← MODIFICAR: Nuevos endpoints
```

### Frontend

```
frontend/src/
├── components/
│   ├── CompanyList.jsx          ← NUEVO: Lista empresas sidebar
│   ├── PeriodSelector.jsx       ← NUEVO: Modal selección período
│   ├── CarryforwardPreview.jsx  ← NUEVO: Preview facturas arrastradas
│   └── Timeline.jsx             ← NUEVO: Vista histórico temporal
├── hooks/
│   ├── useCompanies.js          ← NUEVO: Hook gestión empresas
│   └── useReconciliations.js    ← NUEVO: Hook histórico
└── utils/
    └── periodUtils.js           ← NUEVO: Extracción período de filename
```

---

## 🚀 Fases de Implementación

### **Fase 1: Fundamentos (2-3 días) - PRIORIDAD ALTA**

**Objetivo:** Infraestructura básica de BD y persistencia

1. ✅ Crear esquema SQLite (`backend/database.py`)
2. ✅ Modelos ORM con SQLAlchemy (`backend/models.py`)
3. ✅ Función `extract_period_from_filename()` con regex
4. ✅ Endpoint `POST /api/companies/create`
5. ✅ Endpoint `GET /api/companies`
6. ✅ Test básico: Guardar y recuperar empresa

**Entregable:** BD funcional + API básica de empresas

---

### **Fase 2: Persistencia de Reconciliaciones (2-3 días)**

**Objetivo:** Guardar cada reconciliación en BD

1. ✅ Modificar `/api/conciliate` para aceptar `company_id` y `period`
2. ✅ Al terminar reconciliación → guardar en tabla `reconciliations`
3. ✅ Guardar Excel procesado en disco (path en BD)
4. ✅ Endpoint `GET /api/companies/{id}/reconciliations`
5. ✅ UI: Lista de empresas en sidebar (solo lectura)
6. ✅ UI: Al hacer clic en empresa → mostrar lista de reconciliaciones

**Entregable:** Histórico visible por empresa (sin arrastre aún)

---

### **Fase 3: Encadenamiento Básico (3-4 días) - CORE FEATURE**

**Objetivo:** Arrastre de facturas pendientes entre períodos

1. ✅ Tabla `pending_invoices` + CRUD básico
2. ✅ Al guardar reconciliación → extraer y guardar facturas pendientes
3. ✅ Modificar `reconcile_with_history()` para:
   - Cargar facturas previas
   - Inyectarlas en hojas AR/AP_Detalle
   - Marcar como resueltas las que se pagaron
4. ✅ UI: Modal `CarryforwardPreview` mostrando facturas a arrastrar
5. ✅ Test E2E: Procesar Q1 → Q2 y verificar arrastre

**Entregable:** Sistema funcional de arrastre automático

---

### **Fase 4: Visualización y UX (2-3 días)**

**Objetivo:** Interfaces para explorar histórico

1. ✅ Componente `Timeline.jsx` - Vista cronológica
2. ✅ Gráficos de evolución (Chart.js o Recharts):
   - Total reconciliado por trimestre
   - Evolución de pendientes
   - DSO (Days Sales Outstanding) por período
3. ✅ Filtros: Por año, por tipo cuenta (AR/AP)
4. ✅ Exportar histórico completo a Excel consolidado

**Entregable:** Dashboard de análisis histórico

---

### **Fase 5: Features Avanzados (Opcional/Futuro)**

1. ⬜ Persistencia de justificaciones en BD
2. ⬜ Alertas automáticas (email cuando factura > 90 días)
3. ⬜ Reportes automáticos mensuales
4. ⬜ Multi-usuario con autenticación
5. ⬜ API de exportación consolidada multi-período
6. ⬜ Detección de patrones con ML (predecir retrasos)

---

## 📊 Ejemplo de Flujo Completo

### Escenario: Empresa SUMRRASSA procesando 3 trimestres

**Q1 2025:**
```
1. Usuario sube: "MAYOR ALBA 1T 2025 SUMRRASSA, SL.xlsx"
2. Sistema detecta: Q1 2025, empresa "SUMRRASSA, SL"
3. Primera vez → crear empresa en BD
4. Procesar reconciliación normal
5. Resultado: 3 facturas pendientes (5.200€)
6. Guardar en BD:
   - reconciliations: ID=1, Q1 2025
   - pending_invoices: 3 registros
```

**Q2 2025:**
```
1. Usuario sube: "MAYOR ALBA 2T 2025 SUMRRASSA, SL.xlsx"
2. Sistema detecta: Q2 2025, empresa ya existe (ID=1)
3. Cargar facturas pendientes de Q1: 3 items
4. Modal: "Se encontraron 3 facturas pendientes de Q1. ¿Incluir?"
5. Usuario confirma
6. Procesar reconciliación:
   - Inyectar 3 facturas de Q1 al inicio
   - Procesar movimientos de Q2
   - Detectar que 2 facturas de Q1 se pagaron en Q2
7. Guardar en BD:
   - reconciliations: ID=2, Q2 2025
   - pending_invoices:
     * Actualizar 2 facturas Q1 → status="paid_later"
     * Guardar nuevas pendientes de Q2
```

**Q3 2025:**
```
1. Usuario sube: "MAYOR ALBA 3T 2025 SUMRRASSA, SL.xlsx"
2. Sistema detecta: Q3 2025
3. Cargar pendientes:
   - 1 factura aún pendiente de Q1 (120 días!)
   - 2 facturas pendientes de Q2
4. Total arrastre: 3 facturas
5. Procesar + guardar
```

**Vista Timeline:**
```
Q1 2025 ───┬─── Q2 2025 ───┬─── Q3 2025
  3 pend.  │     2 pend.   │     1 pend.
           │               │
      ├─── 2 resueltas ────┤
      │                    │
      └─── 1 persiste ─────┴───→ (alerta: >90 días)
```

---

## ⚠️ Consideraciones Importantes

### Seguridad y Privacidad

- **Datos sensibles:** Nombres de empresas, importes → considerar encriptación
- **GDPR:** Implementar "derecho al olvido" (borrar empresa + todo histórico)
- **Multi-usuario:** Preparar para añadir autenticación en futuro
- **No guardar:** Datos bancarios, información personal de terceros

### Performance

- **Índices BD:** Crear en `company_id`, `period_year`, `doc_key`, `status`
- **Caché:** Mantener `pending_invoices` en memoria durante procesamiento
- **Archivos Excel:** Guardar en disco/S3, no en BD (solo path)
- **Paginación:** API debe paginar resultados (máx 100 registros por request)

### Testing

**Casos de Prueba Críticos:**
1. ✅ Procesar Q1 → verificar facturas guardadas
2. ✅ Procesar Q2 con arrastre → verificar inyección
3. ✅ Factura pendiente Q1 se paga en Q3 → verificar resolución
4. ✅ Edge case: Factura nunca se paga (> 4 trimestres)
5. ✅ Cambio de año (Q4 2024 → Q1 2025)

### Migración de Datos Existentes

**Script de Migración:**
```python
# migration_historic_data.py

def migrate_existing_files():
    """
    Migrar archivos Excel existentes en /public a BD
    """
    import os
    import glob

    excel_files = glob.glob("/public/*.xlsx")

    for file_path in excel_files:
        # Extraer info del filename
        filename = os.path.basename(file_path)
        company_name = extract_company_from_filename(filename)
        period_q, period_y = extract_period_from_filename(filename)

        # Crear empresa si no existe
        company = get_or_create_company(company_name)

        # Verificar si ya está en BD
        existing = db.query(Reconciliation).filter_by(
            company_id=company.id,
            period_quarter=period_q,
            period_year=period_y
        ).first()

        if existing:
            print(f"Skip: {filename} (ya existe)")
            continue

        # Leer y procesar
        print(f"Migrando: {filename}")
        with open(file_path, 'rb') as f:
            content = f.read()

        # Procesar sin arrastre (histórico no conectado)
        result = process_excel(content, tol=0.01, ar_prefix="43", ap_prefix="40")

        # Guardar en BD
        save_reconciliation(
            company_id=company.id,
            period_quarter=period_q,
            period_year=period_y,
            ...
        )

        print(f"✅ Migrado: {filename}")
```

---

## 🎯 Beneficios Esperados

### Para Contables

1. **Reducción de trabajo manual (40-60%)**
   - Facturas pendientes se arrastran automáticamente
   - No necesitan buscar manualmente en trimestres anteriores

2. **Mayor visibilidad**
   - Dashboard: "Cliente X lleva 3 trimestres con factura Y pendiente"
   - Alertas tempranas de morosidad

3. **Trazabilidad completa**
   - Histórico de decisiones (justificaciones)
   - Auditoría: ¿Cuándo se pagó la factura A/337748? → Query directo

### Para la Empresa

1. **Mejor control de tesorería**
   - Evolución temporal de AR/AP visible
   - Predicción de cobros basada en patrones

2. **Reporting automático**
   - Informes trimestrales generados automáticamente
   - Gráficos de evolución para presentar a gerencia

3. **Escalabilidad**
   - Sistema preparado para 100+ empresas
   - Multi-año sin degradación de performance

---

## 📦 Dependencias Técnicas Adicionales

### Backend
```txt
# requirements.txt (añadir)
sqlalchemy==2.0.23
alembic==1.13.0        # Migraciones BD
python-dateutil==2.8.2
```

### Frontend
```json
// package.json (añadir)
{
  "dependencies": {
    "recharts": "^2.10.0",      // Gráficos
    "date-fns": "^3.0.0",       // Utilidades fecha
    "react-query": "^4.0.0"     // Gestión estado servidor
  }
}
```

---

## 📞 Contacto y Siguientes Pasos

**Para retomar el desarrollo:**

1. **Empezar por Fase 1** (fundamentos BD) - 2-3 días
2. **Testing con datos reales** (archivos en `/public`)
3. **Feedback de usuarios** antes de Fase 4 (visualización)

**Preguntas a resolver antes de empezar:**
- ¿SQLite o PostgreSQL desde el inicio?
- ¿Guardar Excels en disco local o cloud (S3)?
- ¿Necesidad de multi-usuario ya en v1?
- ¿Periodicidad: solo trimestres o también mensual?

---

**Documento creado:** 25 Noviembre 2025
**Última actualización:** 25 Noviembre 2025
**Versión:** 1.0
