"""Acceso a PostgreSQL: conexion, consultas cacheadas y carga de los scripts.

Toda la app pasa por aca: las paginas llaman a query() y reciben un DataFrame.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import psycopg
import streamlit as st
from psycopg import sql as pgsql
from psycopg.conninfo import make_conninfo
from psycopg.types.numeric import FloatLoader

APP_DIR = Path(__file__).resolve().parent.parent
SQL_DIR = APP_DIR / "sql"

# version final de los scripts (con id_categoria en plantel, pase y partido)
DDL_FILE = SQL_DIR / "01_ddl_liga_basquet.sql"
DML_FILE = SQL_DIR / "02_dml_carga_datos.sql"
CONTROLES_FILE = SQL_DIR / "03_controles.sql"

TABLAS = ["club", "categoria", "jugador", "arbitro", "entrenador", "cancha", "equipo",
          "torneo", "plantel", "pase", "serie", "partido", "arbitro_partido", "estadistica"]


def _default_config() -> dict:
    """Toma la conexion de .streamlit/secrets.toml ([postgres]) o de las variables PG*."""
    cfg = {}
    try:
        cfg = dict(st.secrets.get("postgres", {}))
    except Exception:  # no hay secrets.toml
        pass
    return {
        "host": cfg.get("host", os.getenv("PGHOST", "localhost")),
        "port": int(cfg.get("port", os.getenv("PGPORT", 5432))),
        "dbname": cfg.get("dbname", os.getenv("PGDATABASE", "liga_basquet")),
        "user": cfg.get("user", os.getenv("PGUSER", "postgres")),
        "password": cfg.get("password", os.getenv("PGPASSWORD", "")),
    }


def get_config() -> dict:
    if "pg" not in st.session_state:
        st.session_state.pg = _default_config()
    return st.session_state.pg


def conninfo(cfg: dict | None = None, dbname: str | None = None) -> str:
    cfg = dict(cfg or get_config())
    if dbname:
        cfg["dbname"] = dbname
    if not cfg.get("password"):
        cfg.pop("password", None)
    return make_conninfo(**cfg, connect_timeout=5)


def connect(cfg: dict | None = None, dbname: str | None = None, **kw) -> psycopg.Connection:
    conn = psycopg.connect(conninfo(cfg, dbname), **kw)
    conn.adapters.register_loader("numeric", FloatLoader)  # numeric -> float (no Decimal)
    return conn


def ping() -> tuple[bool, str]:
    """(True, '') si la base responde y tiene las tablas cargadas."""
    try:
        with connect() as conn:
            n = conn.execute("select count(*) from information_schema.tables "
                             "where table_schema = 'public' and table_name = any(%s)", (TABLAS,)).fetchone()[0]
            if n < len(TABLAS):
                return False, f"La base existe pero tiene {n} de las {len(TABLAS)} tablas. Usá 'Crear / recargar base'."
            filas = conn.execute("select count(*) from partido").fetchone()[0]
            if filas == 0:
                return False, "Las tablas existen pero estan vacias. Usá 'Crear / recargar base'."
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, str(e).strip().splitlines()[0]


def _rows_to_df(cur) -> pd.DataFrame:
    if cur.description is None:
        return pd.DataFrame()
    return pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])


@st.cache_data(ttl=3600, show_spinner=False)
def _query(info: str, sql: str, params: tuple | None) -> pd.DataFrame:
    with psycopg.connect(info) as conn:
        conn.adapters.register_loader("numeric", FloatLoader)
        return _rows_to_df(conn.execute(sql, params))


def query(sql: str, params: tuple | None = None) -> pd.DataFrame:
    """Corre un select y devuelve un DataFrame (cacheado una hora)."""
    return _query(conninfo(), sql, params)


def run_in_rollback(statements: list[str], check_sql: str | None = None) -> dict:
    """Corre sentencias dentro de una transaccion que SIEMPRE se deshace.

    Sirve para la demo de "datos truchos": devuelve el error (y la restriccion
    que salto) o, si no hubo error, el resultado de check_sql.
    """
    out = {"ok": True, "error": None, "constraint": None, "sqlstate": None, "rowcount": 0, "check": None}
    with connect() as conn:
        try:
            with conn.cursor() as cur:
                for s in statements:
                    cur.execute(s)
                    out["rowcount"] += max(cur.rowcount, 0)
                if check_sql:
                    cur.execute(check_sql)
                    out["check"] = _rows_to_df(cur)
        except psycopg.Error as e:
            out.update(ok=False, error=str(e).strip(), sqlstate=e.sqlstate,
                       constraint=getattr(e.diag, "constraint_name", None))
        finally:
            conn.rollback()
    return out


def crear_y_cargar(progress=None) -> None:
    """Crea la base si no existe y corre sql/01 (DDL) y sql/02 (poblado)."""
    cfg = get_config()
    with connect(dbname="postgres", autocommit=True) as conn:
        existe = conn.execute("select 1 from pg_database where datname = %s", (cfg["dbname"],)).fetchone()
        if not existe:
            conn.execute(pgsql.SQL("create database {}").format(pgsql.Identifier(cfg["dbname"])))
    for i, f in enumerate([DDL_FILE, DML_FILE]):
        if progress:
            progress(i, f.name)
        with connect() as conn:
            conn.execute(f.read_text(encoding="utf-8"))  # sin parametros: admite varias sentencias
            conn.commit()
    st.cache_data.clear()
