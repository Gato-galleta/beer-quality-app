"""Registro JSON de cada analisis de lote.

Cada ejecucion produce un documento JSON con la entrada, el resultado, quien lo ejecuto y
una huella SHA-256 del resultado. Se guarda en la base de datos (LotAnalysis) y ademas como
archivo en ANALYSIS_LOG_DIR/AAAA-MM-DD/analisis-<id>.json.

La huella permite verificar que un registro no fue alterado y que la misma entrada produce
la misma salida: se calcula sobre el resultado sin los datos propios de la ejecucion.
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path

from django.conf import settings

FORMAT_VERSION = 1


def fingerprint(result):
    """SHA-256 del resultado en forma canonica (claves ordenadas, sin espacios)."""
    canonical = json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_document(record):
    return {
        "formato_registro": FORMAT_VERSION,
        "id": record.id,
        "fecha": record.created_at.isoformat(),
        "usuario": record.user.get_username() if record.user else None,
        "lote": record.lot_code,
        "marca": record.brand or None,
        "formato": record.package_format or None,
        "decision": record.decision,
        "huella_resultado": fingerprint(record.result),
        "decision_especialista": specialist_decision(record),
        "mediciones": record.measurements,
        "resultado": record.result,
    }


def specialist_decision(record):
    if not record.final_decision:
        return None
    return {
        "decision": record.final_decision,
        "coincide_con_recomendacion": record.final_decision == record.decision,
        "comentario": record.final_comment,
        "usuario": record.final_by.get_username() if record.final_by else None,
        "fecha": record.final_at.isoformat() if record.final_at else None,
    }


def file_path(record):
    base = Path(settings.ANALYSIS_LOG_DIR)
    return base / f"{record.created_at:%Y-%m-%d}" / f"analisis-{record.id:06d}.json"


def write_file(record):
    """Escribe el registro JSON en disco de forma atomica. Devuelve la ruta."""
    path = file_path(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(build_document(record), ensure_ascii=False, indent=2, sort_keys=False)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return path
