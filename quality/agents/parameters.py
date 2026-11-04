"""Parametros medidos por etapa del proceso cervecero.

Cada parametro: clave, etiqueta, unidad, rango valido (para rechazar datos
imposibles) y rango de aceptacion (None = aun no definido).

IMPORTANTE: las unidades y los rangos son PROVISORIOS. Confirmalos con la
cerveceria o con un especialista antes de usarlos para decidir.

Origen de los rangos de aceptacion (ver README para los enlaces):
- pH, densidad, alcohol y CO2 de envasado: nucleo del proyecto (cerveza terminada).
- Humedad del grano 3,5 a 5 %: interseccion de BYO (3,5 a 6 %) y Ashton Lewis (3 a 5 %).
- Actividad enzimatica minima 194 grados WK: malta base > 60 grados Lintner (Ashton Lewis),
  convertido con grados WK = grados Lintner x 3,5 - 16.
- Arsenico maximo 10 ug/L: guia de la OMS.
- pH del hervido 5,0 a 5,5: Brewers Association (pH de la olla).
- Tiempo de hervido 60 a 90 min: practica comun, sin fuente verificada.
- O2 en cerveza brillante/filtracion hasta 50 ppb: Hach y Yokogawa.
- O2 total del envase hasta 150 ppb: Hach (40 a 150 ppb).
- Pasteurizacion 15 a 25 UP: rango habitual de tunel (Fabrico).
- Diacetilo maximo 0,03 mg/L: Brewers Association (la fuente indica 30 sin unidad clara; se asumio ppb).
Los parametros sin fuente (granulometria, cloro, conductividad, etc.) quedan sin rango.
"""


def _p(key, label, unit, valid, accept=None):
    return {"key": key, "label": label, "unit": unit, "valid": valid, "accept": accept}


# Rangos de aceptacion provisorios para cerveza terminada
_PH = (3.9, 4.6)
_DENSIDAD = (1.008, 1.020)
_ALCOHOL = (4.0, 6.5)
_CO2 = (2.2, 2.8)

