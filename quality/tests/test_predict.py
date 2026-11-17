import copy
import os
from pathlib import Path
from unittest import mock
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
import shutil
import tempfile

# Los registros JSON de las pruebas van a una carpeta temporal, nunca a la carpeta real
_LOG_DIR = tempfile.mkdtemp(prefix="registros-prueba-")
_LOG_OVERRIDE = override_settings(ANALYSIS_LOG_DIR=_LOG_DIR)


def setUpModule():
    _LOG_OVERRIDE.enable()


def tearDownModule():
    _LOG_OVERRIDE.disable()
    shutil.rmtree(_LOG_DIR, ignore_errors=True)

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


RULES_FIXTURE = str(Path(__file__).resolve().parent / "fixtures" / "reglas_prueba.json")


@mock.patch.dict(os.environ, {"DECISION_RULES_FILE": RULES_FIXTURE})
class DecisionRulesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="operador", password="x-123456789")
        self.client.force_login(self.user)

    def search(self, **params):
        return self.client.get("/quality/reglas/buscar/", params)

    def test_rules_page_lists_areas(self):
        response = self.client.get("/reglas/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Área de prueba")
        self.assertContains(response, 'id="ask-input"')
        self.assertContains(response, "sin reglas cargadas")

    def test_rules_require_login(self):
        self.assertRedirects(Client().get("/reglas/"), "/login/?next=/reglas/")
        self.assertEqual(Client().get("/quality/reglas/buscar/", {"q": "presion"}).status_code, 401)

    def test_question_finds_the_matching_rule_first(self):
        body = self.search(q="¿Qué hago si la presión del filtro está sobre 5 bar?").json()
        self.assertEqual(body["resultados"][0]["id"], "prueba-01")
        self.assertEqual(body["resultados"][0]["area_label"], "Área de prueba")
        self.assertEqual(body["resultados"][0]["documento"], "DOC-1")

    def test_synonyms_and_accents(self):
        self.assertEqual(self.search(q="o2 total fuera de tolerancia").json()["resultados"][0]["id"], "prueba-02")
        self.assertEqual(self.search(q="PRESION").json()["resultados"][0]["id"], "prueba-01")

    def test_pick_up_is_not_confused_with_pasteurization_units(self):
        self.assertEqual(self.search(q="UP fuera de tolerancia").json()["resultados"][0]["id"], "otra-02")
        self.assertEqual(self.search(q="pick up zona amarilla").json()["resultados"][0]["id"], "otra-01")

    def test_area_filter_and_browse(self):
        body = self.search(q="fuera de tolerancia", area="otra").json()
        self.assertEqual({r["area"] for r in body["resultados"]}, {"otra"})
        listed = self.search(area="prueba").json()["resultados"]
        self.assertEqual([r["id"] for r in listed], ["prueba-01", "prueba-02"])
        self.assertEqual(self.search(area="nada").status_code, 400)

    def test_unknown_question_returns_nothing(self):
        self.assertEqual(self.search(q="xyzzy").json()["resultados"], [])
        self.assertEqual(self.search(q="").json()["resultados"], [])

    def test_search_is_deterministic(self):
        first = self.search(q="fuera de tolerancia").json()
        for _ in range(5):
            self.assertEqual(self.search(q="fuera de tolerancia").json(), first)

    def test_dashboard_links_to_rules(self):
        self.assertContains(self.client.get("/"), 'href="/reglas/"')


class TrendRuleTests(TestCase):
    """Regla de tendencia de la seccion 9.1: 7 lotes previos, media movil de 3, umbral 80 %."""

    def detect(self, history, value, standard=(3.9, 4.6)):
        from quality.agents.trends import detect
        return detect(history, value, standard)

    def test_needs_seven_previous_lots(self):
        self.assertIsNone(self.detect([4.0] * 6, 4.58))
        self.assertIsNotNone(self.detect([4.0] * 7, 4.58))

    def test_rising_drift_near_upper_limit_alerts(self):
        trend = self.detect([4.0] * 5 + [4.45, 4.5], 4.58)
        self.assertTrue(trend["alert"])
        self.assertEqual(trend["direction"], "alza")
        self.assertEqual(trend["limit"], 4.6)
        self.assertGreaterEqual(trend["progress"], 0.8)

    def test_falling_drift_near_lower_limit_alerts(self):
        trend = self.detect([4.4] * 5 + [4.0, 3.98], 3.95)
        self.assertTrue(trend["alert"])
        self.assertEqual(trend["direction"], "baja")

    def test_drift_far_from_limit_does_not_alert(self):
        trend = self.detect([4.0] * 5 + [4.05, 4.1], 4.15)
        self.assertEqual(trend["direction"], "alza")
        self.assertFalse(trend["alert"])

    def test_stable_or_noisy_series_does_not_alert(self):
        self.assertFalse(self.detect([4.2] * 7, 4.2)["alert"])
        self.assertFalse(self.detect([4.2, 4.4, 4.1, 4.5, 4.2, 4.5, 4.1], 4.55)["alert"])

    def test_no_limit_in_drift_direction_does_not_alert(self):
        trend = self.detect([0.5] * 5 + [0.3, 0.2], 0.1, standard=(None, 0.8))
        self.assertEqual(trend["direction"], "baja")
        self.assertFalse(trend["alert"])


class LotHistoryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="analista", password="x-123456789")
        self.client.force_login(self.user)

    def post(self, payload):
        return self.client.post("/quality/predict/", data=json.dumps(payload), content_type="application/json")

    def test_each_analysis_is_recorded_with_lot_code(self):
        from quality.models import LotAnalysis
        body = self.post({"lote": " L5-001 ", "envasado": {"ph": 4.4}}).json()
        record = LotAnalysis.objects.get()
        self.assertEqual(record.lot_code, "L5-001")
        self.assertEqual(record.measurements, {"envasado": {"ph": 4.4}})
        self.assertEqual(record.decision, "APROBADO")
        self.assertEqual(record.user, self.user)
        self.assertEqual(body["registro"]["id"], record.id)

    def test_invalid_lot_code_is_rejected_and_not_recorded(self):
        from quality.models import LotAnalysis
        self.assertEqual(self.post({"lote": "x" * 61, "envasado": {"ph": 4.4}}).status_code, 400)
        self.assertEqual(self.post({"envasado": {"ph": -1}}).status_code, 400)
        self.assertEqual(LotAnalysis.objects.count(), 0)

    def test_trend_turns_an_in_spec_value_into_observed(self):
        for ph in [4.0] * 5 + [4.45, 4.5]:
            self.assertEqual(self.post({"envasado": {"ph": ph}}).json()["decision"], "APROBADO")
        body = self.post({"envasado": {"ph": 4.58}}).json()
        self.assertEqual(body["decision"], "OBSERVADO")
        envasado = body["stages"][4]
        self.assertEqual(envasado["parameters"][0]["status"], "tendencia")
        self.assertEqual(envasado["trend_alerts"], 1)
        self.assertEqual(body["tendencias"]["alertas"], 1)
        self.assertTrue(any("tendencia a la alza" in n for n in envasado["notes"]))

    def test_without_enough_history_there_is_no_trend(self):
        body = self.post({"envasado": {"ph": 4.58}}).json()
        self.assertEqual(body["decision"], "APROBADO")
        self.assertEqual(body["tendencias"], {"evaluados": 0, "alertas": 0, "sin_historial": 1})


class JsonRecordTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="auditor", password="x-123456789")
        self.client.force_login(self.user)

    def analyze(self, payload):
        return self.client.post("/quality/predict/", data=json.dumps(payload), content_type="application/json").json()

    def test_each_analysis_writes_a_json_file(self):
        from quality import records
        from quality.models import LotAnalysis
        body = self.analyze({"lote": "L-7", "envasado": {"ph": 4.4}})
        self.assertTrue(body["registro"]["archivo_guardado"])
        record = LotAnalysis.objects.get(pk=body["registro"]["id"])
        path = records.file_path(record)
        self.assertTrue(str(path).startswith(_LOG_DIR))
        document = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(document["lote"], "L-7")
        self.assertEqual(document["usuario"], "auditor")
        self.assertEqual(document["mediciones"], {"envasado": {"ph": 4.4}})
        self.assertEqual(document["decision"], "APROBADO")
        self.assertEqual(document["huella_resultado"], body["registro"]["huella"])

    def test_record_endpoint_returns_the_same_document(self):
        body = self.analyze({"envasado": {"ph": 4.4}})
        document = self.client.get(body["registro"]["url"]).json()
        self.assertEqual(document["id"], body["registro"]["id"])
        self.assertEqual(document["huella_resultado"], body["registro"]["huella"])
        download = self.client.get(body["registro"]["url"], {"descargar": 1})
        self.assertIn("attachment", download["Content-Disposition"])
        listed = self.client.get("/quality/registros/").json()["registros"]
        self.assertEqual(listed[0]["id"], body["registro"]["id"])

    def test_same_input_gives_same_fingerprint(self):
        first = self.analyze({"envasado": {"ph": 4.4, "alcohol": 5.0}})["registro"]["huella"]
        second = self.analyze({"envasado": {"ph": 4.4, "alcohol": 5.0}})["registro"]["huella"]
        self.assertEqual(first, second)
        other = self.analyze({"envasado": {"ph": 4.5, "alcohol": 5.0}})["registro"]["huella"]
        self.assertNotEqual(first, other)

    def test_records_require_login_and_existing_id(self):
        self.assertEqual(Client().get("/quality/registros/").status_code, 401)
        self.assertEqual(Client().get("/quality/registros/1.json").status_code, 401)
        self.assertEqual(self.client.get("/quality/registros/999.json").status_code, 404)


class SpecialistDecisionTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Group
        self.specialist = get_user_model().objects.create_user(username="especialista", password="x-123456789")
        self.specialist.groups.add(Group.objects.get(name="Especialista de calidad"))
        self.operator = get_user_model().objects.create_user(username="operador2", password="x-123456789")
        self.client.force_login(self.specialist)

    def analyze(self, payload, client=None):
        client = client or self.client
        return client.post("/quality/predict/", data=json.dumps(payload), content_type="application/json").json()

    def confirm(self, record_id, decision, comment="", client=None):
        client = client or self.client
        return client.post(f"/quality/registros/{record_id}/decision/",
                           data=json.dumps({"decision": decision, "comentario": comment}),
                           content_type="application/json")

    def test_specialist_confirms_and_record_is_updated(self):
        from quality import records
        from quality.models import LotAnalysis
        body = self.analyze({"envasado": {"ph": 4.4}})
        self.assertTrue(body["registro"]["puede_confirmar"])
        response = self.confirm(body["registro"]["id"], "APROBADO")
        self.assertEqual(response.status_code, 200)
        decision = response.json()["decision_especialista"]
        self.assertEqual(decision["usuario"], "especialista")
        self.assertTrue(decision["coincide_con_recomendacion"])
        record = LotAnalysis.objects.get()
        document = json.loads(records.file_path(record).read_text(encoding="utf-8"))
        self.assertEqual(document["decision_especialista"]["decision"], "APROBADO")
        self.assertEqual(self.client.get(body["registro"]["url"]).json()["decision_especialista"]["decision"], "APROBADO")

    def test_different_decision_requires_a_reason(self):
        record_id = self.analyze({"envasado": {"ph": 4.4}})["registro"]["id"]
        self.assertEqual(self.confirm(record_id, "RECHAZADO", "malo").status_code, 400)
        ok = self.confirm(record_id, "RECHAZADO", "Sabor metálico detectado en cata")
        self.assertEqual(ok.status_code, 200)
        self.assertFalse(ok.json()["decision_especialista"]["coincide_con_recomendacion"])

    def test_decision_cannot_be_changed(self):
        record_id = self.analyze({"envasado": {"ph": 4.4}})["registro"]["id"]
        self.assertEqual(self.confirm(record_id, "APROBADO").status_code, 200)
        self.assertEqual(self.confirm(record_id, "OBSERVADO", "cambio de opinión del turno").status_code, 409)

    def test_only_specialists_can_confirm(self):
        operator = Client()
        operator.force_login(self.operator)
        body = self.analyze({"envasado": {"ph": 4.4}}, client=operator)
        self.assertFalse(body["registro"]["puede_confirmar"])
        self.assertEqual(self.confirm(body["registro"]["id"], "APROBADO", client=operator).status_code, 403)
        self.assertEqual(self.confirm(body["registro"]["id"], "APROBADO", client=Client()).status_code, 401)

    def test_invalid_requests(self):
        record_id = self.analyze({"envasado": {"ph": 4.4}})["registro"]["id"]
        self.assertEqual(self.confirm(record_id, "LIBERAR").status_code, 400)
        self.assertEqual(self.confirm(999, "APROBADO").status_code, 404)
        no_range = self.analyze({"granos": {"granulometria": 70}})["registro"]["id"]
        self.assertEqual(self.confirm(no_range, "APROBADO").status_code, 400)
