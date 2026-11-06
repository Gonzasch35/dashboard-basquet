"""Tests estadisticos sobre la temporada: el 'valor agregado' que no sale con SQL solo."""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.proportion import proportion_confint

from lib.liga import CATEGORIAS, TORNEOS, estadisticas_jugadores, id_torneo, partidos, tabla_fiba
from lib.ui import COLOR_CAT, DIVERGENTE, SERIES, chart, encabezado, requiere_base

encabezado("Análisis estadístico",
           "Pruebas de hipótesis sobre los datos de la temporada (SciPy + statsmodels)",
           "Interfaz de acceso a datos que genere valor agregado: gráficos, tests estadísticos, "
           "interfaz amigable… algo que no se pueda resolver solo con SQL.")
requiere_base()

ALFA = st.sidebar.select_slider("Nivel de significación α", [0.01, 0.05, 0.10], value=0.05)


def veredicto(p, h1):
    if p < ALFA:
        st.success(f"p = {p:.4g} < α = {ALFA} → se rechaza H₀: **{h1}**")
    else:
        st.info(f"p = {p:.4g} ≥ α = {ALFA} → no hay evidencia suficiente para rechazar H₀.")


p = partidos()
jugados = p[(p.fase == "Regular") & (~p.wo)].copy()
e = estadisticas_jugadores()

t1, t2, t3, t4, t5 = st.tabs(["Ventaja de local", "Puntos por categoría", "Altura y rebotes",
                              "Posición y tipo de tiro", "Apertura vs Clausura"])

# ------------------------------------------------------------------ 1
with t1:
    st.markdown("**¿Jugar de local aumenta la probabilidad de ganar?** · Test binomial (fase regular, sin W.O.)  \n"
                "H₀: P(gana el local) = 0,5 · H₁: P(gana el local) > 0,5")
    jugados["gana_local"] = jugados.puntos_local > jugados.puntos_visitante
    filas = []
    for cat in CATEGORIAS + ["Todas"]:
        d = jugados if cat == "Todas" else jugados[jugados.categoria == cat]
        k, n = int(d.gana_local.sum()), len(d)
        lo, hi = proportion_confint(k, n, alpha=ALFA, method="wilson")
        pv = stats.binomtest(k, n, 0.5, alternative="greater").pvalue
        filas.append(dict(categoria=cat, partidos=n, gana_local=k, proporcion=k / n, ic_inf=lo, ic_sup=hi, p_valor=pv))
    r = pd.DataFrame(filas)
    fig = go.Figure()
    fig.add_bar(x=r.categoria, y=r.proporcion * 100,
                marker_color=[COLOR_CAT.get(c, "#52514e") for c in r.categoria],
                error_y=dict(type="data", symmetric=False, array=(r.ic_sup - r.proporcion) * 100,
                             arrayminus=(r.proporcion - r.ic_inf) * 100, color="#52514e"),
                text=(r.proporcion * 100).round(1).astype(str) + "%", textposition="outside",
                hovertemplate="%{x}: %{y:.1f}%<extra></extra>")
    fig.add_hline(y=50, line_dash="dot", line_color="#8a8983", annotation_text="50% (sin ventaja)")
    fig.update_layout(height=380, title=f"% de partidos ganados por el local (IC {int((1 - ALFA) * 100)}% de Wilson)",
                      yaxis_title="% ganados por el local", yaxis_range=[0, 100])
    chart(fig)
    st.dataframe(r.round(4), hide_index=True, width="stretch")
    veredicto(r.iloc[-1].p_valor, "el local gana más de la mitad de los partidos")

# ------------------------------------------------------------------ 2
with t2:
    st.markdown("**¿Las categorías anotan distinto?** · ANOVA de un factor + Kruskal-Wallis + Tukey HSD  \n"
                "H₀: la media de puntos por equipo y por partido es igual en las 4 categorías")
    todos = p[~p.wo]
    pts = pd.concat([todos[["categoria", "puntos_local"]].rename(columns={"puntos_local": "puntos"}),
                     todos[["categoria", "puntos_visitante"]].rename(columns={"puntos_visitante": "puntos"})])
    fig = px.box(pts, x="categoria", y="puntos", color="categoria", color_discrete_map=COLOR_CAT,
                 category_orders={"categoria": CATEGORIAS}, points=False)
    fig.update_layout(height=380, showlegend=False, title="Puntos por equipo y por partido", xaxis_title=None)
    chart(fig)
    grupos = [pts[pts.categoria == c].puntos for c in CATEGORIAS]
    f, p_anova = stats.f_oneway(*grupos)
    h, p_kw = stats.kruskal(*grupos)
    c = st.columns(4)
    c[0].metric("F (ANOVA)", f"{f:.1f}")
    c[1].metric("p (ANOVA)", f"{p_anova:.2g}")
    c[2].metric("H (Kruskal-Wallis)", f"{h:.1f}")
    c[3].metric("p (Kruskal)", f"{p_kw:.2g}")
    veredicto(p_anova, "al menos una categoría tiene un promedio de puntos distinto")
    st.markdown("**Comparaciones de a pares (Tukey HSD)** — ¿entre qué categorías está la diferencia?")
    tk = pairwise_tukeyhsd(pts.puntos, pts.categoria, alpha=ALFA)
    st.dataframe(pd.DataFrame(tk.summary().data[1:], columns=tk.summary().data[0]), hide_index=True, width="stretch")
    st.dataframe(pts.groupby("categoria").puntos.describe().round(1), width="stretch")

