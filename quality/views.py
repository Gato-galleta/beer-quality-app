from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json

from quality.agents import decision_rules
from quality.agents.brand_standards import FORMATS, brand_choices
from quality.agents.parameters import EXAMPLE_LOT, STAGES


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


@require_POST
def predict_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Inicia sesión para analizar un lote."}, status=401)

    try:
        from quality.agents.orchestrator import analyze_quality

        data = json.loads(request.body)
        result = analyze_quality(data)

        return JsonResponse(result, status=200)

    except (ValueError, TypeError) as error:
        # json.JSONDecodeError es un ValueError
        return JsonResponse({"error": str(error)}, status=400)
    except Exception:
        return JsonResponse({"error": "Internal server error"}, status=500)
