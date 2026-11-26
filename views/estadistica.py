"""Pruebas estadisticas sobre la temporada 2026: lo que no sale con SQL solo."""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.proportion import proportion_confint

from lib.liga import CATEGORIAS, TORNEOS, estadisticas_jugadores, id_torneo, partidos, tabla_fiba
from lib.ui import COLOR_CAT, DIVERGENTE, chart, encabezado, requiere_base

encabezado("Análisis estadístico", "Preguntas sobre la temporada 2026 respondidas con pruebas estadísticas",
           """
Mirar un gráfico puede engañar: una diferencia chica puede ser pura casualidad. Una **prueba estadística**
calcula qué tan probable sería ver esos datos **si en realidad no hubiera ningún efecto**. Esa probabilidad
es el **p-valor**:

- **p-valor chico** (menor que α, por defecto 0,05 = 5 %): es muy raro que salga así por casualidad, así que
  concluimos que el efecto **existe**.
- **p-valor grande:** los datos pueden explicarse por casualidad; **no hay evidencia** suficiente del efecto.

**H₀** (hipótesis nula) es la idea de "no hay efecto" que la prueba intenta descartar. Cada pestaña responde
una pregunta distinta y al final dice, en palabras, qué se concluye. El nivel α se puede cambiar en la
barra lateral.
""")
requiere_base()

ALFA = st.sidebar.select_slider("Nivel de significación α", [0.01, 0.05, 0.10], value=0.05)


def veredicto(p, si, no):
    """Conclusion de la prueba, en palabras."""
    if p < ALFA:
        st.success(f"**Conclusión:** {si}  \n(p-valor = {p:.2g}, menor que α = {ALFA}: es muy poco probable "
                   "que sea casualidad.)")
    else:
        st.info(f"**Conclusión:** {no}  \n(p-valor = {p:.2g}, mayor que α = {ALFA}: puede ser casualidad.)")


p = partidos()
jugados = p[(p.fase == "Regular") & (~p.wo)].copy()
e = estadisticas_jugadores()

t1, t2, t3, t4, t5 = st.tabs(["Ventaja de local", "Puntos por categoría", "Altura y rebotes",
                              "Posición y tipo de tiro", "Apertura vs Clausura"])

# ------------------------------------------------------------------ 1
with t1:
    st.markdown("### ¿Jugar en tu cancha ayuda a ganar?\n"
                "Si jugar de local no diera ninguna ventaja, el local ganaría la mitad de los partidos, como al "
                "tirar una moneda. Se cuentan los partidos de fase regular de 2026 (sin los W.O.) y se compara "
                "con ese 50 %.  \n"
                "*Prueba: test binomial · H₀: el local gana el 50 % de los partidos.*")
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
    fig.update_layout(height=380, yaxis_title="% ganados por el local", yaxis_range=[0, 100],
                      title=f"% de partidos ganados por el local (la rayita es el margen de error, "
                            f"al {int((1 - ALFA) * 100)}%)")
    chart(fig)
    st.dataframe(r.round(4), hide_index=True, width="stretch")
    total = r.iloc[-1]
    veredicto(total.p_valor,
              f"sí, jugar de local ayuda: en 2026 el local ganó el {total.proporcion:.0%} de los partidos.",
              f"no se puede afirmar que jugar de local ayude (el local ganó el {total.proporcion:.0%}).")

# ------------------------------------------------------------------ 2
with t2:
    st.markdown("### ¿Los más grandes hacen más puntos?\n"
                "Se comparan los puntos que hace un equipo en un partido según la categoría. En el gráfico, cada "
                "caja muestra dónde está la mitad de los partidos y la línea del medio es el valor típico.  \n"
                "*Pruebas: ANOVA y Kruskal-Wallis (¿hay alguna diferencia?) y Tukey (¿entre cuáles?) · "
                "H₀: las 4 categorías hacen en promedio los mismos puntos.*")
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
    c[1].metric("p-valor (ANOVA)", f"{p_anova:.2g}")
    c[2].metric("H (Kruskal-Wallis)", f"{h:.1f}")
    c[3].metric("p-valor (Kruskal)", f"{p_kw:.2g}")
    medias = pts.groupby("categoria").puntos.mean()
    veredicto(p_anova,
              f"sí, las categorías anotan distinto: el promedio por equipo va de {medias['U13']:.0f} puntos "
              f"en U13 a {medias['U19']:.0f} en U19.",
              "no hay evidencia de que las categorías anoten distinto.")
    st.markdown("**Comparación de a pares (Tukey):** cada fila compara dos categorías; "
                "`reject = True` quiere decir que la diferencia entre esas dos es real.")
    tk = pairwise_tukeyhsd(pts.puntos, pts.categoria, alpha=ALFA)
    st.dataframe(pd.DataFrame(tk.summary().data[1:], columns=tk.summary().data[0]), hide_index=True, width="stretch")
    st.dataframe(pts.groupby("categoria").puntos.describe().round(1), width="stretch")

