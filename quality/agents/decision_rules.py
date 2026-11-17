"""Guia de reglas de decision por area, con buscador local.

Las reglas se transcriben de documentos internos de la planta, por eso viven en un JSON
fuera de git (quality/data/reglas_decision.json). Otra ruta: variable DECISION_RULES_FILE.

Formato:
{
  "areas": [{"key", "label", "documento", "revisado", "descripcion", "sin_reglas"?}],
  "reglas": [{"id", "area", "seccion", "control", "condicion",
              "nivel": "continuar|corregir|escalar|detener",
              "acciones": [str], "impacto", "escalar", "palabras", "incompleto"}]
}

La busqueda es determinista: misma pregunta, mismas reglas y en el mismo orden.
"""
import json
import math
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "reglas_decision.json"
EMPTY = {"areas": [], "reglas": []}
LEVELS = ("continuar", "corregir", "escalar", "detener")

# Peso de cada campo de la regla en la busqueda
FIELDS = {"control": 2.5, "condicion": 2.5, "palabras": 2.0, "seccion": 1.5, "area_label": 1.0, "acciones": 0.8}

STOPWORDS = set("""
a al algo alguna algun ante antes como con cual cuales cuando de debo debe deben del desde donde
el ella en entre es esta estan este esto hace hacer hago hay la las le lo los me mi muy no o para
pasa pero por porque puede puedo que quien se segun ser si sin sobre son su sus tengo un una uno
unos y ya regla reglas decision paso pasos tiene tienen
""".split())

# Sinonimos -> termo canonico (se aplica a reglas y preguntas)
SYNONYMS = {
    "o2": "oxigeno", "oxigen": "oxigeno", "tpo": "oxigeno", "od": "oxigeno",
    "co2": "carbonatacion", "carbonat": "carbonatacion", "gas": "carbonatacion",
    "temp": "temperatura", "t°": "temperatura",
    "up": "pasteurizacion", "pasteurizad": "pasteurizacion", "pasteuriz": "pasteurizacion",
    "eo": "extracto", "plato": "extracto", "°p": "extracto",
    "turbio": "turbidez", "turbia": "turbidez",
    "parar": "detener", "parada": "detener", "detencion": "detener", "detengo": "detener",
    "lata": "lata", "latas": "lata", "botellas": "botella",
    "conductivid": "conductividad",
}


def _strip_accents(text):
    text = text.replace("₂", "2").replace("°", " ")
    text = re.sub(r"pick\s*-?\s*up", "pickup", text, flags=re.I)  # no confundir con UP
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _stem(word):
    for suffix in ("aciones", "acion", "amiento", "ados", "adas", "ado", "ada", "idad", "es", "s"):
        if len(word) - len(suffix) >= 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def tokens(text):
    words = re.findall(r"[a-z0-9]+(?:[.,][0-9]+)?", _strip_accents(str(text).lower()))
    out = []
    for w in words:
        if w in STOPWORDS:
            continue
        w = SYNONYMS.get(w, w)
        w = SYNONYMS.get(_stem(w), _stem(w)) if not w[0].isdigit() else w.replace(",", ".")
        out.append(w)
    return out


def _path():
    return Path(os.environ.get("DECISION_RULES_FILE") or DEFAULT_PATH)


@lru_cache(maxsize=4)
def _load(path, mtime):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    areas = {a["key"]: a for a in data.get("areas", [])}
    index = []
    for rule in data.get("reglas", []):
        area = areas.get(rule["area"], {})
        fields = {
            "control": rule.get("control", ""), "condicion": rule.get("condicion", ""),
            "palabras": rule.get("palabras", ""), "seccion": rule.get("seccion", ""),
            "area_label": area.get("label", ""), "acciones": " ".join(rule.get("acciones", [])),
        }
        index.append((rule, {f: set(tokens(v)) for f, v in fields.items()}))
    n = max(len(index), 1)
    df = {}
    for _, f in index:
        for term in set().union(*f.values()):
            df[term] = df.get(term, 0) + 1
    idf = {t: math.log(1 + n / c) for t, c in df.items()}  # termino raro = mas peso
    return {"areas": list(areas.values()), "index": index, "idf": idf}


def _data():
    path = _path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {"areas": [], "index": [], "idf": {}}
    return _load(str(path), mtime)


def areas():
    data = _data()
    counts = {}
    for rule, _ in data["index"]:
        counts[rule["area"]] = counts.get(rule["area"], 0) + 1
    return [dict(a, total=counts.get(a["key"], 0)) for a in data["areas"]]


def _public(rule, areas_by_key, score=None):
    area = areas_by_key.get(rule["area"], {})
    out = dict(rule, area_label=area.get("label", rule["area"]), documento=area.get("documento", ""))
    out.pop("palabras", None)
    if score is not None:
        out["score"] = round(score, 3)
    return out


def search(query="", area=None, limit=8):
    """Devuelve las reglas que mejor responden a la pregunta, de mayor a menor relevancia.

    Sin pregunta, lista todas las reglas del area (o ninguna si tampoco hay area).
    """
    data = _data()
    areas_by_key = {a["key"]: a for a in data["areas"]}
    if area and area not in areas_by_key:
        raise ValueError(f"Área desconocida: {area}")
    pool = [(r, f) for r, f in data["index"] if not area or r["area"] == area]

    terms = list(dict.fromkeys(tokens(query or "")))
    if not terms:
        if not area:
            return []
        return [_public(r, areas_by_key) for r, _ in pool]

    idf = data["idf"]
    scored = []
    for order, (rule, fields) in enumerate(pool):
        score = 0.0
        matched = 0
        for term in terms:
            weight = idf.get(term, 0.0)
            best = 0.0
            for field, words in fields.items():
                if term in words:
                    best = max(best, FIELDS[field])
                elif len(term) >= 4 and any(w.startswith(term) or term.startswith(w) for w in words if len(w) >= 4):
                    best = max(best, FIELDS[field] * 0.5)
            if best:
                matched += 1
                score += weight * best
        if matched:
            # premia las reglas que cubren mas palabras de la pregunta
            score *= (matched / len(terms)) ** 0.5
            scored.append((-score, order, rule, score))
    scored.sort(key=lambda s: (s[0], s[1]))
    return [_public(rule, areas_by_key, score) for _, _, rule, score in scored[:limit]]
