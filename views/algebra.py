import streamlit as st

from lib.db import ALGEBRA_FILE, explain, query
from lib.sqlfiles import leer_bloques
from lib.ui import encabezado, requiere_base

encabezado("Álgebra relacional", "sql/05_algebra_relacional.sql · árbol inicial, árbol optimizado y la consulta nueva",
           "Consulta con tres tablas, una condición de igualdad y una de rango. Árbol de ejecución en álgebra "
           "relacional, optimizarlo y escribir la nueva consulta SQL en base al árbol optimizado.")
requiere_base()

orig, opt = leer_bloques(ALGEBRA_FILE)[:2]

st.markdown("""
**Pregunta:** ¿qué jugadores hicieron **25 puntos o más** en un partido de **semifinal**?

| | |
|---|---|
| Tablas | `jugador` (J), `estadistica` (E), `partido` (P) |
| Igualdad | `P.fase = 'Semifinal'` |
| Rango | `E.puntos >= 25` |
""")

# tamanos reales de cada paso (para mostrar POR QUE conviene optimizar)
n = query("""
    select (select count(*) from jugador) as j, (select count(*) from estadistica) as e,
           (select count(*) from partido) as p,
           (select count(*) from estadistica where puntos >= 25) as e_f,
           (select count(*) from partido where fase = 'Semifinal') as p_f,
           (select count(*) from jugador j, estadistica e where j.dni_jugador = e.dni_jugador and e.puntos >= 25) as je
""").iloc[0]
res = query(orig.sql)
prod = int(n.j) * int(n.e) * int(n.p)


def fmt(x):
    return f"{int(x):,}".replace(",", ".")


ARBOL = """digraph {{ rankdir=BT; bgcolor="transparent";
node [shape=box, style="rounded,filled", fillcolor="#f3f2ee", color="#d4d3cd", fontname="Helvetica", fontsize=11];
edge [color="#8a8983", arrowhead=none];
{cuerpo} }}"""

a, b = st.columns(2)
with a:
    st.subheader("1 · Árbol inicial")
    st.graphviz_chart(ARBOL.format(cuerpo=f"""
        J [label="jugador\\n{fmt(n.j)} filas"]; E [label="estadistica\\n{fmt(n.e)} filas"]; P [label="partido\\n{fmt(n.p)} filas"];
        X1 [label="× (producto)\\n{fmt(int(n.j) * int(n.e))} filas", fillcolor="#fbe0d6"];
        X2 [label="× (producto)\\n{fmt(prod)} filas", fillcolor="#fbe0d6"];
        S [label="σ J.dni=E.dni ∧ E.id_partido=P.id_partido\\n∧ P.fase='Semifinal' ∧ E.puntos≥25\\n{len(res)} filas"];
        PI [label="π apellido, nombre, fecha, puntos", fillcolor="#cde2fb"];
        J -> X1; E -> X1; X1 -> X2; P -> X2; X2 -> S; S -> PI;"""))
with b:
    st.subheader("2 · Árbol optimizado")
    st.graphviz_chart(ARBOL.format(cuerpo=f"""
        J [label="jugador\\n{fmt(n.j)}"]; E [label="estadistica\\n{fmt(n.e)}"]; P [label="partido\\n{fmt(n.p)}"];
        PJ [label="π dni, apellido, nombre"];
        SE [label="σ puntos ≥ 25\\n{fmt(n.e_f)} filas", fillcolor="#d3f0e3"];
        PE [label="π dni, id_partido, puntos"];
        SP [label="σ fase = 'Semifinal'\\n{fmt(n.p_f)} filas", fillcolor="#d3f0e3"];
        PP [label="π id_partido, fecha"];
        J1 [label="⋈ J.dni = E.dni\\n{fmt(n.je)} filas"];
        J2 [label="⋈ E.id_partido = P.id_partido\\n{len(res)} filas"];
        PI [label="π apellido, nombre, fecha, puntos", fillcolor="#cde2fb"];
        J -> PJ; E -> SE -> PE; P -> SP -> PP; PJ -> J1; PE -> J1; J1 -> J2; PP -> J2; J2 -> PI;"""),
    )

st.markdown(f"""
**Qué se hizo para optimizar** (reglas de equivalencia del álgebra relacional):
1. **Bajar las selecciones** lo más cerca posible de las hojas: `σ puntos≥25` va directo sobre `estadistica`
   y `σ fase='Semifinal'` sobre `partido`. Así se trabaja con **{fmt(n.e_f)}** estadísticas en vez de {fmt(n.e)}
   y **{fmt(n.p_f)}** partidos en vez de {fmt(n.p)}.
2. **Producto cartesiano + selección = join**: las condiciones `J.dni = E.dni` y `E.id_partido = P.id_partido`
   convierten cada `×` en un `⋈`. El árbol inicial, leído al pie de la letra, arma un producto de
   **{fmt(prod)}** filas antes de filtrar.
3. **Proyecciones tempranas**: cada rama se queda solo con las columnas que necesita más arriba.
4. **Orden de los joins**: primero se juntan las dos relaciones más chicas ya filtradas.
""")

st.subheader("3 · Las dos consultas SQL")
c1, c2 = st.columns(2)
c1.markdown("**A1 · Original**")
c1.code(orig.sql, language="sql")
c2.markdown("**A2 · A partir del árbol optimizado**")
c2.code(opt.sql, language="sql")

r2 = query(opt.sql)
iguales = res.reset_index(drop=True).equals(r2.reset_index(drop=True))
if iguales:
    st.success(f"Las dos consultas devuelven exactamente las mismas {len(res)} filas.")
else:
    st.error("¡Las consultas no devuelven lo mismo!")
st.dataframe(res, hide_index=True, width="stretch")

st.subheader("4 · Qué hace PostgreSQL de verdad (EXPLAIN ANALYZE)")
p1, ms1 = explain(orig.sql)
p2, ms2 = explain(opt.sql)
c1, c2 = st.columns(2)
c1.metric("A1 · tiempo de ejecución", f"{ms1:.2f} ms")
c1.code(p1, language="text")
c2.metric("A2 · tiempo de ejecución", f"{ms2:.2f} ms")
c2.code(p2, language="text")
st.caption("El optimizador de PostgreSQL aplica solo estas mismas reglas (empuja los filtros y elige hash/nested "
           "joins), por eso los planes de A1 y A2 terminan siendo prácticamente iguales. La optimización del "
           "árbol es exactamente lo que el motor hace por dentro.")
