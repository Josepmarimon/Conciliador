import React from 'react';
import { X, CheckCircle, ArrowRight, Search, DollarSign, Calendar } from 'lucide-react';

function HelpModal({ isOpen, onClose }) {
    if (!isOpen) return null;

    return (
        <div style={{
            background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
            borderRadius: '1rem',
            width: '100%',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)'
        }}>
            {/* Header */}
            <div style={{
                padding: '2rem',
                borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <div>
                    <h2 style={{ fontSize: '1.75rem', fontWeight: '700', margin: 0, color: 'white' }}>
                        Sistema de Conciliación Automática
                    </h2>
                    <p style={{ fontSize: '0.95rem', color: 'var(--color-label-secondary)', margin: '0.5rem 0 0 0' }}>
                        Guía profesional de funcionamiento
                    </p>
                </div>
                <button
                    onClick={onClose}
                    style={{
                        background: 'rgba(255, 255, 255, 0.1)',
                        border: 'none',
                        borderRadius: '50%',
                        width: '40px',
                        height: '40px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                        color: 'white'
                    }}
                    onMouseEnter={(e) => e.target.style.background = 'rgba(255, 255, 255, 0.2)'}
                    onMouseLeave={(e) => e.target.style.background = 'rgba(255, 255, 255, 0.1)'}
                >
                    <X size={20} />
                </button>
            </div>

                {/* Content */}
                <div style={{ padding: '2rem' }}>
                    {/* Intro */}
                    <div style={{
                        background: 'rgba(59, 130, 246, 0.1)',
                        border: '1px solid rgba(59, 130, 246, 0.3)',
                        borderRadius: '0.75rem',
                        padding: '1.5rem',
                        marginBottom: '2rem'
                    }}>
                        <h3 style={{ fontSize: '1.1rem', fontWeight: '600', margin: '0 0 0.75rem 0', color: '#60A5FA' }}>
                            ¿Cómo funciona la conciliación?
                        </h3>
                        <p style={{ fontSize: '0.95rem', lineHeight: '1.6', color: '#cbd5e1', margin: 0 }}>
                            El sistema empareja automáticamente <strong>facturas</strong> (importes positivos) con <strong>pagos</strong> (importes negativos)
                            utilizando un algoritmo inteligente en <strong>3 fases secuenciales</strong>. Cada fase tiene un método diferente para
                            encontrar la mejor coincidencia. Los resultados se organizan por <strong>Clientes (AR)</strong> y <strong>Proveedores (AP)</strong>,
                            mostrando tanto los emparejamientos exitosos como los pendientes que requieren atención.
                        </p>
                    </div>

                    {/* Phase 1 */}
                    <div style={{ marginBottom: '2rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                            <div style={{
                                background: 'linear-gradient(135deg, #10b981 0%, #34d399 100%)',
                                borderRadius: '8px',
                                width: '36px',
                                height: '36px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontWeight: '700',
                                fontSize: '1.1rem'
                            }}>1</div>
                            <h3 style={{ fontSize: '1.25rem', fontWeight: '600', margin: 0, color: 'white' }}>
                                🔗 Emparejamiento por Referencia
                            </h3>
                        </div>

                        <div style={{
                            background: 'rgba(0, 0, 0, 0.3)',
                            borderRadius: '0.75rem',
                            padding: '1.5rem',
                            borderLeft: '4px solid #10b981'
                        }}>
                            <p style={{ fontSize: '0.95rem', lineHeight: '1.6', color: '#cbd5e1', marginBottom: '1rem' }}>
                                Busca el <strong>número de documento de la factura</strong> dentro del concepto o descripción del pago.
                                Requiere al menos 3 caracteres para evitar coincidencias falsas.
                            </p>

                            <div style={{
                                background: 'rgba(16, 185, 129, 0.1)',
                                border: '1px solid rgba(16, 185, 129, 0.3)',
                                borderRadius: '0.5rem',
                                padding: '1rem',
                                fontFamily: 'monospace',
                                fontSize: '0.85rem'
                            }}>
                                <div style={{ color: '#34d399', marginBottom: '0.5rem' }}>✓ Ejemplo:</div>
                                <div style={{ color: '#94a3b8', marginBottom: '0.25rem' }}>
                                    <strong>Factura:</strong> "FAC-2024-00123" → 1,500.00 €
                                </div>
                                <div style={{ color: '#94a3b8', marginBottom: '0.5rem' }}>
                                    <strong>Pago concepto:</strong> "Pago factura FAC-2024-00123"
                                </div>
                                <div style={{ color: '#10b981', fontWeight: '600' }}>
                                    → ✅ MATCH por Reference (1,500.00 €)
                                </div>
                            </div>

                            <div style={{
                                marginTop: '1rem',
                                padding: '0.75rem',
                                background: 'rgba(59, 130, 246, 0.1)',
                                borderRadius: '0.5rem',
                                fontSize: '0.85rem',
                                color: '#93c5fd'
                            }}>
                                <strong>💡 Ventaja:</strong> La más precisa cuando el concepto del pago incluye el número de factura
                            </div>
                        </div>
                    </div>

                    {/* Phase 2 */}
                    <div style={{ marginBottom: '2rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                            <div style={{
                                background: 'linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%)',
                                borderRadius: '8px',
                                width: '36px',
                                height: '36px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontWeight: '700',
                                fontSize: '1.1rem'
                            }}>2</div>
                            <h3 style={{ fontSize: '1.25rem', fontWeight: '600', margin: 0, color: 'white' }}>
                                💯 Emparejamiento Exacto
                            </h3>
                        </div>

                        <div style={{
                            background: 'rgba(0, 0, 0, 0.3)',
                            borderRadius: '0.75rem',
                            padding: '1.5rem',
                            borderLeft: '4px solid #3b82f6'
                        }}>
                            <p style={{ fontSize: '0.95rem', lineHeight: '1.6', color: '#cbd5e1', marginBottom: '1rem' }}>
                                Busca una factura cuyo <strong>importe pendiente coincida exactamente</strong> con el importe del pago
                                (dentro de la tolerancia configurada). Si hay varias coincidencias, selecciona la más antigua.
                            </p>

                            <div style={{
                                background: 'rgba(59, 130, 246, 0.1)',
                                border: '1px solid rgba(59, 130, 246, 0.3)',
                                borderRadius: '0.5rem',
                                padding: '1rem',
                                fontFamily: 'monospace',
                                fontSize: '0.85rem'
                            }}>
                                <div style={{ color: '#60a5fa', marginBottom: '0.5rem' }}>✓ Ejemplo:</div>
                                <div style={{ color: '#94a3b8', marginBottom: '0.25rem' }}>
                                    <strong>Factura A:</strong> 1,250.00 € pendiente
                                </div>
                                <div style={{ color: '#94a3b8', marginBottom: '0.25rem' }}>
                                    <strong>Factura B:</strong> 1,500.00 € pendiente
                                </div>
                                <div style={{ color: '#94a3b8', marginBottom: '0.5rem' }}>
                                    <strong>Pago:</strong> 1,500.00 €
                                </div>
                                <div style={{ color: '#3b82f6', fontWeight: '600' }}>
                                    → ✅ MATCH con Factura B por "Exact" (1,500.00 €)
                                </div>
                            </div>

                            <div style={{
                                marginTop: '1rem',
                                padding: '0.75rem',
                                background: 'rgba(59, 130, 246, 0.1)',
                                borderRadius: '0.5rem',
                                fontSize: '0.85rem',
                                color: '#93c5fd'
                            }}>
                                <strong>💡 Ventaja:</strong> Ideal cuando los pagos se hacen por el importe exacto de la factura
                            </div>
                        </div>
                    </div>

                    {/* Phase 3 */}
                    <div style={{ marginBottom: '2rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                            <div style={{
                                background: 'linear-gradient(135deg, #a855f7 0%, #c084fc 100%)',
                                borderRadius: '8px',
                                width: '36px',
                                height: '36px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontWeight: '700',
                                fontSize: '1.1rem'
                            }}>3</div>
                            <h3 style={{ fontSize: '1.25rem', fontWeight: '600', margin: 0, color: 'white' }}>
                                ⏰ Emparejamiento FIFO
                            </h3>
                        </div>

                        <div style={{
                            background: 'rgba(0, 0, 0, 0.3)',
                            borderRadius: '0.75rem',
                            padding: '1.5rem',
                            borderLeft: '4px solid #a855f7'
                        }}>
                            <p style={{ fontSize: '0.95rem', lineHeight: '1.6', color: '#cbd5e1', marginBottom: '1rem' }}>
                                <strong>First In, First Out:</strong> Aplica el pago a las facturas más antiguas primero, en orden cronológico.
                                Es el método de <strong>fallback</strong> cuando no hay referencia ni coincidencia exacta. Puede aplicar
                                un pago a múltiples facturas.
                            </p>

                            <div style={{
                                background: 'rgba(168, 85, 247, 0.1)',
                                border: '1px solid rgba(168, 85, 247, 0.3)',
                                borderRadius: '0.5rem',
                                padding: '1rem',
                                fontFamily: 'monospace',
                                fontSize: '0.85rem'
                            }}>
                                <div style={{ color: '#c084fc', marginBottom: '0.5rem' }}>✓ Ejemplo de Pago Parcial Múltiple:</div>
                                <div style={{ color: '#94a3b8', marginBottom: '0.25rem' }}>
                                    <strong>Factura A</strong> (15/01/2024): 800.00 € pendiente
                                </div>
                                <div style={{ color: '#94a3b8', marginBottom: '0.25rem' }}>
                                    <strong>Factura B</strong> (20/01/2024): 500.00 € pendiente
                                </div>
                                <div style={{ color: '#94a3b8', marginBottom: '0.5rem' }}>
                                    <strong>Pago:</strong> 1,000.00 €
                                </div>
                                <div style={{ color: '#a855f7', fontWeight: '600', marginBottom: '0.25rem' }}>
                                    → ✅ 800.00 € a Factura A (FIFO) - Totalmente Pagada ✓
                                </div>
                                <div style={{ color: '#a855f7', fontWeight: '600' }}>
                                    → ✅ 200.00 € a Factura B (FIFO) - Queda 300.00 € pendiente
                                </div>
                            </div>

                            <div style={{
                                marginTop: '1rem',
                                padding: '0.75rem',
                                background: 'rgba(59, 130, 246, 0.1)',
                                borderRadius: '0.5rem',
                                fontSize: '0.85rem',
                                color: '#93c5fd'
                            }}>
                                <strong>💡 Ventaja:</strong> Garantiza que las facturas más antiguas se cobren primero
                            </div>
                        </div>
                    </div>

                    {/* Priority Order */}
                    <div style={{
                        background: 'rgba(245, 158, 11, 0.1)',
                        border: '1px solid rgba(245, 158, 11, 0.3)',
                        borderRadius: '0.75rem',
                        padding: '1.5rem',
                        marginBottom: '2rem'
                    }}>
                        <h3 style={{ fontSize: '1.1rem', fontWeight: '600', margin: '0 0 1rem 0', color: '#fbbf24' }}>
                            📋 Orden de Prioridad del Algoritmo
                        </h3>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.95rem', color: '#cbd5e1' }}>
                            <div style={{ background: 'rgba(16, 185, 129, 0.2)', padding: '0.5rem 1rem', borderRadius: '0.5rem', fontWeight: '600' }}>
                                1. Reference
                            </div>
                            <ArrowRight size={20} color="#fbbf24" />
                            <div style={{ background: 'rgba(59, 130, 246, 0.2)', padding: '0.5rem 1rem', borderRadius: '0.5rem', fontWeight: '600' }}>
                                2. Exact
                            </div>
                            <ArrowRight size={20} color="#fbbf24" />
                            <div style={{ background: 'rgba(168, 85, 247, 0.2)', padding: '0.5rem 1rem', borderRadius: '0.5rem', fontWeight: '600' }}>
                                3. FIFO
                            </div>
                        </div>
                    </div>

                    {/* UI Navigation */}
                    <div style={{ marginBottom: '2rem' }}>
                        <h3 style={{ fontSize: '1.25rem', fontWeight: '600', margin: '0 0 1rem 0', color: 'white' }}>
                            🎯 Navegación de la Interfaz
                        </h3>

                        <div style={{
                            background: 'rgba(0, 0, 0, 0.3)',
                            borderRadius: '0.75rem',
                            padding: '1.5rem',
                            borderLeft: '4px solid #06b6d4'
                        }}>
                            <p style={{ fontSize: '0.95rem', lineHeight: '1.6', color: '#cbd5e1', marginBottom: '1rem' }}>
                                La interfaz organiza los resultados en dos niveles de navegación:
                            </p>

                            <div style={{ marginBottom: '1rem' }}>
                                <div style={{ fontSize: '0.9rem', fontWeight: '600', color: '#60a5fa', marginBottom: '0.5rem' }}>
                                    📂 Nivel 1: Tipo de Cuenta
                                </div>
                                <div style={{ paddingLeft: '1rem', fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.6' }}>
                                    • <strong>Clientes (AR)</strong>: Cuentas por cobrar - Facturas emitidas y pagos recibidos<br/>
                                    • <strong>Proveedores (AP)</strong>: Cuentas por pagar - Facturas recibidas y pagos realizados
                                </div>
                            </div>

                            <div>
                                <div style={{ fontSize: '0.9rem', fontWeight: '600', color: '#10b981', marginBottom: '0.5rem' }}>
                                    📋 Nivel 2: Estado de Emparejamiento
                                </div>
                                <div style={{ paddingLeft: '1rem', fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.6' }}>
                                    • <strong>✓ Emparejados</strong>: Pagos que se han vinculado exitosamente con facturas<br/>
                                    &nbsp;&nbsp;- Agrupados por tercero (cliente/proveedor)<br/>
                                    &nbsp;&nbsp;- Facturas expandibles con sus pagos asociados<br/>
                                    &nbsp;&nbsp;- Filtros por método de emparejamiento<br/>
                                    • <strong>⧗ Pendientes</strong>: Facturas que aún tienen saldo por cobrar/pagar<br/>
                                    &nbsp;&nbsp;- Ordenadas por antigüedad (días pendientes)<br/>
                                    &nbsp;&nbsp;- Requieren seguimiento o gestión de cobro/pago
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Special States */}
                    <div style={{ marginBottom: '2rem' }}>
                        <h3 style={{ fontSize: '1.25rem', fontWeight: '600', margin: '0 0 1rem 0', color: 'white' }}>
                            📊 Estados y Códigos de Color
                        </h3>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                            <div style={{
                                background: 'rgba(245, 158, 11, 0.1)',
                                border: '1px solid rgba(245, 158, 11, 0.3)',
                                borderRadius: '0.5rem',
                                padding: '1rem'
                            }}>
                                <div style={{ fontSize: '1rem', fontWeight: '600', color: '#fbbf24', marginBottom: '0.5rem' }}>
                                    🟠 Pago Parcial
                                </div>
                                <p style={{ fontSize: '0.85rem', color: '#cbd5e1', margin: 0 }}>
                                    Factura pagada parcialmente. El <strong>Residual Tras</strong> muestra el importe pendiente.
                                    Aparece en ambas vistas: Emparejados (como pago parcial) y Pendientes (con saldo restante).
                                </p>
                            </div>

                            <div style={{
                                background: 'rgba(239, 68, 68, 0.1)',
                                border: '1px solid rgba(239, 68, 68, 0.3)',
                                borderRadius: '0.5rem',
                                padding: '1rem'
                            }}>
                                <div style={{ fontSize: '1rem', fontWeight: '600', color: '#ef4444', marginBottom: '0.5rem' }}>
                                    🔴 Pago sin Factura
                                </div>
                                <p style={{ fontSize: '0.85rem', color: '#cbd5e1', margin: 0 }}>
                                    Pago que no encuentra factura. Aparece al final de la lista de emparejados.
                                    <strong>Requiere justificación manual</strong> para documentar el motivo.
                                </p>
                            </div>

                            <div style={{
                                background: 'rgba(16, 185, 129, 0.1)',
                                border: '1px solid rgba(16, 185, 129, 0.3)',
                                borderRadius: '0.5rem',
                                padding: '1rem'
                            }}>
                                <div style={{ fontSize: '1rem', fontWeight: '600', color: '#10b981', marginBottom: '0.5rem' }}>
                                    🟢 Totalmente Pagado
                                </div>
                                <p style={{ fontSize: '0.85rem', color: '#cbd5e1', margin: 0 }}>
                                    Factura completamente saldada. <strong>Residual = 0.00 €</strong>.
                                    No aparece en la vista de Pendientes.
                                </p>
                            </div>

                            <div style={{
                                background: 'rgba(59, 130, 246, 0.1)',
                                border: '1px solid rgba(59, 130, 246, 0.3)',
                                borderRadius: '0.5rem',
                                padding: '1rem'
                            }}>
                                <div style={{ fontSize: '1rem', fontWeight: '600', color: '#3b82f6', marginBottom: '0.5rem' }}>
                                    🟢 Justificado
                                </div>
                                <p style={{ fontSize: '0.85rem', color: '#cbd5e1', margin: 0 }}>
                                    Pago sin factura con <strong>justificación documentada</strong>. Opciones: Factura de otro trimestre,
                                    Pago anticipado, Nota de crédito, Otro.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Tips */}
                    <div style={{
                        background: 'rgba(139, 92, 246, 0.1)',
                        border: '1px solid rgba(139, 92, 246, 0.3)',
                        borderRadius: '0.75rem',
                        padding: '1.5rem'
                    }}>
                        <h3 style={{ fontSize: '1.1rem', fontWeight: '600', margin: '0 0 1rem 0', color: '#a78bfa' }}>
                            💡 Flujo de Trabajo Recomendado
                        </h3>
                        <ol style={{ margin: 0, paddingLeft: '1.5rem', color: '#cbd5e1', fontSize: '0.9rem', lineHeight: '1.8' }}>
                            <li><strong>Seleccione el archivo Excel</strong> con su contabilidad (arrastrando o haciendo clic)</li>
                            <li><strong>Configure parámetros</strong> si es necesario:
                                <ul style={{ marginTop: '0.5rem', marginBottom: '0.5rem' }}>
                                    <li>Tolerancia: 0.01 € (recomendado para evitar diferencias de redondeo)</li>
                                    <li>Prefijos de cuenta: 43 para Clientes (AR), 40 para Proveedores (AP)</li>
                                </ul>
                            </li>
                            <li><strong>Ejecute</strong> el análisis y revise el resumen inicial (totales, pendientes)</li>
                            <li><strong>Navegue por Clientes/Proveedores</strong> según lo que necesite analizar</li>
                            <li><strong>Revise Emparejados</strong>:
                                <ul style={{ marginTop: '0.5rem', marginBottom: '0.5rem' }}>
                                    <li>Expanda cada tercero para ver detalles de facturas y pagos</li>
                                    <li>Use filtros para revisar métodos específicos (Reference, Exact, FIFO)</li>
                                    <li><strong>Justifique pagos sin factura</strong> (en rojo) con el selector desplegable</li>
                                </ul>
                            </li>
                            <li><strong>Revise Pendientes</strong>:
                                <ul style={{ marginTop: '0.5rem', marginBottom: '0.5rem' }}>
                                    <li>Priorice por días pendientes (las más antiguas primero)</li>
                                    <li>Gestione cobros/pagos o identifique facturas problemáticas</li>
                                </ul>
                            </li>
                            <li><strong>Descargue el Excel</strong> con el resultado detallado para auditoría o archivo</li>
                        </ol>

                        <div style={{
                            marginTop: '1.5rem',
                            padding: '1rem',
                            background: 'rgba(245, 158, 11, 0.1)',
                            borderRadius: '0.5rem',
                            fontSize: '0.85rem',
                            color: '#fbbf24',
                            borderLeft: '3px solid #fbbf24'
                        }}>
                            <strong>⚠️ Importante:</strong> La barra lateral se puede ocultar/mostrar con el botón circular para maximizar
                            el espacio de visualización de datos.
                        </div>
                    </div>
                </div>
        </div>
    );
}

export default HelpModal;
