"""El modelo leido DIRECTO del catalogo de PostgreSQL (no dibujado a mano)."""
import streamlit as st

from lib.db import DDL_FILE, TABLAS, query
from lib.ui import encabezado, requiere_base

encabezado("Modelo de datos", "14 tablas · leído del catálogo de PostgreSQL (information_schema / pg_constraint)")
requiere_base()

cols = query("""
    select c.table_name as tabla, c.column_name as columna, c.data_type as tipo,
           c.is_nullable = 'NO' as not_null, c.ordinal_position
    from information_schema.columns c
    where c.table_schema = 'public' and c.table_name = any(%s)
    order by c.table_name, c.ordinal_position""", (TABLAS,))

restr = query("""
    select cl.relname as tabla, co.conname as restriccion,
           case co.contype when 'p' then 'PK' when 'f' then 'FK' when 'u' then 'UNIQUE'
                           when 'c' then 'CHECK' end as tipo,
           pg_get_constraintdef(co.oid) as definicion,
           ref.relname as referencia,
           array_length(co.conkey, 1) as n_columnas
    from pg_constraint co
    join pg_class cl on cl.oid = co.conrelid
    join pg_namespace n on n.oid = cl.relnamespace and n.nspname = 'public'
    left join pg_class ref on ref.oid = co.confrelid
    where co.contype in ('p', 'f', 'u', 'c')
    order by cl.relname, co.contype, co.conname""")

c = st.columns(5)
c[0].metric("Tablas", len(TABLAS))
for i, t in enumerate(["PK", "FK", "UNIQUE", "CHECK"], start=1):
    c[i].metric(t, int((restr.tipo == t).sum()))

# ------------------------------------------------------------ diagrama
st.subheader("Diagrama de tablas (generado desde las FK)")
pk = restr[restr.tipo == "PK"].set_index("tabla").definicion.str.extract(r"\((.*)\)")[0].to_dict()
fks = restr[restr.tipo == "FK"]


def nodo(t):
    filas = cols[cols.tabla == t]
    claves = [x.strip() for x in pk.get(t, "").split(",")]
    fk_cols = set(",".join(fks[fks.tabla == t].definicion.str.extract(r"KEY \((.*?)\)")[0]).replace(" ", "").split(","))
    renglones = []
    for r in filas.itertuples():
        marca = "🔑 " if r.columna in claves else ("🔗 " if r.columna in fk_cols else "")
        renglones.append(f'<tr><td align="left">{marca}{r.columna}</td><td align="left"><font color="#8a8983">{r.tipo.replace("character varying", "varchar").replace("time without time zone", "time")}</font></td></tr>')
    return (f'"{t}" [label=<<table border="0" cellborder="1" cellspacing="0" cellpadding="3">'
            f'<tr><td colspan="2" bgcolor="#2a78d6"><font color="white"><b>{t}</b></font></td></tr>'
            + "".join(renglones) + "</table>>]")


lineas = ['digraph G { rankdir=LR; graph [bgcolor="transparent", nodesep=0.3, ranksep=0.9];',
          'node [shape=plaintext, fontname="Helvetica", fontsize=10]; edge [color="#8a8983", arrowsize=0.6];']
lineas += [nodo(t) for t in TABLAS]
for r in fks.itertuples():
    compuesta = r.n_columnas > 1
    estilo = ', color="#e34948", penwidth=2' if compuesta else ""
    lineas.append(f'"{r.tabla}" -> "{r.referencia}" [tooltip="{r.restriccion}"{estilo}];')
lineas.append("}")
st.graphviz_chart("\n".join(lineas), width="stretch")
st.caption("🔑 PK · 🔗 FK · flechas rojas = **FK compuestas** (equipo→entrenador, partido→serie, "
           "estadistica→plantel, estadistica→partido): son las que garantizan reglas entre tablas.")

# ------------------------------------------------------------ detalle por tabla
st.subheader("Restricciones por tabla")
tabla = st.selectbox("Tabla", TABLAS, index=TABLAS.index("partido"))
a, b = st.columns([2, 3])
with a:
    st.markdown("**Columnas**")
    st.dataframe(cols[cols.tabla == tabla][["columna", "tipo", "not_null"]], hide_index=True, width="stretch")
with b:
    st.markdown("**Restricciones**")
    st.dataframe(restr[restr.tabla == tabla][["tipo", "restriccion", "definicion"]], hide_index=True,
                 width="stretch", column_config={"definicion": st.column_config.TextColumn(width="large")})

with st.expander("Ver el DDL completo (PARTE 2/01_ddl_liga_basquet.sql)"):
    st.code(DDL_FILE.read_text(encoding="utf-8"), language="sql")
