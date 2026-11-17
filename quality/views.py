from django.http import JsonResponse
from django.shortcuts import render
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json

from quality.agents import decision_rules
from quality.agents.brand_standards import FORMATS, brand_choices
from quality.agents.parameters import EXAMPLE_LOT, STAGES
from quality import records
from quality.models import LotAnalysis


@login_required
def dashboard_view(request):
    return render(request, "quality/dashboard.html", {
        "stages": STAGES, "example_lot": EXAMPLE_LOT,
        "brands": brand_choices(), "formats": FORMATS.items(),
    })


@login_required
def rules_view(request):
    return render(request, "quality/reglas.html", {
        "areas": decision_rules.areas(),
        "query": request.GET.get("q", "")[:200],
        "area": request.GET.get("area", ""),
    })


def rules_search_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Inicia sesión para consultar las reglas."}, status=401)
    query = request.GET.get("q", "")[:200]
    area = request.GET.get("area") or None
    try:
        results = decision_rules.search(query, area=area, limit=200 if area and not query.strip() else 8)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse({"query": query, "area": area, "resultados": results})


CONFIRM_PERMISSION = "quality.confirm_lotanalysis"
FINAL_DECISIONS = ("APROBADO", "OBSERVADO", "RECHAZADO")


# Lotes previos que se consideran para la tendencia de cada parametro
HISTORY_LIMIT = 20


def _history_provider():
    """Carga una vez los analisis guardados y entrega, por parametro, los valores previos
    en orden cronologico. En envasado solo cuenta el historial de la misma marca."""
    records = list(
        LotAnalysis.objects.order_by("-created_at", "-id").values_list("brand", "measurements")[:1000]
    )
    records.reverse()

    def history_for(stage, key, context):
        brand = context.get("marca") or ""
        values = [
            m[stage][key] for b, m in records
            if isinstance(m.get(stage), dict) and key in m[stage] and (stage != "envasado" or b == brand)
        ]
        return values[-HISTORY_LIMIT:]

    return history_for


@require_POST
def predict_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Inicia sesión para analizar un lote."}, status=401)

    try:
        from quality.agents.orchestrator import analyze_quality

        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError("Se esperaba un objeto con las etapas y sus mediciones")
        lot_code = data.pop("lote", "") or ""
        if not isinstance(lot_code, str) or len(lot_code.strip()) > 60:
            raise ValueError("El código de lote debe ser un texto de hasta 60 caracteres")
        lot_code = lot_code.strip()

        result = analyze_quality(data, history_for=_history_provider())

        measurements = {
            stage["stage"]: {p["key"]: p["value"] for p in stage["parameters"]}
            for stage in result["stages"] if stage["parameters"]
        }
        record = LotAnalysis.objects.create(
            user=request.user, lot_code=lot_code, brand=result["marca"] or "",
            package_format=result["formato"] or "", measurements=measurements,
            result=result, decision=result["decision"],
        )
        try:
            saved_file = records.write_file(record) is not None
        except OSError:
            saved_file = False
        response = dict(result)
        response["registro"] = {
            "id": record.id, "lote": lot_code, "fecha": record.created_at.isoformat(),
            "huella": records.fingerprint(record.result), "archivo_guardado": saved_file,
            "url": f"/quality/registros/{record.id}.json",
            "puede_confirmar": request.user.has_perm(CONFIRM_PERMISSION),
        }
        return JsonResponse(response, status=200)

    except (ValueError, TypeError) as error:
        # json.JSONDecodeError es un ValueError
        return JsonResponse({"error": str(error)}, status=400)
    except Exception:
        return JsonResponse({"error": "Internal server error"}, status=500)


def record_view(request, record_id):
    """Registro JSON de un analisis (se descarga con ?descargar=1)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Inicia sesión para ver los registros."}, status=401)
    record = LotAnalysis.objects.filter(pk=record_id).select_related("user").first()
    if record is None:
        return JsonResponse({"error": "Registro no encontrado."}, status=404)
    response = JsonResponse(records.build_document(record), json_dumps_params={"ensure_ascii": False, "indent": 2})
    if request.GET.get("descargar"):
        response["Content-Disposition"] = f'attachment; filename="analisis-{record.id:06d}.json"'
    return response


def record_list_view(request):
    """Ultimos registros (resumen) en JSON."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Inicia sesión para ver los registros."}, status=401)
    latest = LotAnalysis.objects.order_by("-created_at", "-id")[:50]
    return JsonResponse({"registros": [
        {"id": r.id, "fecha": r.created_at.isoformat(), "lote": r.lot_code, "marca": r.brand or None,
         "decision": r.decision, "decision_especialista": r.final_decision or None,
         "url": f"/quality/registros/{r.id}.json"}
        for r in latest
    ]}, json_dumps_params={"ensure_ascii": False, "indent": 2})


@require_POST
def confirm_view(request, record_id):
    """El especialista registra la decision final del lote (una sola vez)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Inicia sesión para confirmar."}, status=401)
    if not request.user.has_perm(CONFIRM_PERMISSION):
        return JsonResponse({"error": "Solo un especialista de calidad puede confirmar la decisión final."}, status=403)
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError
    except ValueError:
        return JsonResponse({"error": "Solicitud no válida."}, status=400)

    decision = data.get("decision")
    comment = data.get("comentario") or ""
    if decision not in FINAL_DECISIONS:
        return JsonResponse({"error": "Elige aprobar, observar o rechazar."}, status=400)
    if not isinstance(comment, str) or len(comment) > 500:
        return JsonResponse({"error": "El comentario debe ser un texto de hasta 500 caracteres."}, status=400)
    comment = comment.strip()

    with transaction.atomic():
        record = LotAnalysis.objects.select_for_update().filter(pk=record_id).first()
        if record is None:
            return JsonResponse({"error": "Registro no encontrado."}, status=404)
        if record.final_decision:
            return JsonResponse({"error": "Este lote ya tiene una decisión final registrada."}, status=409)
        if record.decision not in FINAL_DECISIONS:
            return JsonResponse({"error": "Este análisis no tiene una recomendación que confirmar."}, status=400)
        if decision != record.decision and len(comment) < 10:
            return JsonResponse(
                {"error": "Tu decisión difiere de la recomendación: explica el motivo (al menos 10 caracteres)."},
                status=400,
            )
        record.final_decision = decision
        record.final_comment = comment
        record.final_by = request.user
        record.final_at = timezone.now()
        record.save(update_fields=["final_decision", "final_comment", "final_by", "final_at"])

    try:
        records.write_file(record)
    except OSError:
        pass
    return JsonResponse({"decision_especialista": records.specialist_decision(record)})
