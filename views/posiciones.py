import plotly.express as px
import streamlit as st

from lib.db import query
from lib.liga import CATEGORIAS, TORNEOS, evolucion_posiciones, id_torneo, partidos, tabla_fiba
from lib.ui import SERIES, chart, encabezado, requiere_base

encabezado("Posiciones y playoff", "Cómo terminó cada torneo de 2026: la tabla, cómo se fue armando y el playoff",
           """
Elegí un **torneo** (Apertura o Clausura) y una **categoría**.

- **Tabla:** el ranking de la fase regular. Columnas: **pj** partidos jugados, **pg** ganados, **pp** perdidos,
  **wo** veces que no se presentó, **pf** puntos (tantos) a favor, **pc** en contra, **dif** la diferencia y
  **pts** los puntos de tabla (2 por ganar, 1 por perder, 0 por no presentarse). Si dos equipos empatan en
  puntos, se mira primero cómo les fue en los partidos entre ellos (regla de la FIBA, la federación
  internacional) y después la diferencia general. Los 8 primeros pasan al playoff.
- **Evolución por fecha:** en qué puesto estaba cada equipo después de cada fecha. Arriba es mejor.
- **Playoff:** los cruces de cuartos y semis (al mejor de 3) y la final.
- **Resultados:** todos los partidos de una fecha.
""")
requiere_base()

f1, f2 = st.columns(2)
torneo = f1.segmented_control("Torneo", TORNEOS, default="Apertura")
cat = f2.segmented_control("Categoría", CATEGORIAS, default="U19")
if not torneo or not cat:
    st.stop()
tid = id_torneo(torneo, cat)
p = partidos(tid)

tab_tabla, tab_evol, tab_playoff, tab_fixture = st.tabs(["Tabla", "Evolución por fecha", "Playoff", "Resultados"])

with tab_tabla:
    t = tabla_fiba(tid)
    t["clasifica"] = t.pos.le(8).map({True: "Playoff", False: ""})
    st.dataframe(t[["pos", "equipo", "pj", "pg", "pp", "wo", "pf", "pc", "dif", "pts", "desempate", "clasifica"]],
                 hide_index=True, width="stretch", height=460,
                 column_config={"pts": st.column_config.ProgressColumn("pts", min_value=0, max_value=22, format="%d"),
                                "dif": st.column_config.NumberColumn(format="%+d")})
    st.caption("Reglas FIBA: 2 pts ganado, 1 perdido, 0 W.O. Desempate: partidos entre los empatados "
               "(puntos y diferencia entre ellos) y después diferencia general. Clasifican los 8 primeros.")

with tab_evol:
    ev = evolucion_posiciones(tid)
    ev["equipo"] = ev.equipo.str.replace(r" U1\d$", "", regex=True)
    final = ev[ev.fecha == ev.fecha.max()].sort_values("pos")
    destacados = st.multiselect("Equipos a resaltar", final.equipo.tolist(), default=final.equipo.head(4).tolist(),
                                max_selections=len(SERIES))
    colores = {e: SERIES[i] for i, e in enumerate(destacados)}
    fig = px.line(ev, x="fecha", y="pos", color="equipo", markers=True,
                  color_discrete_map={e: colores.get(e, "#d4d3cd") for e in ev.equipo.unique()},
                  hover_data={"pts": True})
    for tr in fig.data:
        if tr.name not in colores:
            tr.update(line_width=1, marker_size=4, showlegend=False, opacity=0.6)
    fig.update_yaxes(autorange="reversed", dtick=1, title="posición")
    fig.update_xaxes(dtick=1, title="fecha")
    fig.add_hrect(y0=8.5, y1=12.5, fillcolor="#f3f2ee", line_width=0, layer="below")
    fig.update_layout(height=480, title="Cómo se fue armando la tabla fecha a fecha")
    chart(fig)
    st.caption("La franja gris son los puestos que quedan afuera del playoff (9° a 12°).")

with tab_playoff:
    series = query("""
        select s.id_serie, s.fase, m.nombre as mejor, w.nombre as peor, g.nombre as ganador
        from serie s
        join equipo m on m.id_equipo = s.id_equipo_mejor
        join equipo w on w.id_equipo = s.id_equipo_peor
        left join equipo g on g.id_equipo = s.id_equipo_ganador
        where s.id_torneo = %s order by s.id_serie""", (tid,))
    po = p[p.fase != "Regular"]
    cols = st.columns(3)
    for col, fase in zip(cols, ["Cuartos", "Semifinal", "Final"]):
        col.markdown(f"#### {fase}")
        if fase == "Final":
            for r in po[po.fase == "Final"].itertuples():
                col.success(f"🏆 **{r.ganador}**\n\n{r.local} {r.puntos_local} – {r.puntos_visitante} {r.visitante}"
                            f"\n\n📍 {r.cancha} · {r.fecha:%d/%m}")
            continue
        for s in series[series.fase == fase].itertuples():
            juegos = po[po.id_serie == s.id_serie].sort_values("nro_partido_serie")
            res = "  \n".join(f"P{int(j.nro_partido_serie)}: {j.local.rsplit(' ', 1)[0]} {j.puntos_local}–"
                              f"{j.puntos_visitante} {j.visitante.rsplit(' ', 1)[0]}" for j in juegos.itertuples())
            with col.container(border=True):
                st.markdown(f"**{s.mejor}** vs {s.peor}  \n{res}  \n➡️ **{s.ganador}**")
    st.caption("Cuartos y semis al mejor de 3 (el mejor ubicado es local en el 1 y el 3). Final a un partido en cancha neutral.")

with tab_fixture:
    reg = p[p.fase == "Regular"]
    fecha = st.slider("Fecha", 1, 11, 1)
    vista = reg[reg.nro_fecha == fecha][["fecha", "hora", "local", "puntos_local", "puntos_visitante",
                                         "visitante", "cancha", "wo", "motivo_postergacion"]]
    st.dataframe(vista, hide_index=True, width="stretch")
