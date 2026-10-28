"""
SIRA - Sistema de Registro Académico


Para ejecutarlo:
    pip install -r requirements.txt
    streamlit run app.py
"""

import threading
import time

import pandas as pd
import streamlit as st

from database import init_db, SessionLocal
from seed import seed_if_empty
import services
from services import ErrorConcurrencia, ErrorValidacion

# =============================================================================
# ESTILOS (idénticos al diseño original)
# =============================================================================

NAVY = "#172A4A"
BLUE = "#2563EB"
GREEN = "#16A34A"
GREEN_BG = "#DCF5E3"
AMBER = "#D97706"
AMBER_BG = "#FDEBD0"
RED = "#DC2626"
RED_BG = "#FDE2E2"


def inject_css():
    st.markdown(
        f"""
        <style>
        .sira-topbar {{
            background-color: {NAVY};
            color: white;
            padding: 14px 24px;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .sira-topbar .brand {{
            font-weight: 800;
            font-size: 20px;
            letter-spacing: 1px;
        }}
        .sira-topbar .user {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .pill {{
            display: inline-block;
            padding: 4px 14px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 12px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def topbar(user_label: str):
    st.markdown(
        f"""
        <div class="sira-topbar">
            <div class="brand">SIRA &nbsp; <span style="font-weight:400; opacity:.8; font-size:14px;">
                Sistema de Registro Académico</span></div>
            <div class="user">{user_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(estado: str) -> str:
    colors = {
        "Disponible": (GREEN, GREEN_BG),
        "Pocos cupos": (AMBER, AMBER_BG),
        "Sin cupos": (RED, RED_BG),
        "Normal": (GREEN, GREEN_BG),
        "Casi lleno": (AMBER, AMBER_BG),
        "Lleno": (RED, RED_BG),
    }
    fg, bg = colors.get(estado, (NAVY, "#EEF0F3"))
    return f'<span class="pill" style="color:{fg}; background:{bg};">{estado}</span>'


# =============================================================================
# ESTADO DE SESIÓN
# =============================================================================

def init_session_state():
    defaults = {
        "autenticado": False,
        "usuario_id": None,
        "usuario_nombre": "",
        "usuario_correo": "",
        "rol": "estudiante",
        "vista": "catalogo",
        "grupo_seleccionado": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def cerrar_sesion():
    for k in ["autenticado", "usuario_id", "usuario_nombre", "usuario_correo", "rol", "vista", "grupo_seleccionado"]:
        st.session_state.pop(k, None)
    init_session_state()


# =============================================================================
# PANTALLA: LOGIN
# =============================================================================

def pantalla_login():
    st.markdown("<h2 style='text-align:center;'>SIRA</h2>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center; color:#6B7280;'>Sistema de Registro Académico</p>",
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1, 1.3, 1])
    with col:
        with st.container(border=True):
            st.subheader("Iniciar sesión")
            st.caption("Usa tus credenciales institucionales")

            with st.form("form_login", clear_on_submit=False):
                correo = st.text_input("Usuario institucional", placeholder="nbarrera@umb.edu.co")
                password = st.text_input("Contraseña", type="password")
                enviado = st.form_submit_button("Ingresar al sistema", type="primary", use_container_width=True)

            if enviado:
                try:
                    usuario = services.autenticar(correo, password)
                except ErrorValidacion as e:
                    st.error(str(e))
                else:
                    st.session_state.autenticado = True
                    st.session_state.usuario_id = usuario.id
                    st.session_state.usuario_nombre = usuario.nombre
                    st.session_state.usuario_correo = usuario.correo
                    st.session_state.rol = usuario.rol
                    st.session_state.vista = (
                        "catalogo" if usuario.rol == "estudiante" else "panel_coordinador"
                    )
                    st.rerun()

            st.caption(
                "Cuentas de prueba: nbarrera@umb.edu.co / estudiante123 · "
                "cpena@umb.edu.co / coordinador123"
            )


# =============================================================================
# PANTALLA: CATÁLOGO DE MATERIAS Y GRUPOS
# =============================================================================

def pantalla_catalogo():
    topbar(f"{st.session_state.usuario_nombre} · Estudiante")
    st.subheader("Materias y grupos disponibles")
    st.caption("Periodo académico 2026-2")

    busqueda = st.text_input(
        "Buscar materia", placeholder="Ej: Bases de Datos", label_visibility="collapsed"
    )
    grupos = services.listar_grupos(busqueda)

    if not grupos:
        st.info("No se encontraron materias con ese nombre.")

    for g in grupos:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([3, 1.6, 2.2, 1.4, 1.6])
            c1.markdown(f"**{g['materia']}**  \nGrupo {g['grupo']}")
            c2.markdown(g["docente"])
            c3.markdown(g["horario"])
            c4.markdown(f"**{g['cupos_ocupados']} / {g['cupos_totales']}**")
            c5.markdown(status_pill(g["estado"]), unsafe_allow_html=True)

            etiqueta = "Inscribirme" if g["estado"] != "Sin cupos" else "Unirme a lista de espera"
            if st.button(etiqueta, key=f"btn_{g['id']}"):
                st.session_state.grupo_seleccionado = g["id"]
                st.session_state.vista = "confirmar"
                st.rerun()

    st.divider()
    if st.button("Ver mis inscripciones y lista de espera"):
        st.session_state.vista = "mis_materias"
        st.rerun()


# =============================================================================
# PANTALLA: CONFIRMAR INSCRIPCIÓN
# =============================================================================

def pantalla_confirmar():
    topbar(f"{st.session_state.usuario_nombre} · Estudiante")
    gid = st.session_state.grupo_seleccionado
    g = services.obtener_grupo(gid)

    if g is None:
        st.error("El grupo seleccionado ya no existe.")
        if st.button("← Volver al catálogo"):
            st.session_state.vista = "catalogo"
            st.rerun()
        return

    st.subheader("Confirmar inscripción")
    with st.container(border=True):
        st.markdown(f"### {g['materia']} — Grupo {g['grupo']}")
        st.caption(f"Docente: {g['docente']}  ·  Horario: {g['horario']}")

        m1, m2 = st.columns(2)
        m1.metric("Cupos totales", g["cupos_totales"])
        m2.metric("Cupos disponibles", g["cupos_disponibles"])

        st.info(
            "El cupo se bloqueará durante la transacción para evitar que dos "
            "estudiantes obtengan el mismo cupo al mismo tiempo."
        )

        if st.button("Confirmar inscripción", type="primary"):
            estado_ui = st.empty()
            estado_ui.write("Verificando disponibilidad de cupo…")
            time.sleep(0.2)
            estado_ui.write("Bloqueando registro del grupo…")
            try:
                resultado = services.inscribir_estudiante(st.session_state.usuario_id, gid)
            except ErrorConcurrencia as e:
                estado_ui.empty()
                st.error(str(e))
            else:
                estado_ui.empty()
                if resultado == "inscrito":
                    st.success("Inscripción confirmada. ¡Ya estás matriculado en este grupo!")
                elif resultado == "ya_inscrito":
                    st.warning("Ya estabas inscrito en este grupo.")
                elif resultado == "lista_espera":
                    pos = services.obtener_posicion_espera(st.session_state.usuario_id, gid)
                    st.warning(
                        f"El grupo no tenía cupos disponibles. Fuiste agregado a la lista "
                        f"de espera en la posición #{pos}."
                    )
                elif resultado == "ya_en_espera":
                    pos = services.obtener_posicion_espera(st.session_state.usuario_id, gid)
                    st.info(f"Ya estás en la lista de espera de este grupo, en la posición #{pos}.")

    if st.button("← Volver al catálogo"):
        st.session_state.vista = "catalogo"
        st.rerun()


# =============================================================================
# PANTALLA: MIS INSCRIPCIONES Y LISTA DE ESPERA
# =============================================================================

def pantalla_mis_materias():
    topbar(f"{st.session_state.usuario_nombre} · Estudiante")
    st.subheader("Mis inscripciones y lista de espera")

    usuario_id = st.session_state.usuario_id
    inscritas = services.listar_mis_inscripciones(usuario_id)
    en_espera = services.listar_mi_lista_espera(usuario_id)

    st.markdown("#### Materias inscritas")
    if not inscritas:
        st.caption("Aún no tienes materias inscritas.")
    for g in inscritas:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{g['materia']} — Grupo {g['grupo']}**  \n{g['docente']} · {g['horario']}")
            if c2.button("Cancelar", key=f"cancelar_{g['id']}"):
                services.cancelar_inscripcion(usuario_id, g["id"])
                st.rerun()

    st.markdown("#### En lista de espera")
    if not en_espera:
        st.caption("No estás en ninguna lista de espera.")
    for item in en_espera:
        with st.container(border=True):
            st.markdown(f"**{item['materia']} — Grupo {item['grupo']}**")
            st.markdown(f"Posición en la lista: **#{item['posicion']}** de {item['total_en_espera']}")

    notificaciones = services.listar_notificaciones(usuario_id)
    if notificaciones:
        st.markdown("#### Notificaciones")
        for msg in notificaciones:
            st.success(msg)

    if st.button("← Volver al catálogo"):
        st.session_state.vista = "catalogo"
        st.rerun()


# =============================================================================
# PANTALLA: PANEL DEL COORDINADOR
# =============================================================================

def pantalla_panel_coordinador():
    topbar(f"{st.session_state.usuario_nombre} · Coordinador académico")
    st.subheader("Ocupación de grupos en tiempo real")

    grupos = services.listar_grupos()
    metricas = services.resumen_metricas()

    total_ocupados = sum(g["cupos_ocupados"] for g in grupos)
    total_cupos = sum(g["cupos_totales"] for g in grupos)
    total_espera = sum(g["en_espera"] for g in grupos)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Grupos activos", len(grupos))
    c2.metric("Cupos ocupados", f"{total_ocupados} / {total_cupos}")
    c3.metric("En lista de espera", total_espera)
    c4.metric("Transacciones fallidas", metricas["transacciones_fallidas"])

    df = pd.DataFrame([{
        "Materia / Grupo": f"{g['materia']} - {g['grupo']}",
        "Docente": g["docente"],
        "Ocupados": g["cupos_ocupados"],
        "Disponibles": g["cupos_disponibles"],
        "En espera": g["en_espera"],
        "Estado": g["estado_coordinador"],
    } for g in grupos])

    def resaltar_estado(val):
        color = {"Normal": GREEN, "Casi lleno": AMBER, "Lleno": RED}.get(val, "black")
        return f"color: {color}; font-weight: 700;"

    st.dataframe(
        df.style.map(resaltar_estado, subset=["Estado"]),
        use_container_width=True,
        hide_index=True,
    )

    if metricas["tiempos_ms"]:
        st.markdown("#### Tiempos de respuesta de inscripción (ms)")
        st.bar_chart(pd.DataFrame({"tiempo_respuesta_ms": metricas["tiempos_ms"]}))
        st.caption(
            f"Reintentos registrados: {metricas['reintentos']}  ·  "
            f"Muestras: {len(metricas['tiempos_ms'])}"
        )

    st.divider()
    if st.button("Ir al simulador de concurrencia →"):
        st.session_state.vista = "simulador"
        st.rerun()


# =============================================================================
# PANTALLA: SIMULADOR DE CONCURRENCIA
# =============================================================================

def pantalla_simulador():
    topbar(f"{st.session_state.usuario_nombre} · Coordinador académico")
    st.subheader("Simulador de inscripciones concurrentes")
    st.caption(
        "Lanza varios estudiantes (hilos reales) que intentan inscribirse al mismo "
        "grupo al mismo tiempo, contra la base de datos, para comprobar que el "
        "bloqueo de registros evita el sobrecupo."
    )

    grupos = services.listar_grupos()
    grupo_id = st.selectbox(
        "Grupo a probar",
        options=[g["id"] for g in grupos],
        format_func=lambda gid: next(
            f"{g['materia']} - Grupo {g['grupo']} ({g['cupos_disponibles']} cupos disponibles)"
            for g in grupos if g["id"] == gid
        ),
    )
    n_estudiantes = st.slider("Número de estudiantes simulados", min_value=2, max_value=100, value=20)

    if st.button("Simular inscripciones concurrentes", type="primary"):
        usuario_ids = services.preparar_usuarios_simulados(n_estudiantes)
        services.reiniciar_estado_grupo_para_simulacion(grupo_id, usuario_ids)

        grupo_antes = services.obtener_grupo(grupo_id)
        cupos_antes = grupo_antes["cupos_disponibles"]

        resultados = {}
        lock_resultados = threading.Lock()

        def trabajador(uid):
            try:
                resultado = services.inscribir_estudiante(uid, grupo_id)
            except ErrorConcurrencia:
                resultado = "fallida"
            with lock_resultados:
                resultados[uid] = resultado

        hilos = [threading.Thread(target=trabajador, args=(uid,)) for uid in usuario_ids]
        inicio = time.time()
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        duracion_total = time.time() - inicio

        inscritos = sum(1 for r in resultados.values() if r == "inscrito")
        en_espera = sum(1 for r in resultados.values() if r == "lista_espera")

        st.success(
            f"Simulación completada en {duracion_total:.3f} s con {n_estudiantes} estudiantes concurrentes."
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Cupos disponibles antes", cupos_antes)
        c2.metric("Inscripciones exitosas", inscritos)
        c3.metric("Enviados a lista de espera", en_espera)

        if inscritos <= cupos_antes:
            st.success("✅ Consistencia verificada: el sistema no asignó más cupos de los disponibles.")
        else:
            st.error("⚠️ Se detectó sobrecupo. Revisa la lógica de bloqueo (esto no debería ocurrir).")

        detalle = pd.DataFrame(
            [{"usuario_id": uid, "resultado": r} for uid, r in resultados.items()]
        )
        st.dataframe(detalle, use_container_width=True, hide_index=True)

    if st.button("← Volver al panel"):
        st.session_state.vista = "panel_coordinador"
        st.rerun()


# =============================================================================
# ENRUTADOR PRINCIPAL
# =============================================================================

def main():
    st.set_page_config(
        page_title="SIRA - Registro Académico",
        layout="wide"
    )

    init_db()

    # Carga los datos de prueba si todavía no existen
    seed_if_empty(SessionLocal)

    inject_css()
    init_session_state()

    if not st.session_state.autenticado:
        pantalla_login()
        return

    with st.sidebar:
        st.markdown(f"**{st.session_state.usuario_nombre}**")
        st.caption(st.session_state.rol.capitalize())
        st.divider()
        if st.session_state.rol == "estudiante":
            if st.button("Catálogo de materias", use_container_width=True):
                st.session_state.vista = "catalogo"
                st.rerun()
            if st.button("Mis inscripciones", use_container_width=True):
                st.session_state.vista = "mis_materias"
                st.rerun()
        else:
            if st.button("Panel de ocupación", use_container_width=True):
                st.session_state.vista = "panel_coordinador"
                st.rerun()
            if st.button("Simulador de concurrencia", use_container_width=True):
                st.session_state.vista = "simulador"
                st.rerun()
            if st.button("Datos abiertos (Colombia)", use_container_width=True):
                st.session_state.vista = "datos_abiertos"
                st.rerun()
        st.divider()
        if st.button("Cerrar sesión", use_container_width=True):
            cerrar_sesion()
            st.rerun()

    vista = st.session_state.vista
    if vista == "catalogo":
        pantalla_catalogo()
    elif vista == "confirmar":
        pantalla_confirmar()
    elif vista == "mis_materias":
        pantalla_mis_materias()
    elif vista == "panel_coordinador":
        pantalla_panel_coordinador()
    elif vista == "simulador":
        pantalla_simulador()
    elif vista == "datos_abiertos":
        from presentation.open_data_page import pantalla_datos_abiertos
        pantalla_datos_abiertos()
    else:
        pantalla_catalogo()


if __name__ == "__main__":
    main()
