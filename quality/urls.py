from django.urls import path
from .views import confirm_view, predict_view, record_list_view, record_view, rules_search_view

urlpatterns = [
    path("predict/", predict_view, name="predict"),
    path("reglas/buscar/", rules_search_view, name="rules_search"),
    path("registros/", record_list_view, name="record_list"),
    path("registros/<int:record_id>.json", record_view, name="record"),
    path("registros/<int:record_id>/decision/", confirm_view, name="confirm"),
]

