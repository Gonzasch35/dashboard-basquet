import pandas as pd
import plotly.express as px
import streamlit as st

from lib.db import TABLAS, query
from lib.liga import CATEGORIAS, partidos
from lib.ui import COLOR_CAT, chart, encabezado, requiere_base

encabezado("Liga de Básquet Formativo de Paraná",
           "TP Final de Base de Datos · Temporada 2026 · U13, U15, U17 y U19 · PostgreSQL + Python")
requiere_base()

# ------------------------------------------------------------ numeros grandes
p = partidos()
conteos = query(" union all ".join(f"select '{t}' as tabla, count(*) as filas from {t}" for t in TABLAS))
filas = dict(zip(conteos.tabla, conteos.filas))

c = st.columns(6)
c[0].metric("Clubes", filas["club"])
c[1].metric("Equipos", filas["equipo"])
c[2].metric("Jugadores", filas["jugador"])
c[3].metric("Partidos", filas["partido"])
c[4].metric("Filas de estadística", f"{filas['estadistica']:,}".replace(",", "."))
c[5].metric("Filas en total", f"{int(conteos.filas.sum()):,}".replace(",", "."))

c = st.columns(6)
c[0].metric("W.O. (20 a 0)", int(p.wo.sum()))
c[1].metric("Postergados", int(p.fecha_original.notna().sum()))
c[2].metric("Pases", filas["pase"])
c[3].metric("Series de playoff", filas["serie"])
c[4].metric("Árbitros", filas["arbitro"])
c[5].metric("Entrenadores", filas["entrenador"])

st.divider()
izq, der = st.columns([3, 2])

with izq:
    st.subheader("Campeones 2026")
    finales = p[p.fase == "Final"].copy()
    finales["campeon"] = finales.ganador.str.replace(r" U1\d$", "", regex=True)
    grilla = finales.pivot(index="torneo", columns="categoria", values="campeon").reindex(columns=CATEGORIAS)
    st.dataframe(grilla, width="stretch")
    st.caption("Ganador de cada final (a un partido, en la cancha neutral de mayor capacidad).")

    st.subheader("Partidos por fase y categoría")
    fases = (p.groupby(["fase", "categoria"]).size().rename("partidos").reset_index())
    orden = ["Regular", "Cuartos", "Semifinal", "Final"]
    fig = px.bar(fases, x="fase", y="partidos", color="categoria", barmode="group",
                 category_orders={"fase": orden, "categoria": CATEGORIAS}, color_discrete_map=COLOR_CAT,
                 text="partidos")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=340, yaxis_title=None, xaxis_title=None)
    chart(fig)

with der:
    st.subheader("Filas por tabla")
    conteos["orden"] = conteos.tabla.map({t: i for i, t in enumerate(TABLAS)})
    fig = px.bar(conteos.sort_values("filas"), x="filas", y="tabla", orientation="h", log_x=True,
                 text="filas", color_discrete_sequence=["#2a78d6"])
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=520, xaxis_title="filas (escala log)", yaxis_title=None)
    chart(fig)

st.divider()
st.subheader("Qué pide la consigna y dónde está en este dashboard")
st.dataframe(pd.DataFrame([
    ("1. Poblar la base (IA generativa / datos)", "generar_datos.py → 02_dml_carga_datos.sql (semilla 2026)", "Inicio · Modelo de datos"),
    ("2. Al menos 6 consultas complejas", "sql/04_consultas_complejas.sql (Q1 a Q8)", "Consultas complejas"),
    ("3. Consulta de 3 tablas + álgebra relacional", "sql/05_algebra_relacional.sql (A1 y A2)", "Álgebra relacional"),
    ("4. Interfaz de acceso a datos con valor agregado", "Este dashboard (Streamlit + Plotly + SciPy)", "Todas · sobre todo Análisis estadístico"),
    ("Reglas que el DDL no frena", "03_controles.sql (C1 a C30)", "Controles de integridad"),
], columns=["Consigna", "Archivo", "Página"]), hide_index=True, width="stretch")
