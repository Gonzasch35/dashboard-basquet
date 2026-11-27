"""Colores, plantilla de graficos, estilos (modo oscuro + efectos) y piezas de UI compartidas."""
from __future__ import annotations

import html

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from lib.db import ping

# ---------------------------------------------------------------- colores
# Fondo de la app y de las "tarjetas" donde van los graficos (ver .streamlit/config.toml)
FONDO = "#0e1015"
TARJETA = "#151821"
TEXTO = "#eceae6"
TEXTO_2 = "#a3a8b4"      # texto secundario (ejes, notas)
LINEA = "#2a2f3c"        # bordes y ejes
GRILLA = "#222632"
NEUTRO = "#8b909c"       # lineas de referencia (promedios, 50 %)
APAGADO = "#3b404c"      # lo que NO esta resaltado (ej. equipos sin elegir)
ACENTO = "#ff8a3d"       # naranja pelota

# Paleta categorica para fondo oscuro (mismos 8 tonos de siempre, con el paso
# de luminosidad para modo oscuro; validada: CVD >= 10 entre vecinos, contraste >= 3:1).
# Orden fijo: cada categoria tiene SIEMPRE el mismo color en todos los graficos.
SERIES = ["#338ced", "#e76624", "#00a888", "#d28e05", "#e24d8b", "#0aac23", "#9887ef", "#eb6263"]
COLOR_CAT = {"U13": SERIES[0], "U15": SERIES[1], "U17": SERIES[2], "U19": SERIES[3]}
COLOR_TORNEO = {"Apertura": SERIES[0], "Clausura": SERIES[1]}
# En fondo oscuro "poco" es oscuro (se pierde en el fondo) y "mucho" es claro (resalta)
SECUENCIAL = ["#182232", "#0e3d7e", "#1757ac", "#2370cd", "#338ced", "#6aabf1", "#9dc8f7", "#cce3fd"]
DIVERGENTE = [SERIES[1], "#3a3e48", SERIES[0]]  # naranja = menos / gris neutro / azul = mas
OK, MAL = "#0aac23", "#eb6263"

pio.templates["liga"] = go.layout.Template(
    layout=dict(
        colorway=SERIES,
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color=TEXTO_2),
        title=dict(font=dict(size=16, color=TEXTO), x=0, xanchor="left", yref="container", y=0.98, yanchor="top"),
        xaxis=dict(showgrid=False, linecolor=LINEA, ticks="outside", tickcolor=LINEA, zeroline=False),
        yaxis=dict(gridcolor=GRILLA, zeroline=False, linecolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text="", font=dict(color=TEXTO)),
        margin=dict(l=10, r=10, t=90, b=10),
        hoverlabel=dict(bgcolor="#1f2430", bordercolor=LINEA, font=dict(size=13, color=TEXTO)),
        coloraxis=dict(colorbar=dict(outlinewidth=0, tickfont=dict(color=TEXTO_2))),
        bargap=0.25,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        # cuando cambia un filtro, el grafico se mueve en vez de saltar
        transition=dict(duration=500, easing="cubic-in-out"),
        modebar=dict(bgcolor="rgba(0,0,0,0)", color=TEXTO_2, activecolor=ACENTO),
    ),
    data=dict(
        # borde del color de la tarjeta: separa barras vecinas y segmentos apilados
        bar=[go.Bar(marker=dict(line=dict(width=2, color=TARJETA), cornerradius=4))],
        scatter=[go.Scatter(line=dict(width=2), marker=dict(size=8, line=dict(width=1, color=TARJETA)))],
        box=[go.Box(line=dict(width=1.5))],
    ),
)
pio.templates.default = "plotly_dark+liga"


def letra_grande() -> bool:
    return bool(st.session_state.get("letra_grande", False))


def chart(fig, **kw):
    fig.update_layout(legend_title_text="")
    if letra_grande():  # modo proyector: todo el texto del grafico mas grande
        fig.update_layout(font_size=16, title_font_size=19, hoverlabel_font_size=15, legend_font_size=15)
    st.plotly_chart(fig, width="stretch", theme=None,
                    config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}, **kw)


