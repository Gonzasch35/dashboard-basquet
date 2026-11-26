import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lib.liga import CATEGORIAS, estadisticas_jugadores
from lib.ui import COLOR_CAT, SERIES, chart, encabezado, requiere_base

encabezado("Jugadores", "Quiénes se destacaron en 2026 y cómo le fue a cada uno partido a partido",
           """
De cada partido se guarda la **planilla** de cada jugador: minutos jugados, tiros convertidos (**libres** valen
1 punto, **dobles** 2 y **triples** 3), puntos, **rebotes** (agarrar la pelota después de un tiro errado),
**asistencias** (el pase que termina en una canasta) y faltas.

- **Líderes:** los 15 mejores de la temporada en la estadística que elijas (solo jugadores con 10 partidos o más).
- **Perfil de jugador:** buscá a cualquier jugador y mirá sus números partido a partido. La línea punteada
  es el promedio de su categoría, para comparar.
- **Cómo se anota:** qué parte de los puntos sale de cada tipo de tiro, según la edad.

Con los botones de arriba podés filtrar por categoría.
""")
requiere_base()

e = estadisticas_jugadores()
cats = st.segmented_control("Categorías", CATEGORIAS, default=CATEGORIAS, selection_mode="multi")
e = e[e.categoria.isin(cats or CATEGORIAS)]

tot = (e.groupby(["dni_jugador", "jugador", "equipo", "categoria", "posicion", "altura_cm"], as_index=False)
       .agg(pj=("puntos", "size"), puntos=("puntos", "sum"), triples=("triples", "sum"),
            rebotes=("rebotes", "sum"), asistencias=("asistencias", "sum"), minutos=("minutos", "sum"),
            maximo=("puntos", "max")))
# un jugador con pase aparece con 2 equipos: se junta por dni
tot = (tot.groupby(["dni_jugador", "jugador", "categoria", "posicion", "altura_cm"], as_index=False)
       .agg(equipo=("equipo", " / ".join), pj=("pj", "sum"), puntos=("puntos", "sum"), triples=("triples", "sum"),
            rebotes=("rebotes", "sum"), asistencias=("asistencias", "sum"), minutos=("minutos", "sum"),
            maximo=("maximo", "max")))
for k in ["puntos", "rebotes", "asistencias"]:
    tot[f"{k[:3]}_pp"] = (tot[k] / tot.pj).round(1)

tab_lideres, tab_perfil, tab_tiro = st.tabs(["Líderes", "Perfil de jugador", "Cómo se anota"])

with tab_lideres:
    stat = st.radio("Estadística", ["puntos", "rebotes", "asistencias", "triples"], horizontal=True)
    top = tot[tot.pj >= 10].nlargest(15, stat).sort_values(stat)
    fig = px.bar(top, x=stat, y="jugador", color="categoria", orientation="h", text=stat,
                 color_discrete_map=COLOR_CAT, category_orders={"categoria": CATEGORIAS},
                 hover_data=["equipo", "pj", "pun_pp", "maximo"])
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=520, title=f"Top 15 en {stat} (temporada, mínimo 10 partidos)",
                      yaxis_title=None, xaxis_title=None, yaxis={"categoryorder": "total ascending"})
    chart(fig)

    st.markdown("**Las mejores actuaciones en un partido**")
    st.dataframe(e.nlargest(10, "puntos")[["jugador", "equipo", "categoria", "fase", "fecha", "puntos",
                                           "triples", "rebotes", "minutos"]], hide_index=True, width="stretch")

with tab_perfil:
    opciones = tot.sort_values("puntos", ascending=False)
    etiqueta = opciones.jugador + " · " + opciones.equipo
    sel = st.selectbox("Jugador", opciones.dni_jugador, format_func=dict(zip(opciones.dni_jugador, etiqueta)).get)
    j = tot[tot.dni_jugador == sel].iloc[0]
    log = e[e.dni_jugador == sel].sort_values("fecha")
    c = st.columns(5)
    c[0].metric("Partidos", int(j.pj))
    c[1].metric("Puntos por partido", j.pun_pp)
    c[2].metric("Rebotes por partido", j.reb_pp)
    c[3].metric("Asistencias por partido", j.asi_pp)
    c[4].metric("Máximo en un partido", int(j.maximo))
    st.caption(f"{j.posicion} · {int(j.altura_cm)} cm · {j.categoria} · {j.equipo}")

    prom_cat = e[e.categoria == j.categoria].groupby("dni_jugador").puntos.mean().mean()
    fig = go.Figure()
    fig.add_bar(x=log.fecha, y=log.puntos, name="puntos", marker_color=SERIES[0],
                customdata=log[["fase", "equipo"]], hovertemplate="%{x|%d/%m}: %{y} pts<br>%{customdata[0]}<extra></extra>")
    fig.add_scatter(x=log.fecha, y=log.puntos.rolling(5, min_periods=1).mean(), name="promedio móvil (5)",
                    line=dict(color=SERIES[1]), mode="lines")
    fig.add_hline(y=prom_cat, line_dash="dot", line_color="#8a8983",
                  annotation_text=f"promedio {j.categoria}: {prom_cat:.1f}", annotation_position="top left")
    fig.update_layout(height=380, title="Puntos partido a partido", yaxis_title=None, xaxis_title=None)
    chart(fig)
    st.dataframe(log[["fecha", "torneo", "fase", "equipo", "minutos", "libres", "dobles", "triples", "puntos",
                      "rebotes", "asistencias", "faltas"]], hide_index=True, width="stretch")

with tab_tiro:
    mix = (e.groupby("categoria")[["libres", "dobles", "triples"]].sum()
           .assign(**{"Libres (1)": lambda d: d.libres, "Dobles (2)": lambda d: d.dobles * 2,
                      "Triples (3)": lambda d: d.triples * 3})
           [["Libres (1)", "Dobles (2)", "Triples (3)"]])
    mix = (mix.div(mix.sum(axis=1), axis=0) * 100).round(1).reset_index().melt("categoria", var_name="tipo",
                                                                               value_name="porcentaje")
    fig = px.bar(mix, x="categoria", y="porcentaje", color="tipo", text="porcentaje",
                 color_discrete_sequence=SERIES[:3], category_orders={"categoria": CATEGORIAS})
    fig.update_traces(texttemplate="%{text:.0f}%", textposition="inside")
    fig.update_layout(height=380, title="De dónde salen los puntos (% de los puntos de cada categoría)",
                      yaxis_title="% de los puntos", xaxis_title=None)
    chart(fig)
    st.caption("A más edad, más peso del triple: es parte de lo que el generador modela por categoría.")

    por_pos = (e.groupby("posicion")[["rebotes", "asistencias", "triples"]].mean().round(2)
               .reindex(["Base", "Escolta", "Alero", "Ala-pivot", "Pivot"]).reset_index())
    st.markdown("**Promedio por partido según la posición**")
    st.dataframe(por_pos, hide_index=True, width="stretch")
