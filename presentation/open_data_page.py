"""Pantalla Streamlit: APIs colombianas + circuit breaker + análisis DuckDB."""
import pandas as pd
import streamlit as st

from presentation.container import build_open_data_service

_COLORS = {"CLOSED": "🟢", "OPEN": "🔴", "HALF_OPEN": "🟡"}


def pantalla_datos_abiertos():
    st.title("Datos abiertos de Colombia")
    st.caption("datos.gov.co: IES (SNIES - MEN) y DIVIPOLA (nomenclatura DANE). "
               "Procesados con DuckDB y protegidos con circuit breaker + retry con backoff.")

    if "open_data" not in st.session_state:
        st.session_state.open_data = build_open_data_service()
    service, clients = st.session_state.open_data

    c1, c2, c3 = st.columns(3)
    if c1.button("Actualizar datos", use_container_width=True):
        with st.spinner("Consultando APIs..."):
            st.session_state.open_data_report = service.refresh(limit=1000)
    if c2.button("Simular caída de API", use_container_width=True):
        clients[0].simulate_outage()
        st.warning(f"Caída simulada en {clients[0].name}. Pulsa 'Actualizar datos' varias veces.")
    if c3.button("Restaurar API", use_container_width=True):
        clients[0].restore()
        st.success("API restaurada.")

    st.subheader("Estado de los circuit breakers")
    for cl in clients:
        st.write(f"{_COLORS[cl.breaker.state.value]} **{cl.name}** (`{cl.dataset_id}`): {cl.breaker.state.value}")

    report = st.session_state.get("open_data_report", {})
    for name, info in report.items():
        if info["ok"]:
            st.success(f"{name}: {info['rows']} registros cargados en DuckDB")
        else:
            st.error(f"{name}: {info['error']}")

    for name, info in report.items():
        if not info["ok"] or info["rows"] == 0:
            continue
        st.subheader(f"Análisis: {name}")
        st.caption("Query 1 - SUMMARIZE (estadísticas descriptivas)")
        st.dataframe(pd.DataFrame(service.summary(name)), use_container_width=True)
        column, rows = service.top_categories(name)
        if column:
            st.caption(f"Query 2 - GROUP BY `{column}` (top 10)")
            df = pd.DataFrame(rows).set_index("category")
            st.bar_chart(df["total"])