# ---------------------------------------------------------------- estilos
_CSS = """
<style>
/* ---------- fondo con brillo suave (naranja arriba, azul abajo) ---------- */
.stApp {
  background:
    radial-gradient(1100px 520px at 88% -8%, rgba(255,138,61,.13), transparent 60%),
    radial-gradient(900px 600px at -10% 110%, rgba(51,140,237,.10), transparent 60%),
    #0e1015;
}
[data-testid="stHeader"] { background: transparent; }

/* ---------- entrada de la pagina: cada bloque aparece y sube ---------- */
@keyframes subir { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
[data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"],
[data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"],
[data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"],
[data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > [data-testid="stExpander"] {
  animation: subir .55s cubic-bezier(.2,.7,.2,1) both;
}
[data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > :nth-child(2) { animation-delay: .05s; }
[data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > :nth-child(3) { animation-delay: .10s; }
[data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > :nth-child(4) { animation-delay: .15s; }
[data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > :nth-child(5) { animation-delay: .20s; }
[data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > :nth-child(6) { animation-delay: .25s; }
[data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlock"] > :nth-child(n+7) { animation-delay: .30s; }

/* ---------- titulos ---------- */
[data-testid="stMain"] h1 {
  background: linear-gradient(92deg, #ffffff 0%, #ffd2ad 45%, #ff8a3d 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
  letter-spacing: -.02em; padding-bottom: .1rem;
}
[data-testid="stMain"] h1 a { display: none; }
[data-testid="stMain"] h3 { letter-spacing: -.01em; }
[data-testid="stMain"] h3::after {
  content: ""; display: block; width: 44px; height: 3px; margin-top: .35rem; border-radius: 3px;
  background: linear-gradient(90deg, #ff8a3d, rgba(255,138,61,0));
}

/* ---------- metricas como tarjetas que se levantan al pasar el mouse ---------- */
[data-testid="stMetric"] {
  background: linear-gradient(160deg, #1b1f2a 0%, #151821 100%);
  border: 1px solid #2a2f3c; border-radius: 14px; padding: 14px 16px 12px;
  transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
}
[data-testid="stMetric"]:hover {
  transform: translateY(-4px); border-color: rgba(255,138,61,.6);
  box-shadow: 0 10px 28px -12px rgba(255,138,61,.45);
}
[data-testid="stMetricLabel"] { color: #a3a8b4; }

/* ---------- graficos, tablas y desplegables en tarjeta ---------- */
[data-testid="stPlotlyChart"] {
  background: #151821; border: 1px solid #2a2f3c; border-radius: 14px; overflow: hidden;
  transition: border-color .25s ease, box-shadow .25s ease;
}
[data-testid="stPlotlyChart"]:hover { border-color: #3a4152; box-shadow: 0 12px 34px -18px rgba(0,0,0,.9); }
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; transition: box-shadow .25s ease; }
[data-testid="stDataFrame"]:hover { box-shadow: 0 0 0 1px rgba(255,138,61,.35); }
[data-testid="stExpander"] details { border-radius: 12px; transition: border-color .2s ease; background: rgba(21,24,33,.6); }
[data-testid="stExpander"] details:hover { border-color: rgba(255,138,61,.5); }
[data-testid="stExpander"] summary:hover p { color: #ffb36b; }

/* ---------- llaves del playoff ---------- */
[class*="st-key-serie_"] { background: linear-gradient(160deg, #1b1f2a, #151821); transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease; }
[class*="st-key-serie_"]:hover { transform: translateY(-3px); border-color: rgba(255,138,61,.6) !important; box-shadow: 0 10px 26px -14px rgba(255,138,61,.5); }

/* ---------- pestanias ---------- */
[data-testid="stTabs"] button[role="tab"] { transition: color .2s ease, background .2s ease; border-radius: 8px 8px 0 0; padding: 0 .9rem; }
[data-testid="stTabs"] button[role="tab"]:hover { background: rgba(255,138,61,.08); color: #ffb36b; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p { font-weight: 700; }

/* ---------- botones ---------- */
.stButton > button, .stFormSubmitButton > button { transition: transform .15s ease, box-shadow .2s ease, border-color .2s ease; }
.stButton > button:hover, .stFormSubmitButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px -10px rgba(255,138,61,.6); }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #ff8a3d, #e7602a); border: 0; color: #12141b; font-weight: 700; }

/* ---------- avisos ---------- */
[data-testid="stAlert"] { border-radius: 12px; }

/* ---------- barra lateral ---------- */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #151822 0%, #0f1117 100%); }
[data-testid="stSidebarNavLink"] { transition: transform .18s ease, background .18s ease; border-radius: 8px; }
[data-testid="stSidebarNavLink"]:hover { transform: translateX(4px); background: rgba(255,138,61,.10); }
[data-testid="stSidebarNavLink"][aria-current="page"] { background: rgba(255,138,61,.16); box-shadow: inset 3px 0 0 #ff8a3d; }

/* ---------- scroll ---------- */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: #2a2f3c; border-radius: 10px; border: 2px solid #0e1015; }
::-webkit-scrollbar-thumb:hover { background: #ff8a3d; }

/* ---------- hero de la portada ---------- */
.hero {
  position: relative; overflow: hidden; border-radius: 22px; padding: 38px 40px 34px; margin: 4px 0 18px;
  background: linear-gradient(125deg, #1d2230 0%, #151821 55%, #2a1a12 100%);
  border: 1px solid #2f3545;
  box-shadow: 0 30px 60px -35px rgba(255,138,61,.45);
  animation: subir .6s cubic-bezier(.2,.7,.2,1) both;
}
.hero .cancha { position: absolute; inset: 0; opacity: .13; pointer-events: none; }
.hero .chip {
  display: inline-block; font-size: .8rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
  color: #ffb36b; background: rgba(255,138,61,.12); border: 1px solid rgba(255,138,61,.35);
  padding: 4px 12px; border-radius: 999px; margin-bottom: 14px;
}
.hero h1.hero-titulo {
  font-size: 2.9rem; line-height: 1.05; margin: 0 0 .6rem; padding: 0; font-weight: 800;
  background: linear-gradient(92deg, #ffffff 0%, #ffd2ad 50%, #ff8a3d 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero p { color: #c9ccd4; font-size: 1.12rem; max-width: 46rem; margin: 0; }
.hero .pelota {
  position: absolute; right: 46px; top: 26px; font-size: 4.6rem;
  animation: picar 1.6s cubic-bezier(.5,0,.5,1) infinite; will-change: transform;
}
.hero .sombra {
  position: absolute; right: 58px; top: 142px; width: 62px; height: 12px; border-radius: 50%;
  background: radial-gradient(closest-side, rgba(0,0,0,.7), transparent); will-change: transform, opacity; animation: sombra 1.6s cubic-bezier(.5,0,.5,1) infinite;
}
@keyframes picar { 0%,100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(38px) rotate(160deg); } }
@keyframes sombra { 0%,100% { transform: scale(.65); opacity: .45; } 50% { transform: scale(1); opacity: .9; } }
@media (max-width: 760px) { .hero .pelota, .hero .sombra { display: none; } .hero h1.hero-titulo { font-size: 2.1rem; } }

/* ---------- numeros grandes que cuentan hacia arriba ---------- */
@property --n { syntax: "<integer>"; inherits: false; initial-value: 0; }
@property --k { syntax: "<integer>"; inherits: false; initial-value: 0; }
@property --u { syntax: "<integer>"; inherits: false; initial-value: 0; }
@counter-style tres { system: extends decimal; pad: 3 "0"; }
@keyframes contar { from { --n: 0; --k: 0; --u: 0; } }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 6px 0 14px; }
.kpi {
  position: relative; overflow: hidden;
  background: linear-gradient(160deg, #1b1f2a 0%, #151821 100%); border: 1px solid #2a2f3c; border-radius: 14px;
  padding: 14px 16px 12px; transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
  animation: subir .55s cubic-bezier(.2,.7,.2,1) both;
}
.kpi::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--c, #ff8a3d); opacity: .9; }
.kpi:hover { transform: translateY(-4px); border-color: rgba(255,138,61,.6); box-shadow: 0 10px 28px -12px rgba(255,138,61,.45); }
.kpi .ico { font-size: 1.25rem; }
.kpi .lbl { color: #a3a8b4; font-size: .88rem; margin-top: 2px; }
.kpi .val { font-size: 2.1rem; font-weight: 800; color: #eceae6; line-height: 1.15; font-variant-numeric: tabular-nums; }
/* la animacion mueve --n (o --k/--u) en el div; el ::after solo muestra el contador */
.kpi .val { animation: contar 1.6s cubic-bezier(.2,.7,.2,1) both; }
.kpi .val.n { counter-reset: n var(--n); }
.kpi .val.n::after { content: counter(n); }
.kpi .val.m { counter-reset: k var(--k) u var(--u); }
.kpi .val.m::after { content: counter(k) "." counter(u, tres); }

/* ---------- respeta a quien pidio menos movimiento ---------- */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
</style>
"""

