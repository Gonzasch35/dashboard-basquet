"""Lee los .sql del TP y los separa en bloques por su encabezado "-- C1) ...".

Asi el dashboard muestra y corre EXACTAMENTE lo que se entrega: si cambian
el .sql, el dashboard cambia solo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HEADER = re.compile(r"^--\s*([A-Z]+\d+)\)\s*(.*)$")
SEPARADOR = re.compile(r"^--\s*[-=]{5,}")


@dataclass
class Bloque:
    codigo: str          # C1, E2, Q3, A1...
    titulo: str          # primera linea del comentario
    detalle: str         # resto del comentario (lineas que siguen)
    sql: str             # la consulta, sin comentarios de encabezado
    seccion: str = ""    # titulo de la seccion (ENTRENADORES Y EQUIPOS, ...)

    @property
    def usa(self) -> str:
        """Lo que va despues de '-- Usa:' (si esta)."""
        for linea in self.detalle.splitlines():
            if linea.lower().startswith("usa:"):
                return linea[4:].strip()
        return ""


def leer_bloques(path: Path) -> list[Bloque]:
    bloques: list[Bloque] = []
    actual: Bloque | None = None
    en_encabezado = False
    seccion = ""
    lineas = path.read_text(encoding="utf-8").splitlines()
    for i, linea in enumerate(lineas):
        m = HEADER.match(linea)
        # titulos de seccion: "-- ----" / "-- TITULO" / "-- ----"
        if SEPARADOR.match(linea) and i + 2 < len(lineas) and SEPARADOR.match(lineas[i + 2]):
            texto = lineas[i + 1].lstrip("- ").strip()
            if texto and not HEADER.match(lineas[i + 1]):
                seccion = texto
        if m:
            actual = Bloque(m.group(1), m.group(2).strip(), "", "", seccion)
            bloques.append(actual)
            en_encabezado = True
            continue
        if actual is None:
            continue
        if SEPARADOR.match(linea):
            actual = None
            continue
        if en_encabezado and linea.startswith("--"):
            actual.detalle += linea.lstrip("-").strip() + "\n"
            continue
        en_encabezado = False
        actual.sql += linea + "\n"
    for b in bloques:
        # el titulo puede seguir en las lineas de detalle (sin "Usa:")
        cont = [l for l in b.detalle.splitlines() if l and not l.lower().startswith("usa:")]
        if cont and not b.titulo.endswith("."):
            b.titulo = " ".join([b.titulo, *cont])
        b.sql = b.sql.strip().rstrip(";").strip()
    return [b for b in bloques if b.sql]
