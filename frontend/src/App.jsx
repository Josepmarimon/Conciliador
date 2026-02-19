import React, { useState, useEffect } from 'react';
import { Upload, FileSpreadsheet, Download, CheckCircle, AlertCircle, ArrowRight, Settings, TrendingUp, AlertTriangle, HelpCircle, ChevronLeft, ChevronRight, Activity, LogOut, User } from 'lucide-react';
import { conciliateFile, getStats } from './api';
import HelpModal from './HelpModal';
import Login from './Login';
import { useAuth } from './AuthContext';

function App() {
  const { user, loading: authLoading, logout, isAuthenticated } = useAuth();

  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Settings
  const [tol, setTol] = useState(0.01);
  const [arPrefix, setArPrefix] = useState("43");
  const [apPrefix, setApPrefix] = useState("40,41");
  const [showSettings, setShowSettings] = useState(false);
  const [isRecalculating, setIsRecalculating] = useState(false);

  // Justifications for unmatched payments
  const [justifications, setJustifications] = useState({});

  // Help modal
  const [showHelp, setShowHelp] = useState(false);

  // Sidebar toggle
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Statistics
  const [stats, setStats] = useState(null);

  useEffect(() => {
    // Load statistics on mount
    const loadStats = async () => {
      const statsData = await getStats();
      setStats(statsData);
    };
    loadStats();
  }, [result]); // Reload stats after each reconciliation

  // Auth guards — AFTER all hooks
  if (authLoading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)',
      }}>
        <div style={{ color: '#94a3b8', fontSize: '16px' }}>Carregant...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login />;
  }

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
      const data = await conciliateFile(file, tol, arPrefix, apPrefix, justifications);
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
      const data = await conciliateFile(file, newTol, arPrefix, apPrefix, justifications);
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
              <h1 style={{ fontSize: '28px', fontWeight: '700', letterSpacing: '-0.03em', margin: 0, display: 'flex', alignItems: 'baseline', gap: '0.75rem', flexWrap: 'wrap' }}>
                <span>Conciliador Contable</span>
                <span style={{ fontSize: '20px', color: 'var(--color-label-secondary)', fontWeight: '400' }}>Assessoria Egara</span>
                {result?.company_name && (
                  <>
                    <span style={{ fontSize: '24px', color: 'var(--color-label-secondary)', fontWeight: '400' }}>/</span>
                    <span style={{ fontSize: '20px', color: 'var(--color-label-primary)' }}>
                      {result.company_name}
                    </span>
                    {result?.period && (
                      <span style={{ fontSize: '18px', color: 'var(--color-accent-blue)', fontWeight: '600' }}>
                        • {result.period}
                      </span>
                    )}
                  </>
                )}
              </h1>
            </div>
          </div>
          {/* User Info and Logout */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-3)' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--spacing-2)',
              padding: 'var(--spacing-2) var(--spacing-3)',
              background: 'rgba(99, 102, 241, 0.1)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid rgba(99, 102, 241, 0.2)',
            }}>
              <User size={16} color="var(--color-accent-blue)" />
              <span style={{ fontSize: '13px', color: 'var(--color-label-primary)', fontWeight: '500' }}>
                {user?.email}
              </span>
              {user?.role === 'admin' && (
                <span style={{
                  fontSize: '10px',
                  fontWeight: '700',
                  color: '#f59e0b',
                  background: 'rgba(245, 158, 11, 0.15)',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  textTransform: 'uppercase',
                }}>
                  Admin
                </span>
              )}
            </div>
            <button
              onClick={logout}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--spacing-2)',
                padding: 'var(--spacing-2) var(--spacing-3)',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.2)',
                borderRadius: 'var(--radius-md)',
                color: '#ef4444',
                fontSize: '13px',
                fontWeight: '500',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)';
              }}
            >
              <LogOut size={16} />
              Sortir
            </button>
          </div>
        </div>
      </div>

      <main style={{ display: 'flex', minHeight: 'calc(100vh - 84px)', position: 'relative' }}>
        {/* Left Sidebar - Apple Style */}
        <aside style={{
          width: sidebarCollapsed ? '0px' : '320px',
          minWidth: sidebarCollapsed ? '0px' : '320px',
          background: 'var(--color-bg-secondary)',
          borderRight: '1px solid var(--color-separator)',
          padding: sidebarCollapsed ? '0' : 'var(--spacing-6)',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--spacing-6)',
          transition: 'all 0.3s ease-in-out',
          overflow: sidebarCollapsed ? 'hidden' : 'auto'
        }}>

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

          {/* Statistics Card */}
          {stats && (
            <div className="card" style={{
              padding: 'var(--spacing-5)',
              marginBottom: 'var(--spacing-4)',
              background: 'linear-gradient(135deg, rgba(88, 86, 214, 0.05) 0%, rgba(32, 201, 151, 0.05) 100%)',
              borderLeft: '3px solid var(--color-accent-blue)'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--spacing-2)',
                marginBottom: 'var(--spacing-3)'
              }}>
                <Activity size={18} color="var(--color-accent-blue)" />
                <h3 style={{
                  fontSize: '15px',
                  fontWeight: '600',
                  color: 'var(--color-label-primary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  margin: 0
                }}>
                  Estadísticas de Uso
                </h3>
              </div>
              <div style={{ fontSize: '14px', color: 'var(--color-label-secondary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--spacing-2)' }}>
                  <span>Total conciliaciones:</span>
                  <span style={{ fontWeight: '600', color: 'var(--color-accent-blue)' }}>
                    {stats.total_reconciliations || 0}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--spacing-2)' }}>
                  <span>Archivos procesados:</span>
                  <span style={{ fontWeight: '600', color: 'var(--color-accent-green)' }}>
                    {stats.total_files_processed || 0}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Movimientos totales:</span>
                  <span style={{ fontWeight: '600', color: 'var(--color-label-primary)' }}>
                    {stats.total_rows_processed ? stats.total_rows_processed.toLocaleString('es-ES') : 0}
                  </span>
                </div>
                {stats.last_reconciliation && (
                  <div style={{
                    marginTop: 'var(--spacing-3)',
                    paddingTop: 'var(--spacing-3)',
                    borderTop: '1px solid var(--color-separator)',
                    fontSize: '12px'
                  }}>
                    <div>
                      Última conciliación: {new Date(stats.last_reconciliation).toLocaleString('es-ES')}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Settings Panel - Collapsible */}
          <div className="card" style={{
            padding: 'var(--spacing-5)'
          }}>
            <div
              onClick={() => setShowSettings(!showSettings)}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                cursor: 'pointer',
                marginBottom: showSettings ? 'var(--spacing-4)' : '0'
              }}
            >
              <h3 style={{
                fontSize: '15px',
                fontWeight: '600',
                color: 'var(--color-label-primary)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                margin: 0
              }}>
                Configuración
              </h3>
              <Settings size={18} color="var(--color-label-secondary)" style={{
                transform: showSettings ? 'rotate(90deg)' : 'rotate(0deg)',
                transition: 'transform 0.3s ease'
              }} />
            </div>
            {showSettings && (
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
            )}
          </div>

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
              <button
                className="btn btn-secondary"
                onClick={() => setShowHelp(true)}
                style={{
                  width: '100%',
                  padding: 'var(--spacing-3)',
                  fontSize: '14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem'
                }}
              >
                <HelpCircle size={16} />
                Cómo Funciona
              </button>
            </div>
          )}

          {/* Help Button - When no result */}
          {!result && (
            <div style={{ marginTop: 'auto', paddingTop: 'var(--spacing-4)' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setShowHelp(true)}
                style={{
                  width: '100%',
                  padding: 'var(--spacing-3)',
                  fontSize: '14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem'
                }}
              >
                <HelpCircle size={16} />
                Cómo Funciona
              </button>
            </div>
          )}
        </aside>

        {/* Toggle Button */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          style={{
            position: 'absolute',
            left: sidebarCollapsed ? '0' : '320px',
            top: '20px',
            zIndex: 1001,
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            background: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-separator)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            transition: 'all 0.3s ease-in-out',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            color: 'var(--color-label-primary)'
          }}
        >
          {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>

        {/* Main Content Area - Apple Style */}
        <div style={{ flex: 1, padding: 'var(--spacing-8)', overflowY: 'auto', background: 'var(--color-bg-primary)' }}>

          {/* Results View */}
          {result && !showHelp && (
            <div className="animate-fade-in">
              {/* Metrics Grid - Full Width Dashboard */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                {/* Clientes Metrics */}
                <MetricCard
                  title="Clientes Conciliado"
                  value={`${result.summary.find(r => r.Bloque === 'Clientes')?.Asignado?.toLocaleString() ?? '0'} €`}
                  icon={TrendingUp}
                  color="var(--success)"
                />
                <MetricCard
                  title="Clientes Pendientes"
                  value={result.summary.find(r => r.Bloque === 'Clientes')?.Docs_pendientes ?? 0}
                  icon={AlertTriangle}
                  color="var(--secondary)"
                />
                <MetricCard
                  title="Proveedores Conciliado"
                  value={`${result.summary.find(r => r.Bloque === 'Proveedores')?.Asignado?.toLocaleString() ?? '0'} €`}
                  icon={TrendingUp}
                  color="var(--success)"
                />
                <MetricCard
                  title="Proveedores Pendientes"
                  value={result.summary.find(r => r.Bloque === 'Proveedores')?.Docs_pendientes ?? 0}
                  icon={AlertTriangle}
                  color="var(--secondary)"
                />
              </div>

              {/* Visual Reconciliation Details */}
              {result.details && (
                <ReconciliationDetails details={result.details} justifications={justifications} setJustifications={setJustifications} />
              )}
            </div>
          )}

        </div>
      </main >

      {/* Help Modal */}
      <HelpModal isOpen={showHelp} onClose={() => setShowHelp(false)} />
    </div >
  );
}

function ReconciliationDetails({ details, justifications, setJustifications }) {
  const [activeTab, setActiveTab] = useState('matches'); // 'matches' | 'pending'
  const [activeBlock, setActiveBlock] = useState('AR'); // 'AR' | 'AP'

  const getMatches = () => {
    const detailKey = activeBlock === 'AR' ? 'Clientes_Detalle' : 'Proveedores_Detalle';
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
    const pendingKey = activeBlock === 'AR' ? 'Pendientes_Clientes' : 'Pendientes_Proveedores';
    return details[pendingKey] || [];
  };

  return (
    <div style={{ marginTop: '3rem' }}>
      {/* Compact tabs container */}
      <div style={{
        background: 'rgba(0,0,0,0.2)',
        borderRadius: '1rem',
        padding: '0.75rem',
        marginBottom: '1.5rem',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        flexWrap: 'wrap'
      }}>
        {/* Main Tabs (Clientes / Proveedores) */}
        <div style={{
          display: 'inline-flex',
          gap: '4px',
          background: 'rgba(0,0,0,0.4)',
          borderRadius: '8px',
          padding: '3px',
          border: '1px solid rgba(255,255,255,0.1)'
        }}>
          <button
            onClick={() => setActiveBlock('AR')}
            style={{
              padding: '6px 20px',
              borderRadius: '6px',
              border: activeBlock === 'AR' ? '2px solid rgba(10, 132, 255, 0.6)' : '2px solid transparent',
              background: activeBlock === 'AR' ? 'linear-gradient(135deg, var(--color-accent-blue) 0%, var(--color-accent-purple) 100%)' : 'transparent',
              color: 'white',
              cursor: 'pointer',
              fontWeight: activeBlock === 'AR' ? '700' : '600',
              fontSize: '13px',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: activeBlock === 'AR' ? '0 4px 16px rgba(10, 132, 255, 0.4)' : 'none',
              opacity: activeBlock === 'AR' ? 1 : 0.7
            }}
          >
            Clientes
          </button>
          <button
            onClick={() => setActiveBlock('AP')}
            style={{
              padding: '6px 20px',
              borderRadius: '6px',
              border: activeBlock === 'AP' ? '2px solid rgba(236, 72, 153, 0.6)' : '2px solid transparent',
              background: activeBlock === 'AP' ? 'linear-gradient(135deg, #ec4899 0%, #f472b6 100%)' : 'transparent',
              color: 'white',
              cursor: 'pointer',
              fontWeight: activeBlock === 'AP' ? '700' : '600',
              fontSize: '13px',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: activeBlock === 'AP' ? '0 4px 16px rgba(236, 72, 153, 0.4)' : 'none',
              opacity: activeBlock === 'AP' ? 1 : 0.7
            }}
          >
            Proveedores
          </button>
        </div>

        {/* Vertical divider */}
        <div style={{ width: '1px', height: '24px', background: 'rgba(255,255,255,0.2)' }}></div>

        {/* Sub-tabs */}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => setActiveTab('matches')}
            style={{
              padding: '6px 16px',
              borderRadius: '16px',
              border: activeTab === 'matches' ? '2px solid #10b981' : '2px solid rgba(255,255,255,0.15)',
              background: activeTab === 'matches' ? 'linear-gradient(135deg, #10b981 0%, #34d399 100%)' : 'rgba(0,0,0,0.3)',
              color: 'white',
              cursor: 'pointer',
              fontWeight: '700',
              fontSize: '11px',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: activeTab === 'matches' ? '0 4px 16px rgba(16, 185, 129, 0.5), inset 0 1px 0 rgba(255,255,255,0.2)' : 'none',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              opacity: activeTab === 'matches' ? 1 : 0.6
            }}
          >
            ✓ Emparejados
          </button>
          <button
            onClick={() => setActiveTab('pending')}
            style={{
              padding: '6px 16px',
              borderRadius: '16px',
              border: activeTab === 'pending' ? '2px solid #f59e0b' : '2px solid rgba(255,255,255,0.15)',
              background: activeTab === 'pending' ? 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)' : 'rgba(0,0,0,0.3)',
              color: 'white',
              cursor: 'pointer',
              fontWeight: '700',
              fontSize: '11px',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: activeTab === 'pending' ? '0 4px 16px rgba(245, 158, 11, 0.5), inset 0 1px 0 rgba(255,255,255,0.2)' : 'none',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              opacity: activeTab === 'pending' ? 1 : 0.6
            }}
          >
            ⧗ Pendientes
          </button>
        </div>
      </div>

      {/* Content Container */}
      <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '1rem', padding: '1.5rem', maxHeight: '600px', overflowY: 'auto' }}>

        {activeTab === 'matches' ? (
          <MatchesList
            matches={getMatches()}
            justifications={justifications}
            setJustifications={setJustifications}
          />
        ) : (
          <PendingList items={getPending()} />
        )}
      </div>
    </div>
  );
}

