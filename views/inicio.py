import plotly.express as px
import streamlit as st

from lib.db import TABLAS, query
from lib.liga import CATEGORIAS, partidos
from lib.ui import ACENTO, COLOR_CAT, SERIES, chart, hero, kpis, requiere_base

hero("Liga de Básquet Formativo de Paraná",
     "Un tablero para recorrer la temporada 2026 de una liga de básquet juvenil, guardada en una base de datos")
requiere_base()

# ------------------------------------------------------------ que es esto
st.markdown("""
### ¿Qué es esto?

Una **liga de básquet formativo** es una liga para chicos que están aprendiendo a jugar.
Esta tiene **12 clubes de Paraná**, y cada club tiene **4 equipos**, uno por edad.
**Todos los datos de este tablero son de la temporada 2026.**

| Categoría | Edades en 2026 | Quiere decir |
|---|---|---|
| U13 | 11 y 12 años | *menores de 13* ("U" viene de *under*, "menor que") |
| U15 | 13 y 14 años | menores de 15 |
| U17 | 15 y 16 años | menores de 17 |
| U19 | 17 y 18 años | menores de 19 |

En 2026 cada categoría jugó dos torneos: el **Apertura** (primer semestre) y el **Clausura** (segundo).
En cada torneo primero **todos juegan contra todos** (fase regular) y los 8 mejores pasan al **playoff**:
cuartos de final, semifinal y final. Los nombres de los clubes son reales; los jugadores, resultados y
estadísticas son inventados por un programa, pero respetan todas las reglas de una liga de verdad.

Toda esa información está guardada en una **base de datos** (PostgreSQL): un conjunto de tablas conectadas
entre sí, como planillas de cálculo que se referencian unas a otras. Este tablero le hace preguntas a esa base
y muestra las respuestas con tablas y gráficos.
""")
st.info("**Todo lo que vas a ver corresponde a la temporada 2026:** torneos Apertura y Clausura, "
        "con sus partidos, jugadores, árbitros y estadísticas.", icon="📅")

with st.expander("📖 Glosario: palabras que aparecen en el tablero"):
    st.markdown("""
| Palabra | Qué significa |
|---|---|
| **Fase regular** | La primera parte del torneo: cada equipo juega una vez contra cada uno de los otros 11 (11 fechas) |
| **Fecha** | Una "ronda" de la fase regular: todos los equipos juegan un partido |
| **Playoff** | La etapa final: cuartos de final y semifinal se juegan al mejor de 3 partidos, la final a un solo partido |
| **Serie** | En el playoff, el cruce entre dos equipos; gana el primero que gana 2 partidos |
| **Tabla de posiciones** | El ranking: cada victoria da 2 puntos, cada derrota 1 y no presentarse 0 |
| **W.O.** | *Walkover*: un equipo no se presentó, pierde 20 a 0 |
| **Postergado** | Un partido que se pasó a otro día |
| **Pase** | Un jugador que cambió de club entre el Apertura y el Clausura |
| **Libre, doble, triple** | Tipos de tiro: valen 1, 2 y 3 puntos |
| **Rebote / asistencia** | Agarrar la pelota después de un tiro errado / el pase que termina en una canasta |
| **ENEBA** | La escuela de entrenadores; su nivel (1 a 3) dice qué categorías puede dirigir cada uno |
| **Base de datos / tabla** | Donde se guardan los datos; cada tabla guarda un tipo de cosa (jugadores, partidos…) |
""")

# ------------------------------------------------------------ numeros grandes
st.markdown("### La temporada 2026 en números")
p = partidos()
conteos = query(" union all ".join(f"select '{t}' as tabla, count(*) as filas from {t}" for t in TABLAS))
filas = dict(zip(conteos.tabla, conteos.filas))


def miles(n):
    return f"{int(n):,}".replace(",", ".")


# los numeros cuentan desde 0 al aparecer (solo la animacion; los valores son los de la base)
kpis([
    ("🏟️", "Clubes", filas["club"], "Los 12 clubes de Paraná", ACENTO),
    ("👕", "Equipos", filas["equipo"], "12 clubes × 4 categorías", ACENTO),
    ("⛹️", "Jugadores", filas["jugador"], "16 por equipo", ACENTO),
    ("🏀", "Partidos jugados", filas["partido"], "Fase regular + playoff de los 8 torneos", ACENTO),
    ("📋", "Entrenadores", filas["entrenador"], "Uno por equipo", ACENTO),
    ("🧑‍⚖️", "Árbitros", filas["arbitro"], "Nacionales, provinciales y aspirantes", ACENTO),
])
kpis([
    ("🏆", "Torneos", filas["torneo"], "Apertura y Clausura × 4 categorías", SERIES[0]),
    ("⚔️", "Series de playoff", filas["serie"], "Cuartos y semis, al mejor de 3", SERIES[0]),
    ("🚫", "W.O. (no se presentaron)", int(p.wo.sum()), "Partidos que terminaron 20 a 0 por ausencia", SERIES[0]),
    ("📅", "Partidos postergados", int(p.fecha_original.notna().sum()), "Pasados a otro día", SERIES[0]),
    ("🔁", "Pases entre clubes", filas["pase"], "Entre el Apertura y el Clausura", SERIES[0]),
    ("📊", "Planillas de jugadores", filas["estadistica"],
     "Una fila por cada jugador en cada partido: minutos, puntos, rebotes, etc.", SERIES[0]),
])

st.divider()
izq, der = st.columns([3, 2])

with izq:
    st.subheader("Campeones 2026")
    finales = p[p.fase == "Final"].copy()
    finales["campeon"] = finales.ganador.str.replace(r" U1\d$", "", regex=True)
    grilla = finales.pivot(index="torneo", columns="categoria", values="campeon").reindex(columns=CATEGORIAS)
    st.dataframe(grilla, width="stretch")
    st.caption("El ganador de cada final. La final se juega a un partido en cancha neutral: la más grande "
               "entre los clubes que no la juegan.")

    st.subheader("Partidos por etapa y categoría")
    fases = p.groupby(["fase", "categoria"]).size().rename("partidos").reset_index()
    fig = px.bar(fases, x="fase", y="partidos", color="categoria", barmode="group",
                 category_orders={"fase": ["Regular", "Cuartos", "Semifinal", "Final"], "categoria": CATEGORIAS},
                 color_discrete_map=COLOR_CAT, text="partidos")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=340, yaxis_title="partidos", xaxis_title=None)
    chart(fig)
    st.caption("La fase regular tiene 66 partidos por torneo y categoría; en cuartos y semis hay entre 2 y 3 "
               "partidos por serie, según si hizo falta el tercero.")

with der:
    st.subheader("Cuántos datos hay en cada tabla")
    fig = px.bar(conteos.sort_values("filas"), x="filas", y="tabla", orientation="h", log_x=True,
                 text="filas", color_discrete_sequence=[SERIES[0]])
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=520, xaxis_title="filas (escala logarítmica)", yaxis_title=None, margin_r=60)
    chart(fig)
    st.caption(f"En total hay {miles(conteos.filas.sum())} filas en 14 tablas. La escala es logarítmica "
               "porque las tablas van de 4 filas (categorías) a más de 15.000 (estadísticas).")

st.info("**Cómo usar el tablero:** elegí una página en el menú de la izquierda. En cada página, "
        "el recuadro **ℹ️ ¿Qué estoy viendo?** explica qué muestra y cómo leerlo.", icon="🧭")
