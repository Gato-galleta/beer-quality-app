from django.shortcuts import render, redirect
from .models import QualityParameter

def home(request):
    if request.method == "POST":
        name = request.POST.get("name")
        value = request.POST.get("value")
        unit = request.POST.get("unit")

        if name and value and unit:
            QualityParameter.objects.create(
                name=name,
                value=value,
                unit=unit
            )
            return redirect("home")

    parameters = QualityParameter.objects.all()
    return render(request, "quality_app/home.html", {"parameters": parameters})
