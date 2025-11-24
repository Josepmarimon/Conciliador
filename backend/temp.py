import streamlit as st, pandas as pd, numpy as np, tempfile, subprocess, sys
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Conciliador Clientes/Proveedores (FIFO)", layout="wide", page_icon="📊")

# Título con estilo
st.markdown("""
    <h1 style='text-align: center; color: #2E4057;'>
        📊 Conciliador Clientes/Proveedores (FIFO)
    </h1>
    <p style='text-align: center; color: #666;'>
        Conciliación automática de facturas y pagos usando método FIFO
    </p>
    """, unsafe_allow_html=True)

# Sidebar para configuración
with st.sidebar:
    st.header("⚙️ Configuración")
    tol = st.number_input("Tolerancia (euros)", min_value=0.0, value=0.01, step=0.01, format="%.2f")
    ar_prefix = st.text_input("Prefijo Clientes", value="43")
    ap_prefix = st.text_input("Prefijo Proveedores", value="4000")
    st.info("💡 **Consejo:** El prefijo debe coincidir con el inicio de las cuentas contables")

# Área principal
upl = st.file_uploader("📁 Sube el Excel de libro mayor", type=["xlsx"], help="Formato: 43x para clientes, 4000x para proveedores")

if upl is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(upl.read()); tmp.flush(); tmp_in = Path(tmp.name)
    script_path = Path(tempfile.gettempdir()) / "conciliador_fifo_stream.py"
    script_path.write_text(Path("conciliador_fifo.py").read_text(encoding="utf-8"), encoding="utf-8")
    out_path = tmp_in.with_name(tmp_in.stem + "_conciliado.xlsx")

    if st.button("🚀 Ejecutar conciliación", type="primary", use_container_width=True):
        with st.spinner("Procesando conciliación..."):
            cmd = [sys.executable, str(script_path), str(tmp_in), "--tol", str(tol),
                   "--ar-prefix", ar_prefix, "--ap-prefix", ap_prefix, "-o", str(out_path)]
            res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode != 0:
            st.error("❌ Error en la conciliación: " + res.stderr[:4000])
        else:
            st.success("✅ Conciliación completada exitosamente")

            # Botón de descarga destacado
            with open(out_path, "rb") as f:
                st.download_button(
                    "⬇️ Descargar Excel conciliado",
                    f,
                    file_name=out_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )

            # Visualización de resultados
            try:
                xls = pd.ExcelFile(out_path)

                # Resumen con métricas
                if "Resumen" in xls.sheet_names:
                    st.markdown("---")
                    st.header("📈 Resumen Ejecutivo")

                    resumen = pd.read_excel(out_path, sheet_name="Resumen")

                    # Métricas en columnas
                    col1, col2 = st.columns(2)

                    with col1:
                        st.subheader("👥 Clientes")
                        cliente_row = resumen[resumen['Bloque'] == 'Clientes'].iloc[0]
                        c1, c2, c3 = st.columns(3)
                        c1.metric("💰 Conciliado", f"€{cliente_row['Conciliado']:,.2f}", help="Total de facturas cobradas")
                        c2.metric("⚠️ Pendientes", f"{int(cliente_row['Facturas_pendientes'])}", help="Facturas sin cobrar")
                        c3.metric("🔍 Sin Factura", f"€{abs(cliente_row['Cobros_sin_factura']):,.2f}", help="Cobros sin factura asociada")

                    with col2:
                        st.subheader("🏢 Proveedores")
                        prov_row = resumen[resumen['Bloque'] == 'Proveedores'].iloc[0]
                        p1, p2, p3 = st.columns(3)
                        p1.metric("💰 Conciliado", f"€{prov_row['Conciliado']:,.2f}", help="Total de facturas pagadas")
                        p2.metric("⚠️ Pendientes", f"{int(prov_row['Facturas_pendientes'])}", help="Facturas sin pagar")
                        p3.metric("🔍 Sin Factura", f"€{abs(prov_row['Pagos_sin_factura']):,.2f}", help="Pagos sin factura asociada")

                    # Gráficos comparativos
                    st.markdown("---")
                    col_chart1, col_chart2 = st.columns(2)

                    with col_chart1:
                        # Gráfico de barras comparativo
                        fig_bar = go.Figure(data=[
                            go.Bar(name='Clientes', x=['Conciliado', 'Pendientes'],
                                   y=[cliente_row['Conciliado'], cliente_row['Facturas_pendientes']],
                                   marker_color='#4CAF50', text=[f"€{cliente_row['Conciliado']:,.0f}", f"{int(cliente_row['Facturas_pendientes'])}"],
                                   textposition='outside'),
                            go.Bar(name='Proveedores', x=['Conciliado', 'Pendientes'],
                                   y=[prov_row['Conciliado'], prov_row['Facturas_pendientes']],
                                   marker_color='#2196F3', text=[f"€{prov_row['Conciliado']:,.0f}", f"{int(prov_row['Facturas_pendientes'])}"],
                                   textposition='outside')
                        ])
                        fig_bar.update_layout(title='Comparación Clientes vs Proveedores', barmode='group', height=400)
                        st.plotly_chart(fig_bar, use_container_width=True)

                    with col_chart2:
                        # Gráfico de estado por tipo
                        estados_data = []
                        for sheet in ['Clientes_Detalle', 'Proveedores_Detalle']:
                            if sheet in xls.sheet_names:
                                df_det = pd.read_excel(out_path, sheet_name=sheet)
                                if 'Estado' in df_det.columns:
                                    tipo = 'Clientes' if 'Clientes' in sheet else 'Proveedores'
                                    counts = df_det['Estado'].value_counts()
                                    for estado, count in counts.items():
                                        estados_data.append({'Tipo': tipo, 'Estado': estado, 'Cantidad': count})

                        if estados_data:
                            df_estados = pd.DataFrame(estados_data)
                            fig_estados = px.bar(df_estados, x='Tipo', y='Cantidad', color='Estado',
                                               title='Distribución por Estado',
                                               color_discrete_map={
                                                   'CANCELADA': '#4CAF50',
                                                   'PENDIENTE': '#FF9800',
                                                   'PAGO SIN FACTURA': '#2196F3',
                                                   'PARCIAL': '#FFC107'
                                               }, height=400)
                            st.plotly_chart(fig_estados, use_container_width=True)

                # Tablas de pendientes y canceladas
                st.markdown("---")
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "✅ Canceladas Clientes",
                    "⚠️ Pendientes Clientes",
                    "✅ Canceladas Proveedores",
                    "⚠️ Pendientes Proveedores",
                    "📊 Análisis Multipago"
                ])

                with tab1:
                    if "Canceladas_Clientes" in xls.sheet_names:
                        canc_cli = pd.read_excel(out_path, sheet_name="Canceladas_Clientes")
                        if not canc_cli.empty:
                            st.success(f"✅ {len(canc_cli)} facturas de clientes emparejadas correctamente")
                            # Mostrar estadísticas de días hasta pago
                            if 'Dias_hasta_pago' in canc_cli.columns:
                                col_stats1, col_stats2, col_stats3 = st.columns(3)
                                col_stats1.metric("⏱️ Días promedio", f"{canc_cli['Dias_hasta_pago'].mean():.0f}")
                                col_stats2.metric("⚡ Pago más rápido", f"{canc_cli['Dias_hasta_pago'].min():.0f} días")
                                col_stats3.metric("🐌 Pago más lento", f"{canc_cli['Dias_hasta_pago'].max():.0f} días")
                            st.dataframe(canc_cli.head(50), use_container_width=True, height=400)
                            st.caption(f"Mostrando 50 de {len(canc_cli)} facturas canceladas")
                        else:
                            st.info("No hay facturas canceladas de clientes")

                with tab2:
                    if "Pendientes_Clientes" in xls.sheet_names:
                        pend_cli = pd.read_excel(out_path, sheet_name="Pendientes_Clientes")
                        if not pend_cli.empty:
                            st.warning(f"⚠️ {len(pend_cli)} facturas de clientes pendientes")
                            st.dataframe(pend_cli.head(50), use_container_width=True, height=400)
                            st.caption(f"Mostrando 50 de {len(pend_cli)} facturas pendientes")
                        else:
                            st.success("✅ No hay facturas pendientes de clientes")

                with tab3:
                    if "Canceladas_Proveedores" in xls.sheet_names:
                        canc_prov = pd.read_excel(out_path, sheet_name="Canceladas_Proveedores")
                        if not canc_prov.empty:
                            st.success(f"✅ {len(canc_prov)} facturas de proveedores emparejadas correctamente")
                            # Mostrar estadísticas de días hasta pago
                            if 'Dias_hasta_pago' in canc_prov.columns:
                                col_stats1, col_stats2, col_stats3 = st.columns(3)
                                col_stats1.metric("⏱️ Días promedio", f"{canc_prov['Dias_hasta_pago'].mean():.0f}")
                                col_stats2.metric("⚡ Pago más rápido", f"{canc_prov['Dias_hasta_pago'].min():.0f} días")
                                col_stats3.metric("🐌 Pago más lento", f"{canc_prov['Dias_hasta_pago'].max():.0f} días")
                            st.dataframe(canc_prov.head(50), use_container_width=True, height=400)
                            st.caption(f"Mostrando 50 de {len(canc_prov)} facturas canceladas")
                        else:
                            st.info("No hay facturas canceladas de proveedores")

                with tab4:
                    if "Pendientes_Proveedores" in xls.sheet_names:
                        pend_prov = pd.read_excel(out_path, sheet_name="Pendientes_Proveedores")
                        if not pend_prov.empty:
                            st.warning(f"⚠️ {len(pend_prov)} facturas de proveedores pendientes")
                            st.dataframe(pend_prov.head(50), use_container_width=True, height=400)
                            st.caption(f"Mostrando 50 de {len(pend_prov)} facturas pendientes")
                        else:
                            st.success("✅ No hay facturas pendientes de proveedores")

                with tab5:
                    st.header("📊 Análisis de Facturas con Múltiples Pagos")

                    # Datos de multipago
                    multi_cli_exists = "Multipago_Clientes" in xls.sheet_names
                    multi_prov_exists = "Multipago_Proveedores" in xls.sheet_names

                    if multi_cli_exists or multi_prov_exists:
                        col_m1, col_m2 = st.columns(2)

                        with col_m1:
                            if multi_cli_exists:
                                multi_cli = pd.read_excel(out_path, sheet_name="Multipago_Clientes")
                                if not multi_cli.empty:
                                    st.subheader("👥 Clientes - Multipago")
                                    st.info(f"📋 {len(multi_cli)} facturas con múltiples pagos")

                                    # Estadísticas
                                    mcol1, mcol2, mcol3 = st.columns(3)
                                    mcol1.metric("Promedio pagos", f"{multi_cli['Num_Pagos'].mean():.1f}")
                                    mcol2.metric("Máx pagos", f"{multi_cli['Num_Pagos'].max():.0f}")
                                    mcol3.metric("Días promedio", f"{multi_cli['Dias_Pago_Total'].mean():.0f}")

                                    # Gráfico de distribución
                                    fig_dist_cli = px.histogram(multi_cli, x='Num_Pagos',
                                                               title='Distribución de Número de Pagos (Clientes)',
                                                               labels={'Num_Pagos': 'Número de Pagos', 'count': 'Cantidad'},
                                                               color_discrete_sequence=['#4CAF50'])
                                    st.plotly_chart(fig_dist_cli, use_container_width=True)

                                    # Tabla
                                    st.dataframe(multi_cli.head(20), use_container_width=True, height=300)
                                    st.caption(f"Mostrando 20 de {len(multi_cli)} facturas multipago")
                                else:
                                    st.success("✅ No hay facturas de clientes con múltiples pagos")

                        with col_m2:
                            if multi_prov_exists:
                                multi_prov = pd.read_excel(out_path, sheet_name="Multipago_Proveedores")
                                if not multi_prov.empty:
                                    st.subheader("🏢 Proveedores - Multipago")
                                    st.info(f"📋 {len(multi_prov)} facturas con múltiples pagos")

                                    # Estadísticas
                                    mcol1, mcol2, mcol3 = st.columns(3)
                                    mcol1.metric("Promedio pagos", f"{multi_prov['Num_Pagos'].mean():.1f}")
                                    mcol2.metric("Máx pagos", f"{multi_prov['Num_Pagos'].max():.0f}")
                                    mcol3.metric("Días promedio", f"{multi_prov['Dias_Pago_Total'].mean():.0f}")

                                    # Gráfico de distribución
                                    fig_dist_prov = px.histogram(multi_prov, x='Num_Pagos',
                                                                title='Distribución de Número de Pagos (Proveedores)',
                                                                labels={'Num_Pagos': 'Número de Pagos', 'count': 'Cantidad'},
                                                                color_discrete_sequence=['#2196F3'])
                                    st.plotly_chart(fig_dist_prov, use_container_width=True)

                                    # Tabla
                                    st.dataframe(multi_prov.head(20), use_container_width=True, height=300)
                                    st.caption(f"Mostrando 20 de {len(multi_prov)} facturas multipago")
                                else:
                                    st.success("✅ No hay facturas de proveedores con múltiples pagos")
                    else:
                        st.info("No hay datos de multipago disponibles")

            except Exception as e:
                st.warning(f"⚠️ No se pudo previsualizar los resultados: {e}")