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
    "OBSERVADO": "Hay una desviación en alguna etapa: el lote requiere revisión.",
    "RECHAZADO": "Hay varias desviaciones: se recomienda rechazar el lote. La decisión final es del especialista.",
    "SIN_EVALUAR": "Las mediciones ingresadas no tienen rangos de aceptación definidos, por lo que no se puede emitir una recomendación.",
}


def analyze_quality(input_data):
    if not isinstance(input_data, dict):
        raise ValueError("Se esperaba un objeto con las etapas y sus mediciones")

    known = {agent.stage_key for agent in AGENTS}
    unknown = [key for key in input_data if key not in known]
    if unknown:
        raise ValueError(f"Etapa desconocida: {unknown}")

    stages = [agent.analyze(input_data.get(agent.stage_key)) for agent in AGENTS]
    if not any(stage["measured"] for stage in stages):
        raise ValueError("Ingresa al menos una medición")

    evaluated = [s for s in stages if s["decision"] in SEVERITY]
    if evaluated:
        decision = max((s["decision"] for s in evaluated), key=SEVERITY.get)
    else:
        decision = "SIN_EVALUAR"

    return {
        "decision": decision,
        "response": MESSAGES[decision],
        "evaluated_stages": len(evaluated),
        "parameters_without_range": sum(s["parameters_without_range"] for s in stages),
        "stages": stages,
    }