_CSS_LETRA_GRANDE = """
<style>
html { font-size: 18px; }
/* solo el texto de st.markdown (no los numeros de las metricas, que tambien usan MarkdownContainer) */
[data-testid="stMarkdown"] p, [data-testid="stMarkdown"] li, [data-testid="stMarkdown"] td { font-size: 1.08rem; }
[data-testid="stMetricValue"] { font-size: 2.6rem; }
[data-testid="stCaptionContainer"] { font-size: .98rem; }
</style>
"""


def _compacto(texto: str) -> str:
    """Una sola linea sin sangrias: Markdown toma las lineas con sangria como bloque de codigo."""
    return " ".join(l.strip() for l in texto.splitlines() if l.strip())


def estilos() -> None:
    """Inyecta el CSS de toda la app (se llama una vez en app.py, antes de cada pagina)."""
    # va en la barra lateral para no sumar un bloque vacio al principio de cada pagina
    # (st.html con solo <style> no llega a la pagina en esta version de Streamlit)
    css = _compacto(_CSS + (_CSS_LETRA_GRANDE if letra_grande() else ""))
    st.sidebar.markdown(css, unsafe_allow_html=True)


# Lineas de una cancha de basquet (media cancha) para el fondo del hero
_CANCHA = """
<svg class="cancha" viewBox="0 0 1000 300" preserveAspectRatio="xMidYMid slice" fill="none"
     stroke="#ffb36b" stroke-width="3">
  <rect x="10" y="10" width="980" height="280" rx="6"/>
  <line x1="500" y1="10" x2="500" y2="290"/>
  <circle cx="500" cy="150" r="60"/>
  <rect x="10" y="95" width="170" height="110"/>
  <circle cx="180" cy="150" r="55"/>
  <path d="M10 30 H70 A240 240 0 0 1 70 270 H10"/>
  <rect x="820" y="95" width="170" height="110"/>
  <circle cx="820" cy="150" r="55"/>
  <path d="M990 30 H930 A240 240 0 0 0 930 270 H990"/>
</svg>
"""