function MatchesList({ matches, justifications, setJustifications }) {
  const [collapsedCards, setCollapsedCards] = useState(() => {
    // Initialize all cards as collapsed (true)
    const initial = {};
    matches.forEach((set, i) => {
      initial[i] = true;
    });
    return initial;
  });

  const [expandedRows, setExpandedRows] = useState({});
  const [filterMethod, setFilterMethod] = useState('all'); // all, Reference, Exact, CombinedAmount, DateProximity, FIFO, Unallocated
  const [showOnlyUnjustified, setShowOnlyUnjustified] = useState(false);

  const toggleCard = (index) => {
    setCollapsedCards(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const toggleRowDetails = (cardIndex, rowIndex) => {
    const key = `${cardIndex}-${rowIndex}`;
    setExpandedRows(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  const justificationOptions = [
    { value: '', label: 'Sin justificar' },
    { value: 'prev_quarter', label: 'Factura trimestre anterior' },
    { value: 'next_quarter', label: 'Factura trimestre posterior' },
    { value: 'advance_payment', label: 'Pago anticipado' },
    { value: 'credit_note', label: 'Nota de crédito' },
    { value: 'other', label: 'Otro (revisar)' }
  ];

  // Apply filters
  const filteredMatches = matches.filter(set => {
    // Check if set has unjustified payments
    if (showOnlyUnjustified) {
      const hasUnjustified = set.some(r => {
        const rowKey = `${r.SetID}-${r.PagoKey}`;
        const justification = justifications[rowKey];
        return r.MatchMethod === 'Unallocated' && (!justification || justification === '');
      });
      if (!hasUnjustified) return false;
    }

    // Filter by method
    if (filterMethod !== 'all') {
      const hasMethod = set.some(r => r.MatchMethod === filterMethod);
      if (!hasMethod) return false;
    }

    return true;
  });

  if (matches.length === 0) return <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No se encontraron emparejamientos.</div>;

  return (
    <div>
      {/* Filter Controls */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '1.5rem',
        marginBottom: '1.5rem',
        padding: '1rem',
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '0.5rem',
        flexWrap: 'wrap'
      }}>
        {/* Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Método:</label>
          <select
            value={filterMethod}
            onChange={(e) => setFilterMethod(e.target.value)}
            style={{
              padding: '0.3rem 0.5rem',
              borderRadius: '0.25rem',
              background: 'rgba(255,255,255,0.1)',
              color: 'white',
              border: '1px solid rgba(255,255,255,0.2)',
              fontSize: '0.75rem'
            }}
          >
            <option value="all">Todos</option>
            <option value="Reference">Referencia</option>
            <option value="Exact">Exacto</option>
            <option value="CombinedAmount">Import Combinat</option>
            <option value="DateProximity">Proximidad Fecha</option>
            <option value="FIFO">FIFO</option>
            <option value="Unallocated">Sin asignar</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input
            type="checkbox"
            id="showUnjustified"
            checked={showOnlyUnjustified}
            onChange={(e) => setShowOnlyUnjustified(e.target.checked)}
          />
          <label htmlFor="showUnjustified" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', cursor: 'pointer' }}>
            Solo sin justificar
          </label>
        </div>

        <div style={{ marginLeft: 'auto', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Mostrando {filteredMatches.length} de {matches.length} grupos
        </div>
      </div>

      <div style={{ display: 'grid', gap: '1.5rem' }}>
      {filteredMatches.slice(0, 100).map((set, cardIndex) => {
        const tercero = set[0].Tercero;

        // Group data by invoices (DocKey) and their payments
        const invoiceMap = {};
        const unmatchedPayments = [];

        set.forEach(row => {
          if (row.DocKey && !row.PagoKey) {
            // Pure invoice (not yet matched)
            if (!invoiceMap[row.DocKey]) {
              invoiceMap[row.DocKey] = {
                invoice: row,
                payments: []
              };
            }
          } else if (row.DocKey && row.PagoKey) {
            // Matched invoice-payment pair
            if (!invoiceMap[row.DocKey]) {
              invoiceMap[row.DocKey] = {
                invoice: row,
                payments: []
              };
            }
            invoiceMap[row.DocKey].payments.push(row);
          } else if (!row.DocKey && row.PagoKey) {
            // Unmatched payment
            unmatchedPayments.push(row);
          }
        });

        // Calculate totals and status
        const invoiceRows = set.filter(r => r.DocKey && r.PagoKey);
        const totalPaid = invoiceRows.reduce((sum, row) => sum + Math.abs(row.Asignado || 0), 0);
        const totalPending = invoiceRows.reduce((sum, row) => sum + (row.ResidualFacturaTras || 0), 0);
        const hasUnmatched = unmatchedPayments.length > 0;
        const hasPartial = set.some(r => r.ResidualFacturaTras > 0.01);
        const numInvoices = Object.keys(invoiceMap).length;
        const numPayments = unmatchedPayments.length + invoiceRows.length;

        // Determine overall status
        const hasJustification = unmatchedPayments.some(r => {
          const rowKey = `${r.SetID}-${r.PagoKey}`;
          return justifications[rowKey] && justifications[rowKey] !== '' && justifications[rowKey] !== 'other';
        });

        let statusColor, statusBg, statusText, statusIcon;
        if (hasUnmatched && hasJustification) {
          statusColor = '#10B981';
          statusBg = 'rgba(16, 185, 129, 0.15)';
          statusText = 'Justificado';
          statusIcon = '🟢';
        } else if (hasUnmatched) {
          statusColor = '#EF4444';
          statusBg = 'rgba(239, 68, 68, 0.15)';
          statusText = 'Sin Factura';
          statusIcon = '🔴';
        } else if (hasPartial || totalPending > 0.01) {
          statusColor = '#F59E0B';
          statusBg = 'rgba(245, 158, 11, 0.15)';
          statusText = 'Pago Parcial';
          statusIcon = '🟠';
        } else {
          statusColor = '#10B981';
          statusBg = 'rgba(16, 185, 129, 0.15)';
          statusText = 'Totalmente Pagado';
          statusIcon = '🟢';
        }

        return (
          <div key={cardIndex} style={{
            background: 'rgba(0,0,0,0.3)',
            borderRadius: '12px',
            padding: '1.5rem',
            border: `3px solid ${statusColor}`,
            boxShadow: `0 0 20px ${statusColor}40`
          }}>
            {/* Header - Clickable */}
            <div
              onClick={() => toggleCard(cardIndex)}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: collapsedCards[cardIndex] ? '0' : '1.25rem',
                paddingBottom: collapsedCards[cardIndex] ? '0' : '1rem',
                borderBottom: collapsedCards[cardIndex] ? 'none' : `2px solid ${statusColor}60`,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                userSelect: 'none'
              }}
              onMouseEnter={(e) => e.currentTarget.style.opacity = '0.8'}
              onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                {/* Expand/Collapse Indicator */}
                <div style={{
                  color: statusColor,
                  fontSize: '1.2rem',
                  fontWeight: '700',
                  transition: 'transform 0.2s ease',
                  transform: collapsedCards[cardIndex] ? 'rotate(0deg)' : 'rotate(90deg)'
                }}>
                  ▶
                </div>
                {/* Company Name */}
                <span style={{ fontWeight: 'bold', color: '#e2e8f0', fontSize: '1.1rem' }}>{tercero}</span>
              </div>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', gap: '0.5rem' }}>
                  <span style={{
                    color: '#3B82F6',
                    fontWeight: '700',
                    background: 'rgba(59, 130, 246, 0.15)',
                    padding: '2px 8px',
                    borderRadius: '4px'
                  }}>{numInvoices} Facturas</span>
                  <span style={{
                    color: '#EC4899',
                    fontWeight: '700',
                    background: 'rgba(236, 72, 153, 0.15)',
                    padding: '2px 8px',
                    borderRadius: '4px'
                  }}>{numPayments} Pagos</span>
                </div>
              </div>
            </div>

            {/* Content - Grouped by Invoices */}
            {!collapsedCards[cardIndex] && (
              <>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {/* Invoices with their payments */}
                  {Object.entries(invoiceMap).map(([docKey, { invoice, payments }], invoiceIndex) => {
                    const invoiceTotal = invoice.Asignado || 0;
                    const totalPaid = payments.reduce((sum, p) => sum + Math.abs(p.Asignado || 0), 0);
                    const residual = invoice.ResidualFacturaTras || 0;
                    const isPartial = residual > 0.01;
                    const rowKey = `${cardIndex}-invoice-${invoiceIndex}`;
                    const isExpanded = expandedRows[rowKey];

                    return (
                      <div key={docKey} style={{
                        background: isPartial ? 'rgba(245, 158, 11, 0.08)' : 'rgba(16, 185, 129, 0.08)',
                        borderRadius: '8px',
                        border: isPartial ? '2px solid #F59E0B' : '2px solid #10B981',
                        overflow: 'hidden'
                      }}>
                        {/* Invoice Header */}
                        <div
                          onClick={() => toggleRowDetails(cardIndex, `invoice-${invoiceIndex}`)}
                          style={{
                            padding: '0.75rem 1rem',
                            background: isPartial ? 'rgba(245, 158, 11, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                            cursor: 'pointer',
                            display: 'grid',
                            gridTemplateColumns: '30px 1fr auto auto',
                            gap: '1rem',
                            alignItems: 'center',
                            transition: 'all 0.2s ease'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.opacity = '0.8'}
                          onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                        >
                          <div style={{
                            fontSize: '0.9rem',
                            transition: 'transform 0.2s ease',
                            transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                            color: isPartial ? '#F59E0B' : '#10B981'
                          }}>▶</div>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <span style={{
                                fontSize: '0.65rem',
                                fontWeight: '700',
                                color: '#3B82F6',
                                background: 'rgba(59, 130, 246, 0.15)',
                                padding: '3px 8px',
                                borderRadius: '3px',
                                border: '1px solid #3B82F6',
                                textTransform: 'uppercase'
                              }}>📄 Factura</span>
                              <span style={{ fontSize: '0.85rem', fontWeight: '600', color: '#e2e8f0' }}>
                                {docKey.split('|')[1]}
                              </span>
                            </div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                              Fecha: {invoice.Fecha_doc}
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '2px' }}>Importe</div>
                            <div style={{ fontSize: '0.9rem', fontWeight: '700', color: '#3B82F6' }}>
                              {Math.abs(invoiceTotal).toFixed(2)} €
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '2px' }}>Pendiente</div>
                            <div style={{
                              fontSize: '0.9rem',
                              fontWeight: '700',
                              color: isPartial ? '#EF4444' : '#10B981'
                            }}>
                              {residual.toFixed(2)} €
                            </div>
                          </div>
                        </div>

                        {/* Expanded Invoice Details */}
                        {isExpanded && (
                          <div style={{
                            padding: '0.75rem 1rem',
                            background: 'rgba(0,0,0,0.2)',
                            fontSize: '0.75rem',
                            borderTop: '1px solid rgba(255,255,255,0.1)'
                          }}>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
                              <div><strong>Cuenta:</strong> {invoice.Cuenta_doc || '-'}</div>
                              <div><strong>Tercero:</strong> {invoice.Tercero}</div>
                              <div><strong>Documento:</strong> {invoice.Documento_doc || '-'}</div>
                              <div><strong>Concepto:</strong> {invoice.Concepto_doc || '-'}</div>
                            </div>
                          </div>
                        )}

                        {/* Payments for this invoice */}
                        {payments.length > 0 && (
                          <div style={{ padding: '0 1rem 0.75rem 1rem' }}>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '0.5rem', marginLeft: '30px' }}>
                              💳 Pagos asociados ({payments.length}):
                            </div>
                            {payments.map((payment, payIdx) => {
                              const paymentKey = `${cardIndex}-payment-${invoiceIndex}-${payIdx}`;
                              const isPayExpanded = expandedRows[paymentKey];

                              return (
                                <div key={payIdx} style={{
                                  marginLeft: '30px',
                                  marginBottom: '0.5rem',
                                  background: 'rgba(0,0,0,0.2)',
                                  borderRadius: '6px',
                                  border: '1px solid rgba(255,255,255,0.1)',
                                  overflow: 'hidden'
                                }}>
                                  <div
                                    onClick={() => toggleRowDetails(cardIndex, `payment-${invoiceIndex}-${payIdx}`)}
                                    style={{
                                      padding: '0.5rem 0.75rem',
                                      cursor: 'pointer',
                                      display: 'grid',
                                      gridTemplateColumns: '20px auto 1fr auto auto',
                                      gap: '0.75rem',
                                      alignItems: 'center',
                                      transition: 'all 0.2s ease'
                                    }}
                                    onMouseEnter={(e) => e.currentTarget.style.opacity = '0.8'}
                                    onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                                  >
                                    <div style={{
                                      fontSize: '0.7rem',
                                      transition: 'transform 0.2s ease',
                                      transform: isPayExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                                      color: '#EC4899'
                                    }}>▶</div>
                                    <span style={{
                                      fontSize: '0.6rem',
                                      fontWeight: '700',
                                      padding: '2px 6px',
                                      borderRadius: '3px',
                                      background:
                                        payment.MatchMethod === 'Reference' ? 'rgba(16, 185, 129, 0.2)' :
                                          payment.MatchMethod === 'Exact' ? 'rgba(16, 185, 129, 0.2)' :
                                            payment.MatchMethod === 'CombinedAmount' ? 'rgba(251, 146, 60, 0.2)' :
                                              payment.MatchMethod === 'DateProximity' ? 'rgba(59, 130, 246, 0.2)' :
                                                'rgba(168, 85, 247, 0.2)',
                                      color:
                                        payment.MatchMethod === 'Reference' ? '#10B981' :
                                          payment.MatchMethod === 'Exact' ? '#10B981' :
                                            payment.MatchMethod === 'CombinedAmount' ? '#FB923C' :
                                              payment.MatchMethod === 'DateProximity' ? '#3B82F6' :
                                                '#A855F7',
                                      border: `1px solid ${payment.MatchMethod === 'Reference' ? '#10B981' :
                                        payment.MatchMethod === 'Exact' ? '#10B981' :
                                          payment.MatchMethod === 'CombinedAmount' ? '#FB923C' :
                                            payment.MatchMethod === 'DateProximity' ? '#3B82F6' :
                                              '#A855F7'
                                        }`,
                                      textTransform: 'uppercase'
                                    }}>
                                      {payment.MatchMethod}
                                    </span>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                                      <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#EC4899' }}>
                                        {payment.PagoKey ? payment.PagoKey.split('|')[1] : '-'}
                                      </div>
                                      <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                                        {payment.Fecha_pago}
                                      </div>
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                      <div style={{
                                        fontSize: '0.8rem',
                                        fontWeight: '700',
                                        color: '#EC4899'
                                      }}>
                                        {Math.abs(payment.Asignado || 0).toFixed(2)} €
                                      </div>
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                      {payment.ResidualFacturaTras !== null && payment.ResidualFacturaTras !== undefined ? (
                                        <div style={{
                                          fontSize: '0.75rem',
                                          fontWeight: '700',
                                          color: payment.ResidualFacturaTras > 0.01 ? '#EF4444' : '#10B981'
                                        }}>
                                          Resta: {payment.ResidualFacturaTras.toFixed(2)} €
                                        </div>
                                      ) : null}
                                    </div>
                                  </div>

                                  {/* Expanded Payment Details */}
                                  {isPayExpanded && (
                                    <div style={{
                                      padding: '0.5rem 0.75rem',
                                      background: 'rgba(0,0,0,0.3)',
                                      fontSize: '0.7rem',
                                      borderTop: '1px solid rgba(255,255,255,0.1)'
                                    }}>
                                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.4rem' }}>
                                        <div><strong>Cuenta:</strong> {payment.Cuenta_pago || '-'}</div>
                                        <div><strong>Documento:</strong> {payment.Documento_pago || '-'}</div>
                                        <div style={{ gridColumn: '1 / -1' }}><strong>Concepto:</strong> {payment.Concepto_pago || '-'}</div>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {/* Unmatched Payments Section */}
                  {unmatchedPayments.length > 0 && (
                    <div style={{
                      background: 'rgba(239, 68, 68, 0.08)',
                      borderRadius: '8px',
                      border: '2px solid #EF4444',
                      padding: '1rem'
                    }}>
                      <div style={{
                        fontSize: '0.85rem',
                        fontWeight: '700',
                        color: '#EF4444',
                        marginBottom: '0.75rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em'
                      }}>
                        ⚠️ Pagos sin factura ({unmatchedPayments.length})
                      </div>
                      {unmatchedPayments.map((payment, payIdx) => {
                        const rowKey = `${payment.SetID}-${payment.PagoKey}`;
                        const rowJustification = justifications[rowKey] || '';
                        const isJustified = rowJustification && rowJustification !== '' && rowJustification !== 'other';
                        const unmatchedPayKey = `${cardIndex}-unmatched-${payIdx}`;
                        const isPayExpanded = expandedRows[unmatchedPayKey];

                        return (
                          <div key={payIdx} style={{
                            marginBottom: '0.5rem',
                            background: isJustified ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.15)',
                            borderRadius: '6px',
                            border: isJustified ? '2px solid #10B981' : '2px solid #EF4444',
                            overflow: 'hidden'
                          }}>
                            <div
                              onClick={() => toggleRowDetails(cardIndex, `unmatched-${payIdx}`)}
                              style={{
                                padding: '0.5rem 0.75rem',
                                cursor: 'pointer',
                                display: 'grid',
                                gridTemplateColumns: '20px 1fr auto auto',
                                gap: '0.75rem',
                                alignItems: 'center',
                                transition: 'all 0.2s ease'
                              }}
                              onMouseEnter={(e) => e.currentTarget.style.opacity = '0.8'}
                              onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                            >
                              <div style={{
                                fontSize: '0.7rem',
                                transition: 'transform 0.2s ease',
                                transform: isPayExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                                color: isJustified ? '#10B981' : '#EF4444'
                              }}>▶</div>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#EF4444' }}>
                                  💸 {payment.PagoKey ? payment.PagoKey.split('|')[1] : '-'}
                                </div>
                                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                                  {payment.Fecha_pago}
                                </div>
                              </div>
                              <div style={{ textAlign: 'right' }}>
                                <div style={{
                                  fontSize: '0.8rem',
                                  fontWeight: '700',
                                  color: '#EF4444'
                                }}>
                                  {Math.abs(payment.Asignado || 0).toFixed(2)} €
                                </div>
                              </div>
                              <div style={{ minWidth: '150px' }}>
                                <select
                                  value={rowJustification}
                                  onChange={(e) => {
                                    e.stopPropagation();
                                    const newJustifications = { ...justifications };
                                    if (e.target.value === '') {
                                      delete newJustifications[rowKey];
                                    } else {
                                      newJustifications[rowKey] = e.target.value;
                                    }
                                    setJustifications(newJustifications);
                                  }}
                                  onClick={(e) => e.stopPropagation()}
                                  style={{
                                    padding: '4px 8px',
                                    borderRadius: '4px',
                                    border: `1px solid ${isJustified ? '#10B981' : '#EF4444'}`,
                                    background: 'rgba(0,0,0,0.3)',
                                    color: 'white',
                                    fontSize: '0.7rem',
                                    fontWeight: '600',
                                    cursor: 'pointer',
                                    width: '100%',
                                    outline: 'none'
                                  }}
                                >
                                  {justificationOptions.map(opt => (
                                    <option key={opt.value} value={opt.value} style={{ background: '#1e293b', color: 'white' }}>
                                      {opt.label}
                                    </option>
                                  ))}
                                </select>
                              </div>
                            </div>

                            {/* Expanded Unmatched Payment Details */}
                            {isPayExpanded && (
                              <div style={{
                                padding: '0.5rem 0.75rem',
                                background: 'rgba(0,0,0,0.3)',
                                fontSize: '0.7rem',
                                borderTop: '1px solid rgba(255,255,255,0.1)'
                              }}>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.4rem' }}>
                                  <div><strong>Cuenta:</strong> {payment.Cuenta_pago || '-'}</div>
                                  <div><strong>Documento:</strong> {payment.Documento_pago || '-'}</div>
                                  <div style={{ gridColumn: '1 / -1' }}><strong>Concepto:</strong> {payment.Concepto_pago || '-'}</div>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Summary Footer */}
                <div style={{
                  marginTop: '1.5rem',
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
              </>
            )}
          </div>
        );
      })}
      {filteredMatches.length > 100 && (
        <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-muted)' }}>
          ... y {filteredMatches.length - 100} grupos más (descarga el Excel para ver todos)
        </div>
      )}
      </div>
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

