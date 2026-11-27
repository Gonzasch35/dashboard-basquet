# Dashboard · Liga de Básquet Formativo de Paraná (temporada 2026)

Un tablero web para recorrer la **temporada 2026** de una liga de básquet juvenil de Paraná, guardada en una
base de datos PostgreSQL. Es la interfaz de acceso a datos del TP Final de Base de Datos (Parte 2).
Integrantes: Tomiozzo Franco y Schmidt Gonzalo.

## ¿De qué se trata?

La liga tiene 12 clubes y cada uno tiene 4 equipos, uno por edad: **U13** (11 y 12 años), **U15**, **U17**
y **U19** ("U" viene de *under*, "menor que"). En 2026 cada categoría jugó dos torneos, el **Apertura** y el
**Clausura**: primero todos contra todos, y los 8 mejores pasan al **playoff** (cuartos, semifinal y final).

Todo eso (jugadores, partidos, resultados, árbitros y la planilla de cada jugador en cada partido) está
guardado en una base de datos de 14 tablas. Los nombres de los clubes son reales; el resto de los datos es
inventado por un programa, respetando las reglas de la liga. **Todos los datos son de la temporada 2026.**

## Qué muestra

| Página | Qué muestra |
|---|---|
| Inicio | Qué es la liga, un glosario, los números de la temporada y los campeones |
| Cómo se guardan los datos | El diagrama de tablas y las reglas de cada tabla |
| Posiciones y playoff | La tabla de cada torneo (con desempate FIBA), cómo cambió fecha a fecha y el playoff |
| Jugadores | Los líderes, el perfil de cada jugador partido a partido y de qué tiro salen los puntos |
| Árbitros y calendario | Cuántos partidos dirigió cada árbitro, las ausencias y los días y horarios de juego |
| Análisis estadístico | Cinco preguntas sobre la temporada respondidas con pruebas estadísticas |

Cada página tiene un recuadro **ℹ️ ¿Qué estoy viendo?** que explica qué muestra y cómo leerla.

## Requisitos

- Python 3.11 o superior
- PostgreSQL 13 o superior (probado con PostgreSQL 15)
- Los módulos de `requirements.txt`: Streamlit (la página web), psycopg (conexión a PostgreSQL),
  pandas (tablas), Plotly (gráficos), SciPy y statsmodels (pruebas estadísticas)

## Cómo correrlo

```bash
python -m venv .venv
.venv\Scripts\activate          # en Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Se abre en el navegador en <http://localhost:8501>.

### Conexión a la base

Tres formas (se usa la primera que encuentre):

1. Copiar `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml` y completar la contraseña.
2. Variables de entorno `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`.
3. Desde la barra lateral del dashboard (**Conexión a PostgreSQL**).

Si la base `liga_basquet` no existe o está vacía, el botón **Crear / recargar base** la crea y carga los
datos de 2026 (corre `sql/01_ddl_liga_basquet.sql` y `sql/02_dml_carga_datos.sql`; tarda menos de un segundo).

## Diseño para la presentación

- **Modo oscuro** (`.streamlit/config.toml`): fondo casi negro, texto claro y el naranja de la pelota como acento.
  Los gráficos usan los mismos colores de siempre por categoría (U13 azul, U15 naranja, U17 verde agua,
  U19 amarillo), con el tono ajustado para fondo oscuro.
- **Efectos** (`lib/ui.py`): portada con la pelota picando sobre las líneas de una cancha, números que cuentan
  desde 0, tarjetas que se levantan al pasar el mouse, bloques que aparecen al entrar a cada página y
  gráficos que se mueven suave al cambiar un filtro. Si la compu tiene activado "reducir movimiento", se apagan.
- **🔍 Letra grande (para proyectar)**: interruptor en la barra lateral que agranda el texto de las páginas y de
  los gráficos para que se lea desde el fondo del aula.

Los datos y las consultas no cambian: es solo cómo se ven.

## Archivos

```
app-dashboard/
├── app.py                      # punto de entrada, menú y barra lateral
├── assets/
│   └── diagrama.png            # diagrama de tablas (versión final, con id_categoria)
├── lib/
│   ├── db.py                   # conexión, consultas y carga de la base
│   ├── liga.py                 # consultas de la liga y tabla con desempate FIBA
│   ├── sqlfiles.py             # separa 03_controles.sql en bloques (C1, C2, … E1, …)
│   └── ui.py                   # modo oscuro, efectos (CSS), colores de gráficos y encabezados
├── views/                      # una página por archivo
├── sql/
│   ├── 01_ddl_liga_basquet.sql      # crea las 14 tablas (versión final, con id_categoria en plantel/pase/partido)
│   ├── 02_dml_carga_datos.sql       # datos de la temporada 2026
│   ├── 03_controles.sql             # controles de las reglas de la liga
│   ├── 04_consultas_complejas.sql   # consultas complejas (Q1 a Q8)
│   └── 05_algebra_relacional.sql    # consulta original y optimizada
└── requirements.txt
```

Los `.sql` 01 a 03 son la **versión final** de la Parte 2: `plantel`, `pase` y `partido` guardan
`id_categoria` y sus FK compuestas a *(equipo, categoría)* y *(torneo, categoría)* hacen que el DDL frene lo que
antes revisaban los controles C3, C6 y C9 (quedan como doble chequeo). Además hay un índice único parcial
(`uq_partido_final`) que permite una sola final por torneo. La página **Controles de integridad** corre los
controles de `03_controles.sql` y muestra cómo la base rechaza datos truchos (siempre con rollback).
Las consultas complejas y el álgebra relacional se explican en el informe del TP, no en el dashboard.
