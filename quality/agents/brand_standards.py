"""Estandares de envasado por marca y formato.

Los datos vienen de un documento interno de la planta, por eso viven en un archivo JSON
fuera de git (quality/data/estandares_marca.json). Se puede indicar otra ruta con la
variable de entorno BRAND_STANDARDS_FILE. Si el archivo no existe, la app funciona con
los rangos provisorios genericos y no ofrece marcas.

Formato del archivo:
{
  "documento": "...", "revisado": "AAAA-MM-DD",
  "marcas": {
    "CODIGO": {
      "nombre": "Nombre visible",
      "estandares": {
        "<parametro>": {"std": [min, max], "tol": [min, max]},          # null = sin limite
        "<parametro por formato>": {"botella": {...}, "lata": {...}, "barril": {...}}
      }
    }
  }
}
"""
import json
import os
from functools import lru_cache
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "estandares_marca.json"

FORMATS = {"botella": "Botella", "lata": "Lata", "barril": "Barril"}

# Parametros de envasado que cubre el documento de la planta. Si hay marca elegida, estos
# se evaluan SOLO con el estandar de la marca (sin dato en el documento = sin rango).
COVERED = {
    "extracto_original", "alcohol", "alcohol_pp", "extracto_aparente", "ph", "turbidez",
    "test_pasteurizacion", "t_salida_pasteurizador", "conductividad", "co2", "o2",
    "o2_entrada_llenadora", "o2_disuelto", "o2_pickup_disuelto", "o2_pickup_total",
}
# Parametros cuyo estandar depende del formato del envase
BY_FORMAT = {"co2", "o2", "o2_pickup_total"}

EMPTY = {"documento": "", "revisado": "", "marcas": {}}


def _path():
    return Path(os.environ.get("BRAND_STANDARDS_FILE") or DEFAULT_PATH)


@lru_cache(maxsize=4)
def _load(path, mtime):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    data.setdefault("marcas", {})
    return data


def get_standards():
    path = _path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return EMPTY
    return _load(str(path), mtime)


def brand_choices():
    """Lista [(codigo, nombre)] para el selector de la web."""
    return [(code, b.get("nombre", code)) for code, b in get_standards()["marcas"].items()]
