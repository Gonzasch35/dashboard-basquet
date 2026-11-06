"""Grafo del codigo del TP armado con graphify (graphify-out/)."""
import json

import pandas as pd
import streamlit as st

from lib.db import APP_DIR
from lib.ui import encabezado

OUT = APP_DIR / "graphify-out"
encabezado("Grafo del código", "Generado con graphify: tablas del DDL, FK entre ellas y funciones de generar_datos.py")

if not (OUT / "graph.html").exists():
    st.warning("No está `graphify-out/graph.html`. Generalo con `/graphify` sobre la carpeta del TP.")
    st.stop()

g = json.loads((OUT / "graph.json").read_text(encoding="utf-8"))
nodos = pd.DataFrame(g["nodes"])
aristas = pd.DataFrame(g.get("links") or g.get("edges"))
c = st.columns(3)
c[0].metric("Nodos", len(nodos))
c[1].metric("Relaciones", len(aristas))
c[2].metric("Comunidades", nodos["community"].nunique() if "community" in nodos else "—")

tab_g, tab_c, tab_r = st.tabs(["Grafo interactivo", "Comunidades", "Reporte"])
with tab_g:
    st.caption("Arrastrá, hacé zoom y pasá el mouse por los nodos. Los colores son las comunidades que detecta graphify.")
    st.iframe(OUT / "graph.html", height=760)
with tab_c:
    if "community" in nodos:
        col = "community_name" if "community_name" in nodos else "community"
        resumen = (nodos.groupby(col).label.apply(lambda s: ", ".join(map(str, s.head(15)))).rename("nodos")
                   .reset_index())
        resumen.insert(1, "cantidad", nodos.groupby(col).size().values)
        st.dataframe(resumen.sort_values("cantidad", ascending=False), hide_index=True, width="stretch",
                     column_config={"nodos": st.column_config.TextColumn(width="large")})
with tab_r:
    st.markdown((OUT / "GRAPH_REPORT.md").read_text(encoding="utf-8"))
