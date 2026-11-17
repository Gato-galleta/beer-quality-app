import copy
import os
from pathlib import Path
from unittest import mock
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from quality.agents.parameters import EXAMPLE_LOT, STAGES


class StageAnalysisTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="quality-user", password="test-password-123"
        )
        self.client = Client()
        self.client.force_login(self.user)

    def post(self, payload, client=None):
        return (client or self.client).post(
            "/quality/predict/", data=json.dumps(payload), content_type="application/json"
        )

    # -- paginas -------------------------------------------------------
    def test_dashboard_renders_one_field_per_parameter(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Calidad de")
        for stage in STAGES:
            for p in stage["parameters"]:
                self.assertContains(response, f'name="{stage["key"]}.{p["key"]}"')
        self.assertContains(response, 'name="logistica.pallets_ok"')
        self.assertNotContains(response, "total_sales")
        self.assertNotContains(response, "Ventas")

    def test_dashboard_requires_login(self):
        self.assertRedirects(Client().get("/"), "/login/?next=/")

    def test_login_page_renders_username_and_password_fields(self):
        response = Client().get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_valid_credentials_start_a_session(self):
        client = Client()
        response = client.post("/login/", {"username": "quality-user", "password": "test-password-123"})
        self.assertRedirects(response, "/")
        self.assertEqual(client.get("/").status_code, 200)

    def test_logout_ends_the_session(self):
        response = self.client.post("/logout/")
        self.assertRedirects(response, "/login/")
        self.assertRedirects(self.client.get("/"), "/login/?next=/")

    # -- seguridad -----------------------------------------------------
    def test_anonymous_prediction_is_rejected(self):
        response = self.post({}, client=Client())
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())

    def test_authenticated_prediction_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        token = client.get("/").cookies["csrftoken"].value
        payload = json.dumps(EXAMPLE_LOT)
        rejected = client.post("/quality/predict/", data=payload, content_type="application/json")
        accepted = client.post(
            "/quality/predict/", data=payload, content_type="application/json", HTTP_X_CSRFTOKEN=token
        )
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(accepted.status_code, 200)

    # -- decision ------------------------------------------------------
    def test_example_lot_is_approved_with_six_stages(self):
        response = self.post(EXAMPLE_LOT)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["decision"], "APROBADO")
        self.assertEqual(len(body["stages"]), 6)
        self.assertEqual(
            [s["stage"] for s in body["stages"]],
            ["granos", "agua", "bloque_caliente", "bloque_frio", "envasado", "logistica"],
        )
        self.assertIn("response", body)
        self.assertGreater(body["parameters_without_range"], 0)

    def test_one_deviation_is_observed(self):
        lot = copy.deepcopy(EXAMPLE_LOT)
        lot["envasado"]["ph"] = 5.0
        self.assertEqual(self.post(lot).json()["decision"], "OBSERVADO")

    def test_two_deviations_are_rejected(self):
        lot = copy.deepcopy(EXAMPLE_LOT)
        lot["envasado"]["ph"] = 5.0
        lot["envasado"]["alcohol"] = 9
        self.assertEqual(self.post(lot).json()["decision"], "RECHAZADO")

    def test_logistics_rate_sets_the_decision(self):
        lot = copy.deepcopy(EXAMPLE_LOT)
        lot["logistica"] = {"pallets_total": 20, "pallets_ok": 17}
        self.assertEqual(self.post(lot).json()["decision"], "OBSERVADO")
        lot["logistica"] = {"pallets_total": 20, "pallets_ok": 10}
        self.assertEqual(self.post(lot).json()["decision"], "RECHAZADO")

    def test_new_provisional_ranges_apply(self):
        ok = self.post({"granos": {"humedad": 4.5, "actividad_enzimatica": 250}}).json()
        self.assertEqual(ok["decision"], "APROBADO")
        bad = self.post({"granos": {"humedad": 5.8, "actividad_enzimatica": 150}}).json()
        self.assertEqual(bad["decision"], "RECHAZADO")
        arsenic = self.post({"agua": {"arsenico": 12}}).json()
        self.assertEqual(arsenic["decision"], "OBSERVADO")

    def test_measurements_without_ranges_give_no_recommendation(self):
        body = self.post({"granos": {"granulometria": 70}}).json()
        self.assertEqual(body["decision"], "SIN_EVALUAR")

    # -- validacion ----------------------------------------------------
    def test_empty_payload_is_rejected(self):
        self.assertEqual(self.post({}).status_code, 400)

    def test_out_of_range_value_is_rejected(self):
        response = self.post({"agua": {"ph": -50}})
        self.assertEqual(response.status_code, 400)
        self.assertIn("fuera de rango", response.json()["error"])

    def test_non_numeric_value_is_rejected(self):
        self.assertEqual(self.post({"granos": {"humedad": "abc"}}).status_code, 400)

    def test_unknown_stage_and_parameter_are_rejected(self):
        self.assertEqual(self.post({"fabrica": {}}).status_code, 400)
        self.assertEqual(self.post({"granos": {"ventas": 5}}).status_code, 400)

    def test_sales_is_not_a_parameter_anywhere(self):
        keys = {p["key"] for s in STAGES for p in s["parameters"]}
        self.assertNotIn("total_sales", keys)
        self.assertNotIn("ventas", keys)

    def test_logistics_validation(self):
        for logistics in (
            {"pallets_total": 5, "pallets_ok": 6},   # OK mayor que el total
            {"pallets_total": 5},                    # falta pallets_ok
            {"pallets_total": 0, "pallets_ok": 0},   # total cero
            {"pallets_total": 5.5, "pallets_ok": 2},  # no entero
        ):
            self.assertEqual(self.post({"logistica": logistics}).status_code, 400, logistics)

    def test_invalid_json_is_rejected(self):
        response = self.client.post("/quality/predict/", data="no es json", content_type="application/json")
        self.assertEqual(response.status_code, 400)


