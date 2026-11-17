from django.urls import path
from .views import predict_view, rules_search_view

urlpatterns = [
    path("predict/", predict_view, name="predict"),
    path("reglas/buscar/", rules_search_view, name="rules_search"),
]

