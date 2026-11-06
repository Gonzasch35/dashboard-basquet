import plotly.express as px
import streamlit as st

from lib.db import query
from lib.liga import CATEGORIAS, partidos
from lib.ui import COLOR_CAT, SECUENCIAL, SERIES, chart, encabezado, requiere_base

encabezado("Árbitros y calendario", "Designaciones, asistencia y cómo se reparte la temporada en el calendario")
requiere_base()

ap = query("""
    select a.dni_arbitro, a.apellido || ', ' || a.nombre as arbitro, a.categoria_arbitro,
           ap.rol, ap.asistencia, ap.observacion, ca.nombre as categoria, p.fase, p.fecha
    from arbitro_partido ap
    join arbitro a on a.dni_arbitro = ap.dni_arbitro
    join partido p on p.id_partido = ap.id_partido
    join torneo t on t.id_torneo = p.id_torneo
    join categoria ca on ca.id_categoria = t.id_categoria""")

tab_arb, tab_cal = st.tabs(["Árbitros", "Calendario"])
with tab_arb:
    dirigidos = ap[ap.asistencia != "Ausente"]
    carga = dirigidos.groupby(["arbitro", "categoria_arbitro", "categoria"]).size().rename("partidos").reset_index()
    orden = carga.groupby("arbitro").partidos.sum().sort_values().index.tolist()
    fig = px.bar(carga, x="partidos", y="arbitro", color="categoria", orientation="h",
                 color_discrete_map=COLOR_CAT, category_orders={"arbitro": orden, "categoria": CATEGORIAS},
                 hover_data=["categoria_arbitro"])
    fig.update_layout(height=520, title="Partidos dirigidos por árbitro y categoría", yaxis_title=None)
    chart(fig)
    st.caption("Los **Aspirantes** solo dirigen U13 y U15 (control C22); toda final tiene un **Nacional** (C23).")

    a, b = st.columns(2)
    with a:
        asis = ap.groupby(["asistencia"]).size().rename("veces").reset_index()
        st.markdown("**Asistencia**")
        st.dataframe(asis, hide_index=True, width="stretch")
    with b:
        st.markdown("**Ausencias y llegadas tarde (con su motivo)**")
        st.dataframe(ap[ap.asistencia != "Presente"][["fecha", "arbitro", "rol", "asistencia", "observacion"]]
                     .sort_values("fecha"), hide_index=True, width="stretch")

with tab_cal:
    p = partidos()
    p["dia"] = p.fecha.map(lambda d: ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][d.weekday()])
    p["hora_txt"] = p.hora.map(lambda h: h.strftime("%H:%M"))
    heat = p.groupby(["dia", "hora_txt"]).size().rename("partidos").reset_index()
    fig = px.density_heatmap(heat, x="dia", y="hora_txt", z="partidos", text_auto=True,
                             category_orders={"dia": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]},
                             color_continuous_scale=SECUENCIAL)
    fig.update_layout(height=420, title="Partidos por día y horario (toda la temporada)",
                      yaxis_title=None, xaxis_title=None, coloraxis_colorbar_title="partidos")
    fig.update_yaxes(autorange="reversed")
    chart(fig)
    st.caption("Viernes 19:00 / 21:30 solo U17-U19; fines de semana 11, 14, 17 y 20 hs; "
               "los postergados caen de lunes a jueves a las 18:00 o 20:00 (check ck_partido_dia_horario).")

    sem = p.assign(semana=p.fecha.map(lambda d: d.isocalendar()[1])).groupby(["semana", "categoria"]).size()
    sem = sem.rename("partidos").reset_index()
    fig = px.bar(sem, x="semana", y="partidos", color="categoria", color_discrete_map=COLOR_CAT,
                 category_orders={"categoria": CATEGORIAS})
    fig.update_layout(height=340, title="Partidos por semana del año", bargap=0.1, xaxis_title="semana")
    chart(fig)
