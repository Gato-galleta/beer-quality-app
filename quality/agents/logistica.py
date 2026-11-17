from quality.agents.base import StageAgent
from quality.agents.parameters import LOGISTICS_APPROVE_RATE, LOGISTICS_OBSERVE_RATE


class LogisticsAgent(StageAgent):
    agent_id = "logistics_agent"
    stage_key = "logistica"

    def _evaluate(self, values, context):
        parameters = [
            {"key": s["key"], "label": s["label"], "unit": s["unit"], "value": values[s["key"]],
             "status": "sin_rango", "accept": None, "tolerance": None, "source": None}
            for s in self.stage["parameters"] if s["key"] in values
        ]
        if not values:
            return self._result(values, parameters, 0, 0)

        if "pallets_total" not in values or "pallets_ok" not in values:
            raise ValueError("Logística: ingresa la cantidad total de pallets y los pallets OK juntos")
        total, ok = values["pallets_total"], values["pallets_ok"]
        if total != int(total) or ok != int(ok):
            raise ValueError("Logística: los pallets deben ser números enteros")
        if total <= 0:
            raise ValueError("Logística: la cantidad total de pallets debe ser mayor que 0")
        if ok > total:
            raise ValueError("Logística: los pallets OK no pueden superar el total de pallets")

        rate = ok / total
        if rate >= LOGISTICS_APPROVE_RATE:
            deviations = 0
        elif rate >= LOGISTICS_OBSERVE_RATE:
            deviations = 1
        else:
            deviations = 2
        for p in parameters:
            p["status"] = "ok" if deviations == 0 else "fuera_de_rango"
        notes = [
            f"Pallets OK: {rate:.1%} (aprobado desde {LOGISTICS_APPROVE_RATE:.0%}, "
            f"observado desde {LOGISTICS_OBSERVE_RATE:.0%}; umbrales provisorios)"
        ]
        result = self._result(values, parameters, deviations, 1, notes)
        result["pallets_ok_rate"] = round(rate, 4)
        return result
