import React, { useState } from 'react';
import { Upload, FileSpreadsheet, Download, CheckCircle, AlertCircle, ArrowRight, Settings, TrendingUp, AlertTriangle, HelpCircle } from 'lucide-react';
import { conciliateFile } from './api';

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Settings
  const [tol, setTol] = useState(0.01);
  const [arPrefix, setArPrefix] = useState("43");
  const [apPrefix, setApPrefix] = useState("40");
  const [showSettings, setShowSettings] = useState(false);
  const [isRecalculating, setIsRecalculating] = useState(false);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setResult(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError(null);
      setResult(null);
    }
  };

  const handleSubmit = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const data = await conciliateFile(file, tol, arPrefix, apPrefix);
      setResult(data);
    } catch (err) {
      console.error(err);
      const msg = err.response?.data?.detail || err.message || "Error processing file";
      setError(`Error: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  // Recalculate with new tolerance
  const handleToleranceChange = async (newTol) => {
    if (!file || !result) return;

    setTol(newTol);
    setIsRecalculating(true);

    try {
      const data = await conciliateFile(file, newTol, arPrefix, apPrefix);
      setResult(data);
    } catch (err) {
      console.error(err);
      const msg = err.response?.data?.detail || err.message || "Error recalculating";
      setError(`Error: ${msg}`);
    } finally {
      setIsRecalculating(false);
    }
  };

  const downloadFile = () => {
    if (!result || !result.file_b64) return;

    const link = document.createElement('a');
    link.href = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${result.file_b64}`;
    link.download = result.filename || 'conciliacion.xlsx';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const MetricCard = ({ title, value, subtext, icon: Icon, color }) => (
    <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div>
        <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '0.25rem' }}>{title}</div>
        <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)' }}>{value}</div>
        {subtext && <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{subtext}</div>}
      </div>
      <div style={{ padding: '0.5rem', borderRadius: '0.5rem', background: `${color}20`, color: color }}>
        <Icon size={18} />
      </div>
    </div>
  );

  return (
    <div className="container">
      {/* Header - Apple Style */}
      <div style={{
        position: 'sticky',
        top: 0,
        zIndex: 1000,
        background: 'var(--color-bg-elevated)',
        backdropFilter: 'blur(40px) saturate(180%)',
        WebkitBackdropFilter: 'blur(40px) saturate(180%)',
        borderBottom: '1px solid var(--color-separator)',
        padding: 'var(--spacing-4) var(--spacing-6)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-4)' }}>
            <div style={{
              width: '44px',
              height: '44px',
              background: 'linear-gradient(135deg, var(--color-accent-blue) 0%, var(--color-accent-purple) 100%)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: 'var(--shadow-md)',
              fontWeight: '700',
              fontSize: '18px'
            }}>
              ∑
            </div>
            <div>
              <h1 style={{ fontSize: '22px', fontWeight: '700', letterSpacing: '-0.03em', margin: 0 }}>Conciliador</h1>
              <p style={{ fontSize: '13px', color: 'var(--color-label-secondary)', margin: 0 }}>
                {result?.company_name || 'Assessoria Egara'}
              </p>
            </div>
          </div>
        </div>
      </div>

      <main style={{ display: 'flex', minHeight: 'calc(100vh - 84px)' }}>
        {/* Left Sidebar - Apple Style */}
        <aside style={{
          width: '320px',
          minWidth: '320px',
          background: 'var(--color-bg-secondary)',
          borderRight: '1px solid var(--color-separator)',
          padding: 'var(--spacing-6)',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--spacing-6)'
        }}>

          {/* Settings Panel */}
          <div className="card" style={{
            padding: 'var(--spacing-5)'
          }}>
            <h3 style={{
              fontSize: '15px',
              fontWeight: '600',
              marginBottom: 'var(--spacing-4)',
              color: 'var(--color-label-primary)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              Configuración
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-4)' }}>
              <div>
                <label style={{
                  fontSize: '13px',
                  marginBottom: 'var(--spacing-2)',
                  display: 'block',
                  color: 'var(--color-label-secondary)',
                  fontWeight: '500'
                }}>Tolerancia (€)</label>
                <input type="number" step="0.01" value={tol} onChange={(e) => setTol(parseFloat(e.target.value))} />
              </div>
              <div>
                <label style={{
                  fontSize: '13px',
                  marginBottom: 'var(--spacing-2)',
                  display: 'block',
                  color: 'var(--color-label-secondary)',
                  fontWeight: '500'
                }}>Prefijo Clientes (AR)</label>
                <input type="text" value={arPrefix} onChange={(e) => setArPrefix(e.target.value)} />
              </div>
              <div>
                <label style={{
                  fontSize: '13px',
                  marginBottom: 'var(--spacing-2)',
                  display: 'block',
                  color: 'var(--color-label-secondary)',
                  fontWeight: '500'
                }}>Prefijo Proveedores (AP)</label>
                <input type="text" value={apPrefix} onChange={(e) => setApPrefix(e.target.value)} />
              </div>
            </div>
          </div>

          {/* File Upload - Apple Style */}
          {!result && (
            <div className="card" style={{
              padding: 'var(--spacing-5)',
              textAlign: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s cubic-bezier(0.25, 0.1, 0.25, 1)',
              borderStyle: 'dashed',
              borderWidth: '2px',
              borderColor: file ? 'var(--color-accent-blue)' : 'var(--color-separator)'
            }}
              onDragOver={(e) => { e.preventDefault(); }}
              onDrop={handleDrop}
              onClick={() => document.getElementById('fileInput').click()}
              onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-accent-blue)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.borderColor = file ? 'var(--color-accent-blue)' : 'var(--color-separator)'; }}
            >
              <input
                id="fileInput"
                type="file"
                accept=".xlsx"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
              <Upload size={36} color={file ? 'var(--color-accent-blue)' : 'var(--color-label-secondary)'} style={{ marginBottom: 'var(--spacing-3)' }} />
              <div style={{ fontSize: '14px', color: 'var(--color-label-primary)', fontWeight: '600', marginBottom: 'var(--spacing-1)', wordBreak: 'break-word' }}>
                {file ? file.name : "Seleccionar archivo"}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-label-tertiary)' }}>
                {file ? "Click para cambiar" : "Arrastra Excel aquí"}
              </div>
              {file && (
                <div style={{
                  marginTop: 'var(--spacing-3)',
                  padding: 'var(--spacing-2) var(--spacing-3)',
                  background: 'rgba(48, 209, 88, 0.15)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--color-accent-green)',
                  fontSize: '12px',
                  fontWeight: '600',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 'var(--spacing-1)'
                }}>
                  <CheckCircle size={14} />
                  Listo
                </div>
              )}
            </div>
          )}

          {/* Action Button - Apple Style */}
          {!result && (
            <button
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={!file || loading}
              style={{
                width: '100%',
                padding: 'var(--spacing-4)',
                fontSize: '15px',
                fontWeight: '600',
                borderRadius: 'var(--radius-lg)'
              }}
            >
              {loading ? (
                <>
                  <div className="loading-spinner"></div>
                  Procesando...
                </>
              ) : (
                <>
                  Ejecutar
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          )}

          {/* Error Message - Apple Style */}
          {error && (
            <div className="card" style={{
              padding: 'var(--spacing-4)',
              background: 'rgba(255, 69, 58, 0.1)',
              borderColor: 'rgba(255, 69, 58, 0.3)',
              display: 'flex',
              alignItems: 'flex-start',
              gap: 'var(--spacing-2)'
            }}>
              <AlertCircle size={18} color="var(--color-accent-red)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div style={{ fontSize: '13px', color: 'var(--color-accent-red)', lineHeight: '1.4' }}>{error}</div>
            </div>
          )}

          {/* Result Actions - Apple Style */}
          {result && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-3)' }}>
              <button className="btn btn-primary" onClick={downloadFile} style={{ width: '100%', padding: 'var(--spacing-3)', fontSize: '14px' }}>
                <Download size={16} />
                Descargar Excel
              </button>
              <button className="btn btn-secondary" onClick={() => { setResult(null); setFile(null); }} style={{ width: '100%', padding: 'var(--spacing-3)', fontSize: '14px' }}>
                Nuevo Archivo
              </button>
            </div>
          )}
        </aside>

        {/* Main Content Area - Apple Style */}
        <div style={{ flex: 1, padding: 'var(--spacing-8)', overflowY: 'auto', background: 'var(--color-bg-primary)' }}>

          {/* Results View */}
          {result && (
            <div className="animate-fade-in">
              {/* Metrics Grid - Full Width Dashboard */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                {/* AR Metrics */}
                <MetricCard
                  title="AR Conciliado (Clientes)"
                  value={`${result.summary.find(r => r.Bloque === 'AR')?.Asignado.toLocaleString()} €`}
                  icon={TrendingUp}
                  color="var(--success)"
                />
                <MetricCard
                  title="AR Pendientes (Clientes)"
                  value={result.summary.find(r => r.Bloque === 'AR')?.Docs_pendientes}
                  icon={AlertTriangle}
                  color="var(--secondary)"
                />
                <MetricCard
                  title="AP Conciliado (Proveedores)"
                  value={`${result.summary.find(r => r.Bloque === 'AP')?.Asignado.toLocaleString()} €`}
                  icon={TrendingUp}
                  color="var(--success)"
                />
                <MetricCard
                  title="AP Pendientes (Proveedores)"
                  value={result.summary.find(r => r.Bloque === 'AP')?.Docs_pendientes}
                  icon={AlertTriangle}
                  color="var(--secondary)"
                />
              </div>

              {/* Visual Reconciliation Details */}
              {result.details && (
                <ReconciliationDetails details={result.details} />
              )}
            </div>
          )}

        </div>
      </main >
    </div >
  );
}

