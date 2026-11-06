# Dashboard · Liga de Básquet Formativo de Paraná

Interfaz de acceso a datos del **TP Final de Base de Datos – Parte 2** (consigna, punto 4).
Integrantes: Tomiozzo Franco y Schmidt Gonzalo.

Hecha en **Python** con Streamlit (interfaz), Plotly (gráficos), psycopg 3 (conexión a PostgreSQL)
y SciPy / statsmodels (tests estadísticos).

## Requisitos

- Python 3.11 o superior
- PostgreSQL 13 o superior (probado con PostgreSQL 15)
- Los módulos de `requirements.txt`

## Cómo correrlo

```bash
cd app-dashboard
python -m venv .venv
.venv\Scripts\activate          # en Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Se abre en <http://localhost:8501>.

### Conexión a la base

Tres formas (la primera que encuentre):

1. Copiar `.streamlit/secrets.toml.example` como `.streamlit/secrets.toml` y completar la contraseña.
2. Variables de entorno `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`.
3. Desde la barra lateral del dashboard (**Conexión a PostgreSQL**).

Si la base `liga_basquet` no existe o está vacía, el botón **Crear / recargar base** la crea y corre
`sql/01_ddl_liga_basquet.sql` y `sql/02_dml_carga_datos.sql` (tarda menos de un segundo).

> Los `01`, `02` y `03` de `sql/` son copias de la carpeta `PARTE 2` del TP. Si el dashboard está dentro de la
> carpeta del TP (con `PARTE 2` al lado), usa los originales de ahí; si no, usa estas copias.

## Qué hay en cada página

| Página | Qué muestra | Consigna |
|---|---|---|
| Inicio | Números de la temporada, campeones, filas por tabla, mapa de la consigna | — |
| Modelo de datos | Diagrama de tablas generado desde las FK del catálogo, todas las PK/FK/UNIQUE/CHECK | Parte 1 |
| Posiciones y playoff | Tabla con desempate FIBA (calculado en Python), evolución fecha a fecha, cuadro del playoff | 4 |
| Jugadores | Líderes, perfil y planilla de cada jugador, de dónde salen los puntos por categoría | 4 |
| Árbitros y calendario | Designaciones, asistencia, mapa de calor día/horario | 4 |
| Consultas complejas | Corre `sql/04_consultas_complejas.sql` (Q1–Q8) + consulta libre de solo lectura | 2 |
| Álgebra relacional | Árbol inicial y optimizado con filas reales, A1 vs A2 y `EXPLAIN ANALYZE` | 3 |
| Controles de integridad | Corre C1–C30 de `03_controles.sql`; demo de datos truchos con `rollback` | 1 |
| Análisis estadístico | Test binomial (ventaja de local), ANOVA + Tukey, Pearson/regresión, χ², Spearman | 4 |
| Grafo del código | Grafo de graphify del DDL y de `generar_datos.py` (no está en el repo: se genera local con graphify en `graphify-out/`) | — |

El dashboard **lee los .sql del TP tal cual** (separa cada consulta por su encabezado `-- C1)`, `-- Q1)`, etc.):
si se modifica un archivo, el dashboard muestra la versión nueva.

## Archivos

```
app-dashboard/
├── app.py                      # punto de entrada y barra lateral
├── lib/
│   ├── db.py                   # conexión, consultas cacheadas, carga de scripts, rollback
│   ├── liga.py                 # consultas compartidas + tabla FIBA
│   ├── sqlfiles.py             # separa los .sql en bloques
│   └── ui.py                   # paleta de colores y plantilla de gráficos
├── views/                      # una página por archivo
├── sql/
│   ├── 01_ddl_liga_basquet.sql      # copia de PARTE 2: crea las 14 tablas
│   ├── 02_dml_carga_datos.sql       # copia de PARTE 2: poblado (generado por generar_datos.py)
│   ├── 03_controles.sql             # copia de PARTE 2: controles C1-C30
│   ├── 04_consultas_complejas.sql   # las 6 consultas complejas (+2)
│   └── 05_algebra_relacional.sql    # consulta original y optimizada
└── requirements.txt
```