FIXTURE = str(Path(__file__).resolve().parent / "fixtures" / "estandares_prueba.json")


@mock.patch.dict(os.environ, {"BRAND_STANDARDS_FILE": FIXTURE})
class BrandStandardsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="brand-user", password="x-123456789")
        self.client.force_login(self.user)

    def post(self, payload):
        return self.client.post("/quality/predict/", data=json.dumps(payload), content_type="application/json")

    def lot(self, **values):
        return {"marca": "PRUEBA", "formato": "lata", "envasado": values}

    def test_dashboard_lists_brands_and_formats(self):
        response = self.client.get("/")
        self.assertContains(response, '<option value="PRUEBA">Marca de prueba</option>')
        self.assertContains(response, 'name="formato"')

    def test_within_standard_is_approved(self):
        body = self.post(self.lot(ph=4.2, alcohol=5.0, co2=5.2, o2=30)).json()
        self.assertEqual(body["decision"], "APROBADO")
        self.assertEqual(body["marca"], "PRUEBA")

    def test_out_of_standard_inside_tolerance_is_observed(self):
        body = self.post(self.lot(ph=4.55)).json()
        self.assertEqual(body["decision"], "OBSERVADO")
        envasado = body["stages"][4]
        self.assertEqual(envasado["out_of_standard"], 1)
        self.assertEqual(envasado["deviations"], 0)
        self.assertEqual(envasado["parameters"][0]["status"], "fuera_de_estandar")

    def test_out_of_tolerance_counts_as_deviation(self):
        self.assertEqual(self.post(self.lot(ph=4.7)).json()["decision"], "OBSERVADO")
        self.assertEqual(self.post(self.lot(ph=4.7, turbidez=1.5)).json()["decision"], "RECHAZADO")

    def test_brand_replaces_generic_ranges_for_covered_parameters(self):
        # Generico de UP es 15-25, pero la marca de prueba no define UP: queda sin rango
        body = self.post(self.lot(test_pasteurizacion=40)).json()
        self.assertEqual(body["decision"], "SIN_EVALUAR")
        # Densidad no la cubre el documento: sigue con el rango provisorio
        self.assertEqual(self.post(self.lot(densidad=1.05)).json()["decision"], "OBSERVADO")

    def test_format_dependent_parameters(self):
        self.assertEqual(self.post(self.lot(co2=5.6)).json()["decision"], "OBSERVADO")
        missing_format = self.post({"marca": "PRUEBA", "envasado": {"co2": 5.2}})
        self.assertEqual(missing_format.status_code, 400)
        # Formato sin estandar para la marca: sin rango
        no_keg = self.post({"marca": "PRUEBA", "formato": "barril", "envasado": {"co2": 5.2}}).json()
        self.assertEqual(no_keg["decision"], "SIN_EVALUAR")

    def test_unknown_brand_or_format_is_rejected(self):
        self.assertEqual(self.post({"marca": "OTRA", "envasado": {"ph": 4.2}}).status_code, 400)
        self.assertEqual(self.post({"formato": "tetra", "envasado": {"ph": 4.2}}).status_code, 400)

    def test_without_brand_generic_ranges_still_apply(self):
        self.assertEqual(self.post({"envasado": {"ph": 4.4}}).json()["decision"], "APROBADO")