STAGES = [
    {
        "key": "granos", "label": "Granos", "subtitle": "Materia prima",
        "agent_id": "grain_agent",
        "parameters": [
            _p("humedad", "Humedad", "%", (0, 100), (3.5, 5.0)),
            _p("granulometria", "Granulometría", "% retenido", (0, 100)),
            _p("actividad_enzimatica", "Actividad enzimática", "°WK", (0, 600), (194, 600)),
        ],
    },
    {
        "key": "agua", "label": "Agua", "subtitle": "Insumo de proceso",
        "agent_id": "water_agent",
        "parameters": [
            _p("conductividad", "Conductividad", "µS/cm", (0, 10000)),
            _p("ph", "pH", "", (0, 14)),
            _p("arsenico", "Arsénico", "µg/L", (0, 1000), (0, 10)),
            _p("cloro", "Cloro", "mg/L", (0, 500)),
            _p("carbonatacion", "Carbonatación (por confirmar)", "mg/L", (0, 2000)),
        ],
    },
    {
        "key": "bloque_caliente", "label": "Bloque caliente", "subtitle": "Molienda · Hervido del mosto",
        "agent_id": "hot_block_agent",
        "parameters": [
            _p("temperatura", "Temperatura", "°C", (0, 110)),
            _p("tiempo_hervido", "Tiempo de hervido", "min", (0, 600), (60, 90)),
            _p("densidad", "Densidad", "g/mL", (0.9, 1.2)),
            _p("extracto_original", "Extracto original", "°P", (0, 40)),
            _p("ph", "pH", "", (0, 14), (5.0, 5.5)),
        ],
    },
    {
        "key": "bloque_frio", "label": "Bloque frío", "subtitle": "Fermentación · Filtrado",
        "agent_id": "cold_block_agent",
        "parameters": [
            _p("densidad", "Densidad", "g/mL", (0.9, 1.2)),
            _p("extracto_original", "Extracto original", "°P", (0, 40)),
            _p("extracto_aparente", "Extracto aparente", "°P", (0, 40)),
            _p("alcohol", "Alcohol", "% v/v", (0, 20)),
            _p("co2", "CO₂", "vol.", (0, 10)),
            _p("o2", "O₂", "ppb", (0, 10000), (0, 50)),
            _p("amargor", "Amargor", "IBU", (0, 200)),
            _p("proteina_sensible", "Proteína sensible", "mg/L", (0, 1000)),
            _p("color", "Color", "EBC", (0, 200)),
            _p("espuma", "Espuma", "s", (0, 1000)),
            _p("ph", "pH", "", (0, 14)),
            _p("temperatura", "Temperatura", "°C", (-5, 40)),
            _p("microbiologia", "Microbiología", "UFC/mL", (0, 1_000_000_000)),
            _p("conductividad", "Conductividad", "µS/cm", (0, 10000)),
        ],
    },
    {
        "key": "envasado", "label": "Envasado", "subtitle": "Botella · Barril",
        "agent_id": "packaging_agent",
        "parameters": [
            _p("densidad", "Densidad", "g/mL", (0.9, 1.2), _DENSIDAD),
            _p("extracto_original", "Extracto original", "°P", (0, 40)),
            _p("extracto_aparente", "Extracto aparente", "°P", (0, 40)),
            _p("alcohol", "Alcohol", "% v/v", (0, 20), _ALCOHOL),
            _p("co2", "CO₂", "vol.", (0, 10), _CO2),
            _p("o2", "O₂", "ppb", (0, 10000), (0, 150)),
            _p("amargor", "Amargor", "IBU", (0, 200)),
            _p("proteina_sensible", "Proteína sensible", "mg/L", (0, 1000)),
            _p("color", "Color", "EBC", (0, 200)),
            _p("espuma", "Espuma", "s", (0, 1000)),
            _p("ph", "pH", "", (0, 14), _PH),
            _p("temperatura", "Temperatura", "°C", (-5, 40)),
            _p("conductividad", "Conductividad", "µS/cm", (0, 10000)),
            _p("so2", "SO₂", "mg/L", (0, 100)),
            _p("hierro", "Hierro", "mg/L", (0, 10)),
            _p("test_pasteurizacion", "Test de pasteurización", "UP", (0, 1000), (15, 25)),
            _p("calcio", "Calcio", "mg/L", (0, 1000)),
            _p("polifenoles", "Polifenoles", "mg/L", (0, 1000)),
            _p("turbidez", "Turbidez", "EBC", (0, 1000)),
            _p("diacetilo", "Diacetilo", "mg/L", (0, 10), (0, 0.03)),
            _p("proteinas_totales", "Proteínas totales", "mg/L", (0, 10000)),
        ],
    },
    {
        "key": "logistica", "label": "Logística", "subtitle": "Pallets despachados",
        "agent_id": "logistics_agent",
        "parameters": [
            _p("pallets_total", "Cantidad total de pallets", "pallets", (0, 1_000_000)),
            _p("pallets_ok", "Pallets OK", "pallets", (0, 1_000_000)),
        ],
    },
]

STAGES_BY_KEY = {s["key"]: s for s in STAGES}

# Umbrales provisorios de logistica (proporcion de pallets OK)
LOGISTICS_APPROVE_RATE = 0.95
LOGISTICS_OBSERVE_RATE = 0.85

# Lote de ejemplo con valores ilustrativos (no son datos reales)
EXAMPLE_LOT = {
    "granos": {"humedad": 4.5, "granulometria": 70, "actividad_enzimatica": 250},
    "agua": {"conductividad": 300, "ph": 7.2, "arsenico": 1, "cloro": 0.5, "carbonatacion": 80},
    "bloque_caliente": {"temperatura": 98, "tiempo_hervido": 60, "densidad": 1.048,
                        "extracto_original": 12, "ph": 5.3},
    "bloque_frio": {"densidad": 1.012, "extracto_original": 12, "extracto_aparente": 2.5,
                    "alcohol": 5.2, "co2": 2.5, "o2": 20, "amargor": 20, "proteina_sensible": 40,
                    "color": 8, "espuma": 250, "ph": 4.4, "temperatura": 3, "microbiologia": 0,
                    "conductividad": 2000},
    "envasado": {"densidad": 1.012, "alcohol": 5.2, "co2": 2.5, "ph": 4.4, "o2": 20,
                 "amargor": 20, "color": 8, "temperatura": 3, "test_pasteurizacion": 20,
                 "diacetilo": 0.02},
    "logistica": {"pallets_total": 20, "pallets_ok": 19},
}
