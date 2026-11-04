import math

from quality.agents.parameters import STAGES_BY_KEY


class StageAgent:
    """Agente deterministico de una etapa del proceso."""

    agent_id = ""
    stage_key = ""

    def __init__(self):
        self.stage = STAGES_BY_KEY[self.stage_key]
        self.specs = {p["key"]: p for p in self.stage["parameters"]}

    # -- validacion -------------------------------------------------------
    def clean(self, raw):
        """Convierte a numeros y rechaza desconocidos, no numericos o fuera de rango."""
        if raw in (None, {}):
            return {}
        if not isinstance(raw, dict):
            raise ValueError(f"'{self.stage_key}' debe ser un objeto con parametros")
        values = {}
        for key, value in raw.items():
            spec = self.specs.get(key)
            if spec is None:
                raise ValueError(f"Parámetro desconocido en {self.stage['label']}: '{key}'")
            if value is None or value == "":
                continue
            if isinstance(value, bool):
                raise ValueError(f"{self.stage['label']} · {spec['label']}: valor no numérico")
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"{self.stage['label']} · {spec['label']}: valor no numérico")
            if not math.isfinite(number):
                raise ValueError(f"{self.stage['label']} · {spec['label']}: valor no válido")
            low, high = spec["valid"]
            if not low <= number <= high:
                raise ValueError(
                    f"{self.stage['label']} · {spec['label']} fuera de rango ({low} a {high}): {number:g}"
                )
            values[key] = number
        return values

    # -- evaluacion -------------------------------------------------------
    def analyze(self, raw):
        values = self.clean(raw)
        return self._evaluate(values)

    def _evaluate(self, values):
        parameters = []
        deviations = 0
        evaluated = 0
        for spec in self.stage["parameters"]:
            if spec["key"] not in values:
                continue
            value = values[spec["key"]]
            accept = spec["accept"]
            if accept is None:
                status = "sin_rango"
            else:
                evaluated += 1
                if accept[0] <= value <= accept[1]:
                    status = "ok"
                else:
                    status = "fuera_de_rango"
                    deviations += 1
            parameters.append({
                "key": spec["key"], "label": spec["label"], "unit": spec["unit"],
                "value": value, "status": status,
                "accept": list(accept) if accept else None,
            })
        return self._result(values, parameters, deviations, evaluated)

    @staticmethod
    def _decision(deviations, evaluated, has_values):
        if evaluated == 0:
            return "SIN_RANGOS" if has_values else "SIN_DATOS"
        if deviations == 0:
            return "APROBADO"
        return "OBSERVADO" if deviations == 1 else "RECHAZADO"

    def _result(self, values, parameters, deviations, evaluated, notes=()):
        return {
            "agent": self.agent_id,
            "stage": self.stage_key,
            "label": self.stage["label"],
            "decision": self._decision(deviations, evaluated, bool(values)),
            "deviations": deviations,
            "measured": len(values),
            "total_parameters": len(self.stage["parameters"]),
            "parameters_without_range": sum(1 for p in parameters if p["status"] == "sin_rango"),
            "parameters": parameters,
            "notes": list(notes),
        }
