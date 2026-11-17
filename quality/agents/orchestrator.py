from quality.agents import brand_standards, trends
from quality.agents.base import StageAgent
from quality.agents.agua import WaterAgent
from quality.agents.cold_block import ColdBlockAgent
from quality.agents.granos import GrainAgent
from quality.agents.hot_block import HotBlockAgent
from quality.agents.logistica import LogisticsAgent
from quality.agents.packaging import PackagingAgent

# Orden del proceso: de la materia prima a la entrega
AGENTS = (
    GrainAgent(), WaterAgent(), HotBlockAgent(), ColdBlockAgent(), PackagingAgent(), LogisticsAgent(),
)

SEVERITY = {"APROBADO": 0, "OBSERVADO": 1, "RECHAZADO": 2}

MESSAGES = {
    "APROBADO": "Las etapas evaluadas están dentro de los rangos definidos.",
    "OBSERVADO": "Hay una desviación, un valor fuera de estándar (dentro de tolerancia) o una tendencia hacia el límite: el lote requiere revisión.",
    "RECHAZADO": "Hay varias desviaciones: se recomienda rechazar el lote. La decisión final es del especialista.",
    "SIN_EVALUAR": "Las mediciones ingresadas no tienen rangos de aceptación definidos, por lo que no se puede emitir una recomendación.",
}


def analyze_quality(input_data, history_for=None):
    """Evalua el lote por etapa. history_for(stage, param, context) entrega los valores previos
    de un parametro para el analisis de tendencias; sin el, no se analizan tendencias."""
    if not isinstance(input_data, dict):
        raise ValueError("Se esperaba un objeto con las etapas y sus mediciones")

    input_data = dict(input_data)
    context = _read_context(input_data.pop("marca", None), input_data.pop("formato", None))

    known = {agent.stage_key for agent in AGENTS}
    unknown = [key for key in input_data if key not in known]
    if unknown:
        raise ValueError(f"Etapa desconocida: {unknown}")

    stages = [agent.analyze(input_data.get(agent.stage_key), context) for agent in AGENTS]
    if not any(stage["measured"] for stage in stages):
        raise ValueError("Ingresa al menos una medición")

    trend_summary = None
    if history_for is not None:
        trend_summary = trends.apply(
            stages, lambda stage, key: history_for(stage, key, context), StageAgent._decision
        )

    evaluated = [s for s in stages if s["decision"] in SEVERITY]
    if evaluated:
        decision = max((s["decision"] for s in evaluated), key=SEVERITY.get)
    else:
        decision = "SIN_EVALUAR"

    return {
        "decision": decision,
        "response": MESSAGES[decision],
        "marca": context.get("marca"),
        "formato": context.get("formato"),
        "evaluated_stages": len(evaluated),
        "parameters_without_range": sum(s["parameters_without_range"] for s in stages),
        "stages": stages,
        "tendencias": trend_summary,
    }


def _read_context(brand, fmt):
    """Valida la marca y el formato del envase (ambos opcionales)."""
    context = {}
    if brand not in (None, ""):
        if not isinstance(brand, str) or brand not in brand_standards.get_standards()["marcas"]:
            raise ValueError(f"Marca desconocida: {brand}")
        context["marca"] = brand
    if fmt not in (None, ""):
        if not isinstance(fmt, str) or fmt not in brand_standards.FORMATS:
            raise ValueError(f"Formato desconocido: {fmt} (usa botella, lata o barril)")
        context["formato"] = fmt
    return context
