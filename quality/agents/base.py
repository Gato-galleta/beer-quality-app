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
    def analyze(self, raw, context=None):
        values = self.clean(raw)
        return self._evaluate(values, context or {})

    def ranges_for(self, values, context):
        """Rango por parametro: {"std": (min, max), "tol": (min, max), "source": str} o None.

        Por defecto usa el rango provisorio generico (estandar = tolerancia).
        """
        ranges = {}
        for spec in self.stage["parameters"]:
            accept = spec["accept"]
            ranges[spec["key"]] = (
                {"std": accept, "tol": accept, "source": "provisorio"} if accept else None
            )
        return ranges

    @staticmethod
    def _within(value, bounds):
        low, high = bounds
        return (low is None or value >= low) and (high is None or value <= high)

    @staticmethod
    def _fmt(bounds):
        low, high = bounds
        if low is None:
            return f"≤ {high:g}"
        if high is None:
            return f"≥ {low:g}"
        return f"{low:g} a {high:g}"

    def _evaluate(self, values, context):
        ranges = self.ranges_for(values, context)
        parameters, notes = [], []
        deviations = warnings = evaluated = 0
        for spec in self.stage["parameters"]:
            if spec["key"] not in values:
                continue
            value = values[spec["key"]]
            rng = ranges.get(spec["key"])
            name = f"{spec['label']}" + (f" ({spec['unit']})" if spec["unit"] else "")
            if rng is None:
                status = "sin_rango"
            else:
                evaluated += 1
                if self._within(value, rng["std"]):
                    status = "ok"
                elif self._within(value, rng["tol"]):
                    status = "fuera_de_estandar"
                    warnings += 1
                    notes.append(f"{name} {value:g}: fuera de estándar ({self._fmt(rng['std'])}), "
                                 f"dentro de tolerancia ({self._fmt(rng['tol'])})")
                else:
                    status = "fuera_de_rango"
                    deviations += 1
                    limit = "tolerancia" if rng["tol"] != rng["std"] else "rango"
                    notes.append(f"{name} {value:g}: fuera de {limit} ({self._fmt(rng['tol'])})")
            parameters.append({
                "key": spec["key"], "label": spec["label"], "unit": spec["unit"],
                "value": value, "status": status,
                "accept": list(rng["std"]) if rng else None,
                "tolerance": list(rng["tol"]) if rng else None,
                "source": rng["source"] if rng else None,
            })
        return self._result(values, parameters, deviations, evaluated, notes, warnings)

    @staticmethod
    def _decision(deviations, evaluated, has_values, warnings=0):
        if evaluated == 0:
            return "SIN_RANGOS" if has_values else "SIN_DATOS"
        if deviations == 0:
            return "OBSERVADO" if warnings else "APROBADO"
        return "OBSERVADO" if deviations == 1 else "RECHAZADO"

    def _result(self, values, parameters, deviations, evaluated, notes=(), warnings=0):
        return {
            "agent": self.agent_id,
            "stage": self.stage_key,
            "label": self.stage["label"],
            "decision": self._decision(deviations, evaluated, bool(values), warnings),
            "deviations": deviations,
            "out_of_standard": warnings,
            "measured": len(values),
            "total_parameters": len(self.stage["parameters"]),
            "parameters_without_range": sum(1 for p in parameters if p["status"] == "sin_rango"),
            "parameters": parameters,
            "notes": list(notes),
        }
