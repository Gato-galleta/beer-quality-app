"""Analisis estadistico del historial: detecta derivas sostenidas hacia el limite del estandar.

Regla (seccion 9.1 del informe):
- Se exige un historial minimo de 7 lotes previos del parametro.
- Sobre la serie historica mas el lote evaluado se calcula la media movil de 3 lotes.
- Hay alerta cuando las ultimas tres medias moviles crecen (o decrecen) de forma
  estrictamente monotona y la ultima alcanza al menos el 80 % de la distancia entre el
  centro historico (promedio de los valores anteriores a las ultimas cinco observaciones)
  y el limite del estandar en el sentido de la deriva.
- Un parametro dentro del estandar con alerta pasa a "tendencia" (la etapa queda en observar).

Es determinista: la misma serie produce siempre el mismo resultado. Umbral provisional.
"""
MIN_HISTORY = 7
WINDOW = 3
THRESHOLD = 0.8


def moving_averages(series, window=WINDOW):
    return [sum(series[i - window + 1:i + 1]) / window for i in range(window - 1, len(series))]


def detect(history, value, standard):
    """history: valores previos en orden cronologico; standard: (min, max) con None = sin limite.

    Devuelve None si no hay historial suficiente, o un dict con el diagnostico.
    """
    if len(history) < MIN_HISTORY:
        return None
    series = list(history) + [value]
    ma = moving_averages(series)
    last3 = ma[-3:]
    rising = last3[0] < last3[1] < last3[2]
    falling = last3[0] > last3[1] > last3[2]
    center = sum(series[:-5]) / len(series[:-5])
    info = {"alert": False, "direction": None, "moving_average": round(ma[-1], 6),
            "center": round(center, 6), "limit": None, "progress": None, "history": len(history)}
    if not (rising or falling):
        return info
    low, high = standard
    limit = high if rising else low
    info["direction"] = "alza" if rising else "baja"
    if limit is None:
        return info
    distance = (limit - center) if rising else (center - limit)
    if distance <= 0:
        return info
    progress = ((ma[-1] - center) if rising else (center - ma[-1])) / distance
    info.update(limit=limit, progress=round(progress, 4), alert=progress >= THRESHOLD)
    return info


def apply(stages, history_for, decide):
    """Agrega el analisis de tendencias a los resultados por etapa (in place).

    history_for(stage_key, param_key) -> lista de valores previos (cronologica).
    decide(deviations, evaluated, has_values, warnings) -> decision de la etapa.
    Devuelve un resumen {"evaluados", "alertas", "sin_historial"}.
    """
    summary = {"evaluados": 0, "alertas": 0, "sin_historial": 0}
    for stage in stages:
        alerts = 0
        for p in stage["parameters"]:
            if not p.get("accept"):
                continue
            trend = detect(history_for(stage["stage"], p["key"]), p["value"], tuple(p["accept"]))
            if trend is None:
                summary["sin_historial"] += 1
                continue
            summary["evaluados"] += 1
            p["trend"] = trend
            if not trend["alert"]:
                continue
            summary["alertas"] += 1
            name = p["label"] + (f" ({p['unit']})" if p["unit"] else "")
            text = (f"{name}: tendencia a la {trend['direction']}, media móvil {trend['moving_average']:g} "
                    f"en el {trend['progress']:.0%} del camino al límite {trend['limit']:g}")
            if p["status"] == "ok":
                p["status"] = "tendencia"
                alerts += 1
                stage["notes"].append(text + " (observar)")
            else:
                stage["notes"].append(text)
        if alerts:
            stage["trend_alerts"] = alerts
            stage["decision"] = decide(stage["deviations"], 1, True, stage["out_of_standard"] + alerts)
    return summary
