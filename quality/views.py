from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json

from quality.agents.parameters import EXAMPLE_LOT, STAGES


@login_required
def dashboard_view(request):
    return render(request, "quality/dashboard.html", {"stages": STAGES, "example_lot": EXAMPLE_LOT})


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
