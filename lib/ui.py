"""Colores, plantilla de graficos y piezas de UI compartidas."""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from lib.db import ping

# Paleta categorica validada (orden fijo, nunca ciclado). Cada categoria
# tiene SIEMPRE el mismo color en todos los graficos.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
COLOR_CAT = {"U13": SERIES[0], "U15": SERIES[1], "U17": SERIES[2], "U19": SERIES[3]}
COLOR_TORNEO = {"Apertura": SERIES[0], "Clausura": SERIES[1]}
SECUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGENTE = ["#eb6834", "#f3f2ee", "#2a78d6"]  # perder / neutro / ganar
OK, MAL = "#008300", "#e34948"

pio.templates["liga"] = go.layout.Template(
    layout=dict(
        colorway=SERIES,
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color="#52514e"),
        title=dict(font=dict(size=15, color="#0b0b0b"), x=0, xanchor="left", yref="container", y=0.98, yanchor="top"),
        xaxis=dict(showgrid=False, linecolor="#d4d3cd", ticks="outside", tickcolor="#d4d3cd"),
        yaxis=dict(gridcolor="#ecebe7", zeroline=False, linecolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
        margin=dict(l=10, r=10, t=90, b=10),
        hoverlabel=dict(bgcolor="white", font_size=12),
        bargap=0.25,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    ),
    data=dict(
        bar=[go.Bar(marker=dict(line=dict(width=2, color="white"), cornerradius=4))],
        scatter=[go.Scatter(line=dict(width=2), marker=dict(size=8))],
    ),
)
pio.templates.default = "plotly_white+liga"


def chart(fig, **kw):
    fig.update_layout(legend_title_text="")
    st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False}, **kw)


def requiere_base() -> None:
    """Corta la pagina con un aviso si la base no esta lista."""
    ok, msg = ping()
    if not ok:
        st.warning(f"No hay conexión con la base de datos.\n\n`{msg}`\n\n"
                   "Configurá la conexión en la barra lateral (o en `.streamlit/secrets.toml`) "
                   "y, si hace falta, tocá **Crear / recargar base**.")
        st.stop()


def encabezado(titulo: str, bajada: str = "", ayuda: str = "") -> None:
    """Titulo de la pagina + aviso de que los datos son de 2026 + ayuda para quien no conoce el tema."""
    st.title(titulo)
    st.badge("Datos de la temporada 2026", icon="📅", color="blue")
    if bajada:
        st.caption(bajada)
    if ayuda:
        with st.expander("ℹ️ ¿Qué estoy viendo?"):
            st.markdown(ayuda)
