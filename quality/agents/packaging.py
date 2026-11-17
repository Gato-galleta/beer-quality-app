from quality.agents import brand_standards
from quality.agents.base import StageAgent


class PackagingAgent(StageAgent):
    agent_id = "packaging_agent"
    stage_key = "envasado"

    def ranges_for(self, values, context):
        ranges = super().ranges_for(values, context)
        brand = context.get("marca")
        if not brand:
            return ranges

        standards = brand_standards.get_standards()
        brand_std = standards["marcas"][brand]["estandares"]
        fmt = context.get("formato")
        needs_format = [k for k in brand_standards.BY_FORMAT if k in values and k in brand_std]
        if needs_format and not fmt:
            raise ValueError("Envasado: indica el formato (botella, lata o barril) para evaluar CO₂ y O₂")

        source = f"{standards.get('documento') or 'estándar de planta'}"
        for key in brand_standards.COVERED:
            entry = brand_std.get(key)
            if entry and key in brand_standards.BY_FORMAT:
                entry = entry.get(fmt)
            ranges[key] = (
                {"std": tuple(entry["std"]), "tol": tuple(entry["tol"]), "source": source}
                if entry else None
            )
        return ranges

    def _evaluate(self, values, context):
        result = super()._evaluate(values, context)
        brand = context.get("marca")
        if brand and values:
            name = brand_standards.get_standards()["marcas"][brand].get("nombre", brand)
            fmt = brand_standards.FORMATS.get(context.get("formato"), "formato sin indicar")
            result["notes"].insert(0, f"Estándares de {name} · {fmt}")
        elif values:
            result["notes"].insert(0, "Sin marca elegida: se usan rangos provisorios genéricos")
        return result
