"""Como esta armada la base: el diagrama de tablas y las reglas de cada tabla."""
import streamlit as st

from lib.db import APP_DIR, TABLAS, query
from lib.ui import encabezado, requiere_base

encabezado("Cómo se guardan los datos", "El diagrama de tablas de la base de datos de la liga",
           """
Una **base de datos relacional** guarda la información en **tablas**. Cada tabla guarda un tipo de cosa
(clubes, jugadores, partidos…), cada **fila** es una cosa y cada **columna** es un dato de esa cosa.

Las tablas se conectan entre sí para no repetir información. Por ejemplo, un partido no guarda el nombre de
los equipos: guarda su número (`id_equipo`), y ese número apunta a la fila del equipo en la tabla `equipo`.
En el diagrama, esas conexiones son las **flechas**.

- **PK (clave primaria):** el dato que identifica a cada fila y no se puede repetir, como el DNI de una persona.
- **FK (clave foránea):** una columna que apunta a la PK de otra tabla. Si apunta a algo que no existe
  (un equipo inventado), la base no deja guardar el dato.
- **FK compuesta:** lo mismo, pero con varias columnas juntas. La flecha roja es la de `estadistica` hacia
  `plantel`: asegura que a un jugador solo se le carguen puntos en el equipo donde está fichado.
- **FK compuesta con la categoría:** `plantel`, `pase` y `partido` guardan también `id_categoria`, y sus FK
  apuntan a *(equipo, categoría)* y *(torneo, categoría)*. Como todas comparten la misma columna, la base no
  deja meter un equipo U15 en un torneo U17, ni hacer un pase de U13 a U15, ni armar un partido entre
  categorías distintas.
- **Índice único parcial:** `uq_partido_final` no deja cargar dos finales en el mismo torneo
  (es UNIQUE, pero solo para las filas con `fase = 'Final'`).
""")
requiere_base()

st.subheader("Diagrama de tablas")
st.image(str(APP_DIR / "assets" / "diagrama.png"), width="stretch")
st.caption("Cada caja es una tabla con sus columnas y su tipo de dato (INT = número entero, VARCHAR = texto, "
           "DATE = fecha, TIME = hora, SERIAL = número que la base pone sola). Las flechas van desde la FK "
           "hasta la tabla a la que apunta.")

# ------------------------------------------------------------ detalle por tabla
cols = query("""
    select c.table_name as tabla, c.column_name as columna, c.data_type as tipo,
           c.is_nullable = 'NO' as obligatorio
    from information_schema.columns c
    where c.table_schema = 'public' and c.table_name = any(%s)
    order by c.table_name, c.ordinal_position""", (TABLAS,))
restr = query("""
    select cl.relname as tabla, co.conname as nombre,
           case co.contype when 'p' then 'PK (clave primaria)' when 'f' then 'FK (clave foránea)'
                           when 'u' then 'UNIQUE (no se repite)' when 'c' then 'CHECK (regla sobre el valor)' end as tipo,
           pg_get_constraintdef(co.oid) as definicion
    from pg_constraint co
    join pg_class cl on cl.oid = co.conrelid
    join pg_namespace n on n.oid = cl.relnamespace and n.nspname = 'public'
    where co.contype in ('p', 'f', 'u', 'c')
    union all
    -- indices unicos que no son constraint (ej. el parcial de una sola final por torneo)
    select i.tablename, i.indexname, 'UNIQUE parcial (índice)', i.indexdef
    from pg_indexes i
    where i.schemaname = 'public' and i.indexdef ilike 'create unique index%'
      and not exists (select 1 from pg_constraint co where co.conname = i.indexname)
    order by 1, 3, 2""")

QUE_GUARDA = {
    "club": "Los 12 clubes de la liga",
    "categoria": "Las 4 categorías (U13, U15, U17, U19), con las edades y el nivel de entrenador que piden",
    "jugador": "Los datos personales de cada jugador",
    "arbitro": "Los 16 árbitros y su categoría (Nacional, Provincial o Aspirante)",
    "entrenador": "Los entrenadores, el club donde trabajan y su nivel ENEBA",
    "cancha": "La cancha de cada club y su capacidad",
    "equipo": "Los 48 equipos: un club en una categoría, con su entrenador",
    "torneo": "El Apertura y el Clausura de cada categoría",
    "plantel": "Qué jugador está en qué equipo en cada torneo (de la misma categoría) y con qué número de camiseta",
    "pase": "Los jugadores que cambiaron de club entre el Apertura y el Clausura, dentro de su categoría",
    "serie": "Los cruces del playoff (cuartos y semis, al mejor de 3)",
    "partido": "Cada partido: categoría, fecha, hora, cancha, equipos y resultado",
    "arbitro_partido": "Qué árbitros dirigieron cada partido y si fueron",
    "estadistica": "La planilla de cada jugador en cada partido (minutos, puntos, rebotes…)",
}

st.subheader("Qué guarda cada tabla y qué reglas tiene")
st.caption("Además de las conexiones, cada tabla tiene reglas que impiden cargar datos sin sentido "
           "(por ejemplo, un jugador con 6 faltas o un partido empatado). La base rechaza cualquier dato que no las cumpla.")
tabla = st.selectbox("Elegí una tabla", TABLAS, index=TABLAS.index("partido"),
                     format_func=lambda t: f"{t} — {QUE_GUARDA[t]}")
a, b = st.columns([2, 3])
with a:
    st.markdown("**Columnas**")
    st.dataframe(cols[cols.tabla == tabla][["columna", "tipo", "obligatorio"]], hide_index=True, width="stretch")
with b:
    st.markdown("**Reglas**")
    st.dataframe(restr[restr.tabla == tabla][["tipo", "nombre", "definicion"]], hide_index=True, width="stretch",
                 column_config={"definicion": st.column_config.TextColumn("cómo está escrita", width="large")})
