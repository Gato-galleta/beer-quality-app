const form = document.querySelector("#quality-form");
const submitButton = document.querySelector("#submit-button");
const buttonLabel = document.querySelector(".button-label");
const errorBox = document.querySelector("#form-error");
const resultPanel = document.querySelector(".result-panel");
const resultState = document.querySelector("#result-state");
const resultTitle = document.querySelector("#result-title");
const resultDescription = document.querySelector("#result-description");
const stageSummary = document.querySelector("#stage-summary");
const stageList = document.querySelector("#stage-list");
const stageNote = document.querySelector("#stage-note");

const menu = document.querySelector("#stage-menu");
const menuHint = document.querySelector("#menu-hint");
const groups = [...document.querySelectorAll(".process-group")];
let currentStage = "todas";

function selectStage(stage) {
  currentStage = stage;
  for (const tab of menu.querySelectorAll(".stage-tab")) {
    const active = tab.dataset.stage === stage;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-pressed", String(active));
  }
  for (const group of groups) group.hidden = stage !== "todas" && group.dataset.stage !== stage;
  const label = menu.querySelector(`[data-stage="${stage}"]`).textContent.replace(/^\d+/, "");
  menuHint.textContent = stage === "todas"
    ? "Mostrando todas las etapas. Elige una para analizarla por separado."
    : `Solo se analizará la etapa: ${label}.`;
  buttonLabel.textContent = stage === "todas" ? "Analizar lote" : "Analizar esta etapa";
  errorBox.hidden = true;
}

menu.addEventListener("click", (event) => {
  const tab = event.target.closest(".stage-tab");
  if (tab) selectStage(tab.dataset.stage);
});

const exampleLot = JSON.parse(document.querySelector("#example-lot").textContent);

const DECISIONS = {
  APROBADO: { state: "good", label: "RECOMENDACIÓN: APROBAR", title: "Lote dentro de los rangos." },
  OBSERVADO: { state: "review", label: "RECOMENDACIÓN: OBSERVAR", title: "Lote requiere revisión." },
  RECHAZADO: { state: "error", label: "RECOMENDACIÓN: RECHAZAR", title: "Lote con varias desviaciones." },
  SIN_EVALUAR: { state: "uncertain", label: "SIN RECOMENDACIÓN", title: "Faltan rangos para evaluar." },
};

const STAGE_TEXT = {
  APROBADO: "dentro de rango",
  OBSERVADO: "1 desviación",
  RECHAZADO: "varias desviaciones",
  SIN_RANGOS: "registrado, sin rangos definidos",
  SIN_DATOS: "sin datos",
};

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function renderResult(result) {
  const info = DECISIONS[result.decision] || DECISIONS.SIN_EVALUAR;
  resultPanel.dataset.state = info.state;
  resultState.textContent = info.label;
  resultTitle.textContent = info.title;
  resultDescription.textContent = result.response || "El análisis del lote ha finalizado.";

  stageList.replaceChildren();
  for (const stage of result.stages) {
    const item = document.createElement("li");
    item.dataset.decision = stage.decision;
    const name = document.createElement("span");
    name.textContent = stage.label;
    const status = document.createElement("strong");
    status.textContent = STAGE_TEXT[stage.decision] || stage.decision;
    item.append(name, status);
    stageList.append(item);
    for (const note of stage.notes || []) {
      const noteItem = document.createElement("li");
      noteItem.className = "stage-sub";
      noteItem.textContent = note;
      stageList.append(noteItem);
    }
  }
  stageNote.textContent = `${result.parameters_without_range} parámetros registrados aún no tienen rango de aceptación definido. La decisión final es del especialista.`;
  stageSummary.hidden = false;
}

document.querySelector("#example-button").addEventListener("click", () => {
  form.reset();
  for (const [stage, params] of Object.entries(exampleLot)) {
    for (const [key, value] of Object.entries(params)) {
      const input = form.elements.namedItem(`${stage}.${key}`);
      if (input) input.value = value;
    }
  }
  errorBox.hidden = true;
});

form.addEventListener("input", () => {
  errorBox.hidden = true;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.hidden = true;

  if (!form.reportValidity()) return;

  const payload = {};
  let csrfToken = "";
  for (const [name, value] of new FormData(form).entries()) {
    if (name === "csrfmiddlewaretoken") {
      csrfToken = value;
      continue;
    }
    if (value === "") continue; // campo vacio: no se envia
    const [stage, key] = name.split(".");
    if (currentStage !== "todas" && stage !== currentStage) continue; // solo la etapa elegida
    (payload[stage] ||= {})[key] = Number(value);
  }

  if (Object.keys(payload).length === 0) {
    showError(currentStage === "todas" ? "Ingresa al menos una medición." : "Ingresa al menos una medición de esta etapa.");
    return;
  }

  submitButton.disabled = true;
  buttonLabel.textContent = "Analizando…";
  resultState.textContent = "PROCESANDO LOTE";
  resultTitle.textContent = "Analizando mediciones.";
  resultDescription.textContent = "Los agentes de cada etapa están evaluando los datos del lote.";
  resultPanel.dataset.state = "loading";
  stageSummary.hidden = true;

  try {
    const response = await fetch("/quality/predict/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify(payload),
    });
    const result = await response.json();

    if (!response.ok) throw new Error(result.error || "No se pudo analizar el lote.");
    renderResult(result);
  } catch (error) {
    resultPanel.dataset.state = "error";
    resultState.textContent = "ANÁLISIS INTERRUMPIDO";
    resultTitle.textContent = "No se pudo completar.";
    resultDescription.textContent = "Revisa los datos o confirma que el servidor local sigue activo.";
    showError(error.message || "Error de conexión con el servidor local.");
  } finally {
    submitButton.disabled = false;
    buttonLabel.textContent = currentStage === "todas" ? "Analizar lote" : "Analizar esta etapa";
  }
});