function ReconciliationDetails({ details }) {
  const [activeTab, setActiveTab] = useState('matches'); // 'matches' | 'pending'
  const [activeBlock, setActiveBlock] = useState('AR'); // 'AR' | 'AP'

  const getMatches = () => {
    const detailKey = activeBlock === 'AR' ? 'AR_Detalle' : 'AP_Detalle';
    const data = details[detailKey] || [];

    // Group by SetID
    const sets = {};
    data.forEach(row => {
      if (!sets[row.SetID]) sets[row.SetID] = [];
      sets[row.SetID].push(row);
    });

    return Object.values(sets).filter(set => set.length > 0);
  };

  const getPending = () => {
    const pendingKey = activeBlock === 'AR' ? 'Pendientes_AR' : 'Pendientes_AP';
    return details[pendingKey] || [];
  };

  return (
    <div style={{ marginTop: '3rem' }}>
      {/* Controls */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', background: 'rgba(0,0,0,0.4)', borderRadius: '12px', padding: '6px', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }}>
          <button
            onClick={() => setActiveBlock('AR')}
            style={{
              padding: '12px 32px',
              borderRadius: '8px',
              border: 'none',
              background: activeBlock === 'AR' ? 'linear-gradient(135deg, var(--color-accent-blue) 0%, var(--color-accent-purple) 100%)' : 'rgba(255,255,255,0.05)',
              color: 'white',
              cursor: 'pointer',
              fontWeight: '700',
              fontSize: '15px',
              transition: 'all 0.2s ease',
              boxShadow: activeBlock === 'AR' ? '0 4px 12px rgba(10, 132, 255, 0.4)' : 'none',
              transform: activeBlock === 'AR' ? 'scale(1.02)' : 'scale(1)'
            }}
          >
            Clientes (AR)
          </button>
          <button
            onClick={() => setActiveBlock('AP')}
            style={{
              padding: '12px 32px',
              borderRadius: '8px',
              border: 'none',
              background: activeBlock === 'AP' ? 'linear-gradient(135deg, #ec4899 0%, #f472b6 100%)' : 'rgba(255,255,255,0.05)',
              color: 'white',
              cursor: 'pointer',
              fontWeight: '700',
              fontSize: '15px',
              transition: 'all 0.2s ease',
              boxShadow: activeBlock === 'AP' ? '0 4px 12px rgba(236, 72, 153, 0.4)' : 'none',
              transform: activeBlock === 'AP' ? 'scale(1.02)' : 'scale(1)'
            }}
          >
            Proveedores (AP)
          </button>
        </div>

        <div style={{ display: 'flex', background: 'rgba(0,0,0,0.4)', borderRadius: '12px', padding: '6px', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }}>
          <button
            onClick={() => setActiveTab('matches')}
            style={{
              padding: '12px 32px',
              borderRadius: '8px',
              border: 'none',
              background: activeTab === 'matches' ? 'linear-gradient(135deg, #10b981 0%, #34d399 100%)' : 'rgba(255,255,255,0.05)',
              color: 'white',
              cursor: 'pointer',
              fontWeight: '700',
              fontSize: '15px',
              transition: 'all 0.2s ease',
              boxShadow: activeTab === 'matches' ? '0 4px 12px rgba(16, 185, 129, 0.4)' : 'none',
              transform: activeTab === 'matches' ? 'scale(1.02)' : 'scale(1)'
            }}
          >
            Emparejados
          </button>
          <button
            onClick={() => setActiveTab('pending')}
            style={{
              padding: '12px 32px',
              borderRadius: '8px',
              border: 'none',
              background: activeTab === 'pending' ? 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)' : 'rgba(255,255,255,0.05)',
              color: 'white',
              cursor: 'pointer',
              fontWeight: '700',
              fontSize: '15px',
              transition: 'all 0.2s ease',
              boxShadow: activeTab === 'pending' ? '0 4px 12px rgba(245, 158, 11, 0.4)' : 'none',
              transform: activeTab === 'pending' ? 'scale(1.02)' : 'scale(1)'
            }}
          >
            Pendientes
          </button>
        </div>
      </div>

      {/* Content */}
      <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '1rem', padding: '1.5rem', maxHeight: '600px', overflowY: 'auto' }}>
        {activeTab === 'matches' ? (
          <MatchesList matches={getMatches()} />
        ) : (
          <PendingList items={getPending()} />
        )}
      </div>
    </div>
  );
}