def hero(titulo: str, bajada: str, chip: str = "Temporada 2026") -> None:
    """Portada grande con la pelota picando y las lineas de la cancha de fondo."""
    st.markdown(_compacto(
        f"""<div class="hero">{_CANCHA}
        <div class="sombra"></div><div class="pelota">🏀</div>
        <div class="chip">{html.escape(chip)}</div>
        <h1 class="hero-titulo">{html.escape(titulo)}</h1>
        <p>{html.escape(bajada)}</p></div>"""),
        unsafe_allow_html=True)


def kpis(items: list[tuple[str, str, int, str, str]]) -> None:
    """Tarjetas con numeros que cuentan desde 0 (solo CSS).

    items: (icono, etiqueta, valor, ayuda, color del borde)
    Los valores son los mismos que trae la base: la animacion solo cambia como aparecen.
    """
    tarjetas = []
    for i, (ico, lbl, val, ayuda, color) in enumerate(items):
        val = int(val)
        if val >= 1000:  # con punto de miles: 15.360 -> --k:15, --u:360
            num = f'<div class="val m" style="--k:{val // 1000};--u:{val % 1000}"></div>'
        else:
            num = f'<div class="val n" style="--n:{val}"></div>'
        tarjetas.append(
            f'<div class="kpi" title="{html.escape(ayuda)}" style="--c:{color};animation-delay:{i * 0.04:.2f}s">'
            f'<div class="ico">{ico}</div>{num}<div class="lbl">{html.escape(lbl)}</div></div>')
    st.markdown(f'<div class="kpis">{"".join(tarjetas)}</div>', unsafe_allow_html=True)


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
    st.badge("Datos de la temporada 2026", icon="📅", color="orange")
    if bajada:
        st.caption(bajada)
    if ayuda:
        with st.expander("ℹ️ ¿Qué estoy viendo?"):
            st.markdown(ayuda)