# ------------------------------------------------------------------ 3
with t3:
    st.markdown("**¿Los más altos toman más rebotes?** · Correlación de Pearson y regresión lineal por categoría  \n"
                "Una fila por jugador (promedios de la temporada, mínimo 10 partidos)")
    pj = (e.groupby(["dni_jugador", "jugador", "categoria", "posicion", "altura_cm"], as_index=False)
          .agg(pj=("rebotes", "size"), rebotes=("rebotes", "mean"), minutos=("minutos", "mean")))
    pj = pj[pj.pj >= 10]
    pj["rebotes_x40"] = pj.rebotes / pj.minutos * 40
    medida = st.radio("Medida", ["rebotes por partido", "rebotes cada 40 minutos"], horizontal=True)
    y = "rebotes" if medida.startswith("rebotes por") else "rebotes_x40"
    fig = px.scatter(pj, x="altura_cm", y=y, facet_col="categoria", trendline="ols", color="categoria",
                     color_discrete_map=COLOR_CAT, category_orders={"categoria": CATEGORIAS},
                     hover_data=["jugador", "posicion"], opacity=0.65)
    fig.update_traces(marker=dict(size=8, line=dict(width=1, color="white")))
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.update_layout(height=380, showlegend=False, title=f"Altura vs {medida}")
    fig.update_xaxes(title="altura (cm)")
    chart(fig)
    filas = []
    for cat in CATEGORIAS:
        d = pj[pj.categoria == cat]
        rr, pv = stats.pearsonr(d.altura_cm, d[y])
        reg = stats.linregress(d.altura_cm, d[y])
        filas.append(dict(categoria=cat, jugadores=len(d), r=rr, r2=rr ** 2, pendiente_por_10cm=reg.slope * 10, p_valor=pv))
    st.dataframe(pd.DataFrame(filas).round(4), hide_index=True, width="stretch")
    st.caption("pendiente_por_10cm = cuántos rebotes más toma, en promedio, un jugador 10 cm más alto.")

# ------------------------------------------------------------------ 4
with t4:
    st.markdown("**¿La posición influye en el tipo de tiro que se convierte?** · Test χ² de independencia  \n"
                "H₀: posición y tipo de tiro (libre / doble / triple) son independientes")
    orden_pos = ["Base", "Escolta", "Alero", "Ala-pivot", "Pivot"]
    tabla = e.groupby("posicion")[["libres", "dobles", "triples"]].sum().reindex(orden_pos)
    chi2, pv, gl, esperado = stats.chi2_contingency(tabla)
    v = np.sqrt(chi2 / (tabla.values.sum() * (min(tabla.shape) - 1)))
    resid = (tabla - esperado) / np.sqrt(esperado)
    c = st.columns(4)
    c[0].metric("χ²", f"{chi2:,.0f}".replace(",", "."))
    c[1].metric("Grados de libertad", gl)
    c[2].metric("p-valor", f"{pv:.2g}")
    c[3].metric("V de Cramér", f"{v:.3f}")
    veredicto(pv, "el tipo de tiro depende de la posición")
    lim = float(np.abs(resid.values).max())
    fig = px.imshow(resid.round(1), text_auto=True, color_continuous_scale=DIVERGENTE, zmin=-lim, zmax=lim,
                    aspect="auto")
    fig.update_layout(height=360, title="Residuos estandarizados (azul = más de lo esperado, naranja = menos)",
                      coloraxis_colorbar_title="residuo")
    chart(fig)
    st.markdown("**Tabla de contingencia (tiros convertidos)**")
    st.dataframe(tabla, width="stretch")

# ------------------------------------------------------------------ 5
with t5:
    st.markdown("**¿El que anduvo bien en el Apertura repite en el Clausura?** · Correlación de Spearman entre "
                "la posición final de cada club en los dos torneos")
    filas = []
    for cat in CATEGORIAS:
        pos = {}
        for tor in TORNEOS:
            t = tabla_fiba(id_torneo(tor, cat))
            pos[tor] = dict(zip(t.equipo, t.pos))
        for eq in pos["Apertura"]:
            filas.append(dict(categoria=cat, equipo=eq, apertura=pos["Apertura"][eq], clausura=pos["Clausura"][eq]))
    d = pd.DataFrame(filas)
    fig = px.scatter(d, x="apertura", y="clausura", color="categoria", facet_col="categoria",
                     color_discrete_map=COLOR_CAT, category_orders={"categoria": CATEGORIAS}, hover_data=["equipo"])
    fig.update_traces(marker=dict(size=10, line=dict(width=2, color="white")))
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.update_xaxes(dtick=2, autorange="reversed", title="pos. Apertura")
    fig.update_yaxes(dtick=2, autorange="reversed")
    fig.update_layout(height=360, showlegend=False, yaxis_title="pos. Clausura")
    chart(fig)
    res = []
    for cat in CATEGORIAS:
        s = d[d.categoria == cat]
        rho, pv = stats.spearmanr(s.apertura, s.clausura)
        res.append(dict(categoria=cat, rho_spearman=rho, p_valor=pv))
    res = pd.DataFrame(res)
    st.dataframe(res.round(4), hide_index=True, width="stretch")
    rho, pv = stats.spearmanr(d.apertura, d.clausura)
    veredicto(pv, f"hay asociación entre las posiciones de los dos torneos (ρ global = {rho:.2f})")
    st.caption("Tiene sentido: el generador le da a cada equipo una 'fuerza' fija para toda la temporada.")
