"""Consultas de la liga que usan varias paginas + la tabla FIBA completa.

La tabla con desempate FIBA (puntos entre los empatados, diferencia entre
ellos y despues diferencia general) es incomoda de hacer solo con SQL, asi
que se calcula aca en Python a partir de los partidos que trae la base.
"""
from __future__ import annotations

import pandas as pd

from lib.db import query

CATEGORIAS = ["U13", "U15", "U17", "U19"]
TORNEOS = ["Apertura", "Clausura"]


def torneos() -> pd.DataFrame:
    return query("""
        select t.id_torneo, t.nombre as torneo, t.temporada, ca.nombre as categoria,
               t.fecha_inicio, t.fecha_fin
        from torneo t join categoria ca on ca.id_categoria = t.id_categoria
        order by t.id_torneo""")


def id_torneo(nombre: str, categoria: str) -> int:
    t = torneos()
    return int(t[(t.torneo == nombre) & (t.categoria == categoria)].id_torneo.iloc[0])


def partidos(id_torneo: int | None = None) -> pd.DataFrame:
    """Todos los partidos con nombres de equipos, club, cancha y categoria."""
    df = query("""
        select p.id_partido, p.id_torneo, t.nombre as torneo, ca.nombre as categoria, p.fase,
               p.nro_fecha, p.id_serie, p.nro_partido_serie, p.fecha, p.hora,
               c.nombre as cancha, p.id_equipo_local, l.nombre as local, cl.nombre as club_local,
               p.id_equipo_visitante, v.nombre as visitante, cv.nombre as club_visitante,
               p.puntos_local, p.puntos_visitante, p.id_equipo_ausente,
               p.fecha_original, p.motivo_postergacion
        from partido p
        join torneo t on t.id_torneo = p.id_torneo
        join categoria ca on ca.id_categoria = p.id_categoria  -- partido ya guarda su categoria
        join cancha c on c.id_cancha = p.id_cancha
        join equipo l on l.id_equipo = p.id_equipo_local
        join club cl on cl.id_club = l.id_club
        join equipo v on v.id_equipo = p.id_equipo_visitante
        join club cv on cv.id_club = v.id_club
        order by p.fecha, p.hora""")
    df["ganador"] = df.local.where(df.puntos_local > df.puntos_visitante, df.visitante)
    df["margen"] = (df.puntos_local - df.puntos_visitante).abs()
    df["wo"] = df.id_equipo_ausente.notna()
    if id_torneo is not None:
        df = df[df.id_torneo == id_torneo]
    return df


def _puntos_tabla(mio: int, otro: int, ausente: bool) -> int:
    return 2 if mio > otro else (0 if ausente else 1)


def tabla_fiba(id_torneo: int, hasta_fecha: int | None = None) -> pd.DataFrame:
    """Tabla de posiciones con el desempate FIBA (igual que generar_datos.tabla)."""
    p = partidos(id_torneo)
    p = p[p.fase == "Regular"]
    if hasta_fecha is not None:
        p = p[p.nro_fecha <= hasta_fecha]
    filas = []
    for _, r in p.iterrows():
        for eq, nombre, mio, otro in ((r.id_equipo_local, r.local, r.puntos_local, r.puntos_visitante),
                                      (r.id_equipo_visitante, r.visitante, r.puntos_visitante, r.puntos_local)):
            aus = r.id_equipo_ausente == eq
            filas.append(dict(id_equipo=eq, equipo=nombre, rival=r.id_equipo_local if eq != r.id_equipo_local
                              else r.id_equipo_visitante, pf=mio, pc=otro, pg=int(mio > otro),
                              pp=int(mio < otro), wo=int(aus), pts=_puntos_tabla(mio, otro, aus)))
    d = pd.DataFrame(filas)
    if d.empty:
        return d
    t = d.groupby(["id_equipo", "equipo"], as_index=False).agg(
        pj=("pts", "size"), pg=("pg", "sum"), pp=("pp", "sum"), wo=("wo", "sum"),
        pf=("pf", "sum"), pc=("pc", "sum"), pts=("pts", "sum"))
    t["dif"] = t.pf - t.pc

    def entre_ellos(eq, grupo):
        sub = d[(d.id_equipo == eq) & (d.rival.isin(grupo))]
        return sub.pts.sum(), (sub.pf - sub.pc).sum()

    orden = []
    for pts in sorted(t.pts.unique(), reverse=True):
        grupo = t[t.pts == pts]
        ids = set(grupo.id_equipo)
        claves = {r.id_equipo: (*entre_ellos(r.id_equipo, ids), r.dif) for r in grupo.itertuples()}
        orden += sorted(ids, key=lambda e: claves[e], reverse=True)
        if len(ids) > 1:
            for e in ids:
                t.loc[t.id_equipo == e, "desempate"] = f"{claves[e][0]} pts / {claves[e][1]:+d} entre empatados"
    t = t.set_index("id_equipo").loc[orden].reset_index()
    t.insert(0, "pos", range(1, len(t) + 1))
    if "desempate" not in t:
        t["desempate"] = ""
    t["desempate"] = t["desempate"].fillna("")
    return t


def evolucion_posiciones(id_torneo: int) -> pd.DataFrame:
    """Posicion de cada equipo despues de cada fecha (para el grafico de 'carrera')."""
    out = []
    for f in range(1, 12):
        t = tabla_fiba(id_torneo, hasta_fecha=f)
        if t.empty:
            continue
        out.append(t[["equipo", "pos", "pts"]].assign(fecha=f))
    return pd.concat(out) if out else pd.DataFrame()


def estadisticas_jugadores() -> pd.DataFrame:
    """Una fila por jugador y por partido, con su categoria, equipo y fase."""
    return query("""
        select e.id_partido, e.dni_jugador, j.apellido || ', ' || j.nombre as jugador, j.posicion,
               j.altura_cm, eq.nombre as equipo, ca.nombre as categoria, t.nombre as torneo,
               p.fase, p.fecha, e.minutos, e.libres, e.dobles, e.triples, e.puntos,
               e.rebotes, e.asistencias, e.faltas,
               (e.id_equipo = p.id_equipo_local) as de_local
        from estadistica e
        join jugador j on j.dni_jugador = e.dni_jugador
        join equipo eq on eq.id_equipo = e.id_equipo
        join torneo t on t.id_torneo = e.id_torneo
        join categoria ca on ca.id_categoria = t.id_categoria
        join partido p on p.id_partido = e.id_partido""")
