# Beer Quality – evaluación de lotes por etapa

Aplicación web en Django que evalúa un lote de cerveza con un agente por etapa
del proceso. Cada agente es determinista (reglas), no llama servicios externos.

## Etapas y agentes

| Etapa | Agente | Parámetros |
|---|---|---|
| Granos | grain_agent | humedad, granulometría, actividad enzimática |
| Agua | water_agent | conductividad, pH, arsénico, cloro, carbonatación (por confirmar) |
| Bloque caliente | hot_block_agent | temperatura, tiempo de hervido, densidad, extracto original, pH |
| Bloque frío | cold_block_agent | 14 parámetros (densidad, extractos, alcohol, CO2, O2, amargor, proteína sensible, color, espuma, pH, temperatura, microbiología, conductividad) |
| Envasado | packaging_agent | 21 parámetros (los del bloque frío más SO2, hierro, test de pasteurización, calcio, polifenoles, turbidez, diacetilo y proteínas totales) |
| Logística | logistics_agent | cantidad total de pallets y pallets OK |

La definición completa (claves, unidades, rangos) está en `quality/agents/parameters.py`.
Las ventas ya no forman parte del sistema.

## Cómo decide

- Cada agente revisa solo los parámetros que ingresas; todos son opcionales.
- Se rechazan con error 400 los valores no numéricos, imposibles (por ejemplo pH -50), parámetros o etapas desconocidos y entradas vacías.
- Si un parámetro tiene rango de aceptación, se compara. Hoy tienen rango provisorio 13 de 50 parametros: humedad (3,5 a 5 %), actividad enzimatica (>= 194 grados WK) en granos; arsenico (<= 10 ug/L) en agua; tiempo de hervido (60 a 90 min) y pH (5,0 a 5,5) en bloque caliente; O2 (<= 50 ppb) en bloque frio; y en envasado densidad (1,008 a 1,020), alcohol (4 a 6,5 % v/v), CO2 (2,2 a 2,8 vol.), pH (3,9 a 4,6), O2 (<= 150 ppb), pasteurizacion (15 a 25 UP) y diacetilo (<= 0,03 mg/L). Los de envasado de densidad, alcohol, CO2 y pH vienen del nucleo; los demas de fuentes publicas (BYO, Ashton Lewis, OMS, Hach, Yokogawa, Brewers Association, Fabrico). Hervido 60 a 90 min no tiene fuente verificada. El resto se registra como "sin rango definido" hasta que la cerveceria entregue los rangos.
- Estándares por marca (envasado): si eliges marca y formato (botella, lata o barril), el envasado se evalúa con el estándar y la tolerancia de la planta para esa marca: EO, alcohol (% v/v y % p/p), EA, pH, turbidez, UP, T° salida del pasteurizador, conductividad, CO2 (g/L) y O2 (llenadora, disuelto, pick up y TPO). Dentro de estándar = OK; fuera de estándar pero dentro de tolerancia = observar; fuera de tolerancia = desviación. Los datos se leen de `quality/data/estandares_marca.json`, que está excluido de git porque es un documento interno (otra ruta: variable BRAND_STANDARDS_FILE). Sin ese archivo, la app usa los rangos provisorios genéricos.
- Registro y tendencias: cada análisis se guarda (modelo LotAnalysis, visible en /admin/) con código de lote opcional, mediciones validadas, resultado y usuario. Con al menos 7 lotes previos de un parámetro se analiza su tendencia: media móvil de 3 lotes; alerta si las tres últimas medias suben (o bajan) de forma estricta y la última alcanza el 80 % de la distancia entre el centro histórico (promedio de los valores anteriores a las últimas cinco observaciones) y el límite del estándar. Un valor dentro del estándar con alerta pasa a "tendencia" y la etapa queda en observar. Se usan los últimos 20 lotes previos; en envasado, solo los de la misma marca. Umbral provisional, por calibrar con datos reales. Requiere `python manage.py migrate`.
- Registro JSON: cada análisis genera además un archivo `registros/AAAA-MM-DD/analisis-<id>.json` (otra carpeta: variable ANALYSIS_LOG_DIR; excluida de git) con fecha, usuario, lote, marca, formato, mediciones, resultado y una huella SHA-256 del resultado para verificar que no fue alterado. Se consulta en `/quality/registros/<id>.json` (con `?descargar=1` se descarga) y la lista de los últimos 50 en `/quality/registros/`. En el resultado del análisis aparece el enlace "Ver registro JSON".
- Decisión del especialista: después de cada análisis, un usuario con el permiso "Puede confirmar la decisión final de un lote" (grupo "Especialista de calidad", creado por la migración; los superusuarios lo tienen) registra la decisión final: aprobar, observar o rechazar. Si difiere de la recomendación, el comentario es obligatorio (mínimo 10 caracteres). Se guarda una sola vez con usuario y fecha, no se puede modificar y se agrega al registro JSON ("decision_especialista"). Los demás usuarios ven "Pendiente de confirmación". Para dar el permiso: /admin/ → Usuarios → agregar al grupo "Especialista de calidad".
- Guía de reglas de decisión (/reglas/): los operadores escriben el problema ("presión del filtro sobre 5 bar") o eligen un área (descarga de granos, cocimiento, contaminación química, filtración, llenadora L5, empacadora L1, PPQI L2) y ven la regla que corresponde: nivel (continuar, corregir, escalar o detener), pasos, a quién avisar y documento de origen. La búsqueda es local y determinista (sin servicios externos): ignora tildes y mayúsculas y reconoce sinónimos (O2/oxígeno, CO2/carbonatación, UP/pasteurización). Desde el resultado de un análisis, cada parámetro fuera de estándar enlaza a su regla. Las reglas se leen de `quality/data/reglas_decision.json`, excluido de git por ser documentos internos (otra ruta: variable DECISION_RULES_FILE).
- Logística: tasa = pallets OK / total. Desde 95 % aprueba, desde 85 % observa, bajo 85 % rechaza (umbrales provisorios).
- Por etapa: 0 desviaciones = APROBADO, 1 = OBSERVADO, 2 o más = RECHAZADO. El resultado global es el peor de las etapas evaluadas. Sin ningún rango aplicable responde SIN_EVALUAR.
- El sistema solo recomienda; la decisión final es del especialista.

Las unidades y los rangos son PROVISORIOS: confírmalos con la cervecería.

## Instalación (Windows)

```powershell
cd beer_quality_app
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecutar

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre `http://127.0.0.1:8000/` e inicia sesión. Pulsa "Cargar lote de ejemplo" (valores ilustrativos) y "Analizar lote".

## API

POST /quality/predict/ (requiere sesión y token CSRF). Body: JSON anidado por etapa, por ejemplo:

```json
{"envasado": {"ph": 4.4, "alcohol": 5.2}, "logistica": {"pallets_total": 20, "pallets_ok": 19}}
```

Respuesta: `decision`, `response`, `evaluated_stages`, `parameters_without_range` y `stages` (decisión, desviaciones y parámetros de cada etapa).

## Tests

```bash
python manage.py test
```

## Módulo `quality/ml` (experimental, desconectado)

El clasificador supervisado (bosque aleatorio) ya no interviene en la decisión de la web. Se entrenó con 13 variables que incluían ventas; ahora el esquema tiene 12 y los archivos `model.pkl` y `scaler.pkl` actuales no coinciden. Para volver a usarlo habría que reentrenar (`python -m quality.ml.train_model`) y definir cómo se integra. La evaluación (`python -m quality.ml.evaluate_model`) usa 50.000 filas posteriores a las del entrenamiento.