function MatchesList({ matches }) {
  if (matches.length === 0) return <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No se encontraron emparejamientos.</div>;

  return (
    <div style={{ display: 'grid', gap: '1.5rem' }}>
      {matches.slice(0, 100).map((set, i) => {
        const tercero = set[0].Tercero;

        // Calculate totals and status
        const invoiceRows = set.filter(r => r.DocKey && r.PagoKey);
        const totalPaid = invoiceRows.reduce((sum, row) => sum + Math.abs(row.Asignado || 0), 0);
        const totalPending = invoiceRows.reduce((sum, row) => sum + (row.ResidualFacturaTras || 0), 0);
        const hasUnmatched = set.some(r => r.Asignado < 0);
        const hasPartial = set.some(r => r.ResidualFacturaTras > 0.01);
        const numInvoices = new Set(set.filter(r => r.DocKey).map(r => r.DocKey)).size;
        const numPayments = new Set(set.filter(r => r.PagoKey).map(r => r.PagoKey)).size;

        // Determine overall status - VERY CLEAR LOGIC
        let statusColor, statusBg, statusText, statusIcon;
        if (hasUnmatched) {
          // RED: Payment without invoice
          statusColor = '#EF4444';
          statusBg = 'rgba(239, 68, 68, 0.15)';
          statusText = 'Pago sin Factura';
          statusIcon = '🔴';
        } else if (hasPartial || totalPending > 0.01) {
          // ORANGE: Partial payment
          statusColor = '#F59E0B';
          statusBg = 'rgba(245, 158, 11, 0.15)';
          statusText = 'Pago Parcial';
          statusIcon = '🟠';
        } else {
          // GREEN: Fully paid
          statusColor = '#10B981';
          statusBg = 'rgba(16, 185, 129, 0.15)';
          statusText = 'Totalmente Pagado';
          statusIcon = '🟢';
        }

        return (
          <div key={i} style={{
            background: 'rgba(0,0,0,0.3)',
            borderRadius: '12px',
            padding: '1.5rem',
            border: `3px solid ${statusColor}`,
            boxShadow: `0 0 20px ${statusColor}40`
          }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', paddingBottom: '1rem', borderBottom: `2px solid ${statusColor}60` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{
                  background: statusBg,
                  color: statusColor,
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '800',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  border: `2px solid ${statusColor}`,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  <span style={{ fontSize: '18px' }}>{statusIcon}</span>
                  {statusText}
                </div>
                <span style={{ fontWeight: 'bold', color: '#e2e8f0', fontSize: '1.1rem' }}>{tercero}</span>
              </div>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  <span style={{ color: '#3B82F6', fontWeight: 'bold' }}>📄 {numInvoices}</span> ↔ <span style={{ color: '#EC4899', fontWeight: 'bold' }}>💳 {numPayments}</span>
                </div>
              </div>
            </div>

            {/* Table */}
            <table style={{ width: '100%', fontSize: '0.9rem', borderCollapse: 'separate', borderSpacing: '0 0.5rem' }}>
              <thead>
                <tr style={{ color: 'var(--text-muted)', textAlign: 'left', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  <th style={{ padding: '0.75rem' }}>Tipo</th>
                  <th style={{ padding: '0.75rem' }}>Fecha</th>
                  <th style={{ padding: '0.75rem' }}>Documento</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>Importe Asignado</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>Saldo Pendiente</th>
                  <th style={{ padding: '0.75rem', textAlign: 'center' }}>Estado</th>
                </tr>
              </thead>
              <tbody>
                {set.map((row, j) => {
                  const isInvoice = row.DocKey && !row.PagoKey;
                  const isPayment = row.PagoKey && !row.DocKey;
                  const isMatch = row.DocKey && row.PagoKey;
                  const isUnmatched = row.Asignado < 0;
                  const hasPending = row.ResidualFacturaTras > 0.01;

                  // Row-level color coding
                  let rowBg, rowBorder, rowStatusColor;
                  if (isUnmatched) {
                    // RED: Unmatched payment
                    rowBg = 'rgba(239, 68, 68, 0.1)';
                    rowBorder = '4px solid #EF4444';
                    rowStatusColor = '#EF4444';
                  } else if (hasPending) {
                    // ORANGE: Partial
                    rowBg = 'rgba(245, 158, 11, 0.1)';
                    rowBorder = '4px solid #F59E0B';
                    rowStatusColor = '#F59E0B';
                  } else {
                    // GREEN: OK
                    rowBg = 'rgba(16, 185, 129, 0.1)';
                    rowBorder = '4px solid #10B981';
                    rowStatusColor = '#10B981';
                  }

                  return (
                    <tr key={j} style={{
                      background: rowBg,
                      borderLeft: rowBorder,
                      borderRadius: '8px'
                    }}>
                      <td style={{ padding: '0.75rem', borderRadius: '8px 0 0 8px' }}>
                        {isMatch && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <span style={{ color: '#10B981', fontWeight: 'bold', fontSize: '0.9rem' }}>⟷ Match</span>
                            {row.MatchMethod && (
                              <span style={{
                                fontSize: '0.7rem',
                                fontWeight: '700',
                                padding: '2px 8px',
                                borderRadius: '4px',
                                background:
                                  row.MatchMethod === 'Reference' ? 'rgba(16, 185, 129, 0.2)' :
                                    row.MatchMethod === 'Exact' ? 'rgba(59, 130, 246, 0.2)' :
                                      row.MatchMethod === 'FIFO' ? 'rgba(168, 85, 247, 0.2)' :
                                        'rgba(120, 120, 128, 0.2)',
                                color:
                                  row.MatchMethod === 'Reference' ? '#10B981' :
                                    row.MatchMethod === 'Exact' ? '#3B82F6' :
                                      row.MatchMethod === 'FIFO' ? '#A855F7' :
                                        '#6B7280'
                              }}>
                                {row.MatchMethod === 'Reference' && '🔗 Ref'}
                                {row.MatchMethod === 'Exact' && '💯 Exact'}
                                {row.MatchMethod === 'FIFO' && '⏰ FIFO'}
                                {!['Reference', 'Exact', 'FIFO'].includes(row.MatchMethod) && row.MatchMethod}
                              </span>
                            )}
                          </div>
                        )}
                        {isInvoice && <span style={{ color: '#3B82F6', fontWeight: 'bold' }}>📄 Factura</span>}
                        {isPayment && <span style={{ color: '#EF4444', fontWeight: 'bold' }}>💳 Pago</span>}
                      </td>
                      <td style={{ padding: '0.75rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        {isMatch ? (
                          <div style={{ fontSize: '0.8rem' }}>
                            <div style={{ fontWeight: '600' }}>{row.Fecha_doc}</div>
                            <div style={{ color: 'var(--text-muted)', opacity: 0.7 }}>↓ {row.Fecha_pago}</div>
                          </div>
                        ) : (
                          row.Fecha_doc || row.Fecha_pago || '-'
                        )}
                      </td>
                      <td style={{ padding: '0.75rem', maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {isMatch ? (
                          <div style={{ fontSize: '0.8rem' }}>
                            <div title={row.DocKey} style={{ fontWeight: '600' }}>{row.DocKey ? row.DocKey.split('|')[1] : '-'}</div>
                            <div style={{ color: 'var(--text-muted)', opacity: 0.7 }} title={row.PagoKey}>{row.PagoKey ? row.PagoKey.split('|')[1] : '-'}</div>
                          </div>
                        ) : (
                          <span title={row.DocKey || row.PagoKey} style={{ fontSize: '0.85rem' }}>
                            {(row.DocKey || row.PagoKey) ? (row.DocKey || row.PagoKey).split('|')[1] : '-'}
                          </span>
                        )}
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                        <div style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          color: rowStatusColor,
                          fontWeight: '700',
                          background: `${rowStatusColor}20`,
                          padding: '6px 12px',
                          borderRadius: '6px',
                          fontSize: '0.95rem',
                          border: `2px solid ${rowStatusColor}`
                        }}>
                          {Math.abs(row.Asignado)?.toFixed(2)} €
                        </div>
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                        {row.ResidualFacturaTras !== null && row.ResidualFacturaTras !== undefined && !isPayment ? (
                          <div style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            color: row.ResidualFacturaTras > 0.01 ? '#EF4444' : '#10B981',
                            fontWeight: '700',
                            background: row.ResidualFacturaTras > 0.01 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                            padding: '6px 12px',
                            borderRadius: '6px',
                            fontSize: '0.95rem',
                            border: row.ResidualFacturaTras > 0.01 ? '2px solid #EF4444' : '2px solid #10B981'
                          }}>
                            {row.ResidualFacturaTras > 0.01 ? <AlertCircle size={14} /> : <CheckCircle size={14} />}
                            {row.ResidualFacturaTras?.toFixed(2)} €
                          </div>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>-</span>
                        )}
                      </td>
                      <td style={{ padding: '0.75rem', textAlign: 'center', borderRadius: '0 8px 8px 0' }}>
                        {isUnmatched ? (
                          <span style={{
                            fontSize: '16px',
                            fontWeight: '900',
                            color: '#EF4444',
                            background: 'rgba(239, 68, 68, 0.2)',
                            padding: '4px 12px',
                            borderRadius: '6px',
                            border: '2px solid #EF4444'
                          }}>
                            🔴 KO
                          </span>
                        ) : row.ResidualFacturaTras > 0.01 ? (
                          <span style={{
                            fontSize: '16px',
                            fontWeight: '900',
                            color: '#F59E0B',
                            background: 'rgba(245, 158, 11, 0.2)',
                            padding: '4px 12px',
                            borderRadius: '6px',
                            border: '2px solid #F59E0B'
                          }}>
                            🟠 PARCIAL
                          </span>
                        ) : (
                          <span style={{
                            fontSize: '16px',
                            fontWeight: '900',
                            color: '#10B981',
                            background: 'rgba(16, 185, 129, 0.2)',
                            padding: '4px 12px',
                            borderRadius: '6px',
                            border: '2px solid #10B981'
                          }}>
                            🟢 OK
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Summary Footer */}
            <div style={{
              marginTop: '1rem',
              padding: '1rem',
              background: 'rgba(0,0,0,0.4)',
              borderRadius: '8px',
              border: `2px solid ${statusColor}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div style={{ display: 'flex', gap: '2rem' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Total Pagado</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: '800', color: '#10B981' }}>
                    {totalPaid.toFixed(2)} €
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Total Pendiente</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: '800', color: totalPending > 0.01 ? '#EF4444' : '#10B981' }}>
                    {totalPending.toFixed(2)} €
                  </div>
                </div>
              </div>
              <div style={{
                fontSize: '1.5rem',
                fontWeight: '900',
                color: statusColor,
                background: statusBg,
                padding: '12px 24px',
                borderRadius: '8px',
                border: `3px solid ${statusColor}`
              }}>
                {statusIcon} {statusText}
              </div>
            </div>
          </div>
        );
      })}
      {matches.length > 100 && (
        <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-muted)' }}>
          ... y {matches.length - 100} grupos más (descarga el Excel para ver todos)
        </div>
      )}
    </div>
  );
}

function PendingList({ items }) {
  if (items.length === 0) return <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No hay elementos pendientes.</div>;

  // Sort by days open (descending)
  const sortedItems = [...items].sort((a, b) => (b.Dias || 0) - (a.Dias || 0));

  return (
    <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0 0.25rem', fontSize: '0.9rem' }}>
      <thead>
        <tr style={{ background: 'rgba(255,255,255,0.1)', color: 'white' }}>
          <th style={{ padding: '0.75rem', textAlign: 'left', borderRadius: '0.5rem 0 0 0.5rem' }}>Tercero</th>
          <th style={{ padding: '0.75rem', textAlign: 'left' }}>Fecha</th>
          <th style={{ padding: '0.75rem', textAlign: 'left' }}>Documento</th>
          <th style={{ padding: '0.75rem', textAlign: 'right' }}>Días Pendientes</th>
          <th style={{ padding: '0.75rem', textAlign: 'right', borderRadius: '0 0.5rem 0.5rem 0' }}>Importe Pendiente</th>
        </tr>
      </thead>
      <tbody>
        {sortedItems.map((item, i) => {
          // Determine urgency color
          let urgencyColor = 'var(--secondary)';
          let urgencyBg = 'rgba(230, 159, 0, 0.05)';
          let urgencyBorder = '3px solid var(--secondary)';

          if (item.Dias > 90) {
            urgencyColor = 'var(--error)';
            urgencyBg = 'rgba(213, 94, 0, 0.05)';
            urgencyBorder = '3px solid var(--error)';
          } else if (item.Dias > 60) {
            urgencyColor = 'var(--secondary)';
          } else {
            urgencyColor = 'var(--primary)';
            urgencyBg = 'rgba(0, 114, 178, 0.05)';
            urgencyBorder = '3px solid var(--primary)';
          }

          return (
            <tr key={i} style={{
              background: urgencyBg,
              borderLeft: urgencyBorder
            }}>
              <td style={{ padding: '0.75rem' }}>{item.Tercero}</td>
              <td style={{ padding: '0.75rem', color: 'var(--text-muted)' }}>{item.Fecha}</td>
              <td style={{ padding: '0.75rem', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={item.DocKey}>
                {item.DocKey ? item.DocKey.split('|')[1] : item.DocKey}
              </td>
              <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  color: urgencyColor,
                  fontWeight: 'bold',
                  fontSize: '0.85rem'
                }}>
                  {item.Dias > 90 && '🔴'}
                  {item.Dias > 60 && item.Dias <= 90 && '🟠'}
                  {item.Dias <= 60 && '🟢'}
                  {item.Dias} days
                </div>
              </td>
              <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  color: urgencyColor,
                  fontWeight: 'bold',
                  background: urgencyColor === 'var(--error)' ? 'rgba(213, 94, 0, 0.1)' : urgencyColor === 'var(--secondary)' ? 'rgba(230, 159, 0, 0.1)' : 'rgba(0, 114, 178, 0.1)',
                  padding: '0.25rem 0.5rem',
                  borderRadius: '0.25rem'
                }}>
                  <AlertTriangle size={14} />
                  {item.ImportePendiente?.toFixed(2)} €
                </div>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default App;