# ------------------------------------------------------------------ 3
with t3:
    st.markdown("### ¿Los más altos agarran más rebotes?\n"
                "Cada punto es un jugador (con 10 partidos o más en 2026): su altura y sus rebotes. La línea "
                "muestra la tendencia: si sube, los más altos agarran más rebotes.  \n"
                "*Prueba: correlación de Pearson (r va de -1 a 1; cerca de 0 = no hay relación, cerca de 1 = "
                "relación fuerte) y regresión lineal.*")
    pj = (e.groupby(["dni_jugador", "jugador", "categoria", "posicion", "altura_cm"], as_index=False)
          .agg(pj=("rebotes", "size"), rebotes=("rebotes", "mean"), minutos=("minutos", "mean")))
    pj = pj[pj.pj >= 10]
    pj["rebotes_x40"] = pj.rebotes / pj.minutos * 40
    medida = st.radio("Medida", ["rebotes por partido", "rebotes cada 40 minutos"], horizontal=True,
                      help="'Cada 40 minutos' compara como si todos hubieran jugado el partido entero.")
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
        filas.append(dict(categoria=cat, jugadores=len(d), r=rr, r2=rr ** 2, pendiente_por_10cm=reg.slope * 10,
                          p_valor=pv))
    corr = pd.DataFrame(filas)
    st.dataframe(corr.round(4), hide_index=True, width="stretch")
    st.caption("pendiente_por_10cm = cuántos rebotes más agarra, en promedio, un jugador 10 cm más alto. "
               "r2 = qué parte de las diferencias de rebotes se explica por la altura (de 0 a 1).")
    veredicto(corr.p_valor.max(),
              f"sí, en las 4 categorías los más altos agarran más rebotes (r entre {corr.r.min():.2f} y "
              f"{corr.r.max():.2f}).",
              "en al menos una categoría no hay evidencia de que la altura influya en los rebotes.")

# ------------------------------------------------------------------ 4
with t4:
    st.markdown("### ¿Cada posición anota de una forma distinta?\n"
                "En básquet hay 5 posiciones: el **base** organiza el juego, el **escolta** y el **alero** tiran "
                "más de afuera, y el **ala-pivot** y el **pivot** juegan cerca del aro. Se cuenta cuántos libres, "
                "dobles y triples convirtió cada posición en 2026.  \n"
                "*Prueba: χ² (chi cuadrado) de independencia · H₀: todas las posiciones reparten sus tiros igual.*")
    orden_pos = ["Base", "Escolta", "Alero", "Ala-pivot", "Pivot"]
    tabla = e.groupby("posicion")[["libres", "dobles", "triples"]].sum().reindex(orden_pos)
    chi2, pv, gl, esperado = stats.chi2_contingency(tabla)
    v = np.sqrt(chi2 / (tabla.values.sum() * (min(tabla.shape) - 1)))
    resid = (tabla - esperado) / np.sqrt(esperado)
    c = st.columns(4)
    c[0].metric("χ²", f"{chi2:,.0f}".replace(",", "."))
    c[1].metric("Grados de libertad", gl)
    c[2].metric("p-valor", f"{pv:.2g}")
    c[3].metric("V de Cramér", f"{v:.3f}", help="Qué tan fuerte es la relación: 0 = nada, 1 = total.")
    veredicto(pv, "sí, cada posición anota distinto. En el mapa de abajo, azul = esa posición convierte más de ese "
                  "tiro de lo esperado; naranja = menos.",
              "no hay evidencia de que la posición cambie el tipo de tiro.")
    lim = float(np.abs(resid.values).max())
    fig = px.imshow(resid.round(1), text_auto=True, color_continuous_scale=DIVERGENTE, zmin=-lim, zmax=lim,
                    aspect="auto")
    fig.update_layout(height=360, title="Diferencia con lo esperado (azul = más de lo esperado, naranja = menos)",
                      coloraxis_colorbar_title="diferencia")
    chart(fig)
    st.markdown("**Tiros convertidos por posición en 2026**")
    st.dataframe(tabla, width="stretch")

# ------------------------------------------------------------------ 5
with t5:
    st.markdown("### ¿El que anduvo bien en el Apertura repite en el Clausura?\n"
                "Cada punto es un equipo: en qué puesto terminó el Apertura 2026 (eje horizontal) y el Clausura "
                "(eje vertical). Si los puntos forman una diagonal, los buenos siguieron siendo buenos.  \n"
                "*Prueba: correlación de Spearman (ρ va de -1 a 1; cerca de 1 = el orden se repite).*")
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
    fig.update_xaxes(dtick=2, autorange="reversed", title="puesto Apertura")
    fig.update_yaxes(dtick=2, autorange="reversed")
    fig.update_layout(height=360, showlegend=False, yaxis_title="puesto Clausura")
    chart(fig)
    res = []
    for cat in CATEGORIAS:
        s = d[d.categoria == cat]
        rho, pv = stats.spearmanr(s.apertura, s.clausura)
        res.append(dict(categoria=cat, rho_spearman=rho, p_valor=pv))
    st.dataframe(pd.DataFrame(res).round(4), hide_index=True, width="stretch")
    rho, pv = stats.spearmanr(d.apertura, d.clausura)
    veredicto(pv, f"sí, los que terminaron arriba en el Apertura tienden a terminar arriba en el Clausura (ρ = {rho:.2f}).",
              f"no hay evidencia de que el puesto del Apertura se repita en el Clausura (ρ = {rho:.2f}).")
    st.caption("El programa que generó los datos le da a cada equipo un nivel para toda la temporada, pero el azar "
               "de cada partido pesa mucho y hay solo 12 equipos por categoría: una relación débil no alcanza "
               "para descartar la casualidad.")
