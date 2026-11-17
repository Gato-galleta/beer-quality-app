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

// Etapa del analisis -> area de la guia de reglas de decision
const RULE_AREA = { granos: "granos", bloque_caliente: "cocimiento", bloque_frio: "filtracion", envasado: "llenadora" };

const STAGE_TEXT = {
  APROBADO: "dentro de rango",
  OBSERVADO: "requiere revisión",
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
      noteItem.className = note.includes(": tendencia a la ") ? "stage-trend" : "stage-sub";
      noteItem.textContent = note;
      stageList.append(noteItem);
    }
    const outOfRange = (stage.parameters || []).filter((p) => p.status === "fuera_de_estandar" || p.status === "fuera_de_rango");
    if (outOfRange.length && RULE_AREA[stage.stage]) {
      const help = document.createElement("li");
      help.className = "stage-help";
      help.append("¿Qué hacer? ");
      outOfRange.forEach((p, i) => {
        const link = document.createElement("a");
        const query = `${p.label} ${p.status === "fuera_de_rango" ? "fuera de tolerancia" : "fuera de estándar"}`;
        link.href = `/reglas/?area=${RULE_AREA[stage.stage]}&q=${encodeURIComponent(query)}`;
        link.textContent = p.label;
        if (i) help.append(" · ");
        help.append(link);
      });
      stageList.append(help);
    }
  }
  const t = result.tendencias;
  const trendText = t
    ? ` Tendencias: con historial suficiente ${t.evaluados}, con alerta ${t.alertas}${t.sin_historial ? `, aún sin 7 lotes previos ${t.sin_historial}` : ""}.`
    : "";
  const saved = result.registro ? ` Registrado como análisis #${result.registro.id}${result.registro.lote ? ` (lote ${result.registro.lote})` : ""}.` : "";
  stageNote.textContent = `${result.parameters_without_range} parámetros registrados aún no tienen rango de aceptación definido.${trendText}${saved} La decisión final es del especialista.`;
  stageNote.querySelector("a.record-link")?.remove();
  if (result.registro) {
    const link = document.createElement("a");
    link.className = "record-link";
    link.href = result.registro.url;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = "Ver registro JSON";
    stageNote.append(" ", link);
  }
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
  const context = {};
  let lotCode = "";
  let csrfToken = "";
  for (const [name, value] of new FormData(form).entries()) {
    if (name === "csrfmiddlewaretoken") {
      csrfToken = value;
      continue;
    }
    if (value === "") continue; // campo vacio: no se envia
    if (name === "lote") {
      lotCode = value.trim();
      continue;
    }
    if (name === "marca" || name === "formato") {
      // marca y formato solo aplican al envasado
      if (currentStage === "todas" || currentStage === "envasado") context[name] = value;
      continue;
    }
    const [stage, key] = name.split(".");
    if (currentStage !== "todas" && stage !== currentStage) continue; // solo la etapa elegida
    (payload[stage] ||= {})[key] = Number(value);
  }

  const hasMeasurements = Object.keys(payload).length > 0;
  Object.assign(payload, hasMeasurements ? context : {});
  if (hasMeasurements && lotCode) payload.lote = lotCode;
  if (!hasMeasurements) {
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
  document.querySelector("#specialist").hidden = true;

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
    showSpecialist(result);
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

// ---- Decision final del especialista ----------------------------------------
const specialist = document.querySelector("#specialist");
const specialistForm = document.querySelector("#specialist-form");
const specialistMsg = document.querySelector("#specialist-msg");
const specialistComment = document.querySelector("#specialist-comment");
const specialistConfirm = document.querySelector("#specialist-confirm");
const commentRule = document.querySelector("#comment-rule");
const DECISION_VERB = { APROBADO: "Aprobar", OBSERVADO: "Observar", RECHAZADO: "Rechazar" };
let pending = null; // { id, recommendation, choice }

function showSpecialist(result) {
  const record = result.registro;
  specialist.hidden = !record || !(result.decision in DECISION_VERB);
  if (specialist.hidden) return;
  pending = { id: record.id, recommendation: result.decision, choice: result.decision };
  specialistComment.value = "";
  specialistMsg.className = "specialist-msg";
  if (!record.puede_confirmar) {
    specialistForm.hidden = true;
    specialistMsg.textContent = `Pendiente de confirmación por un especialista de calidad (análisis #${record.id}).`;
    return;
  }
  specialistForm.hidden = false;
  specialistMsg.textContent = "";
  chooseDecision(result.decision);
}

function chooseDecision(decision) {
  pending.choice = decision;
  for (const b of specialist.querySelectorAll(".specialist-options button")) {
    b.setAttribute("aria-checked", String(b.dataset.decision === decision));
  }
  const differs = decision !== pending.recommendation;
  commentRule.textContent = differs ? "(obligatorio: difiere de la recomendación)" : "(opcional)";
}

specialist.querySelector(".specialist-options").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-decision]");
  if (button && pending) chooseDecision(button.dataset.decision);
});

specialistConfirm.addEventListener("click", async () => {
  if (!pending) return;
  const comment = specialistComment.value.trim();
  if (pending.choice !== pending.recommendation && comment.length < 10) {
    specialistMsg.className = "specialist-msg is-error";
    specialistMsg.textContent = "Tu decisión difiere de la recomendación: explica el motivo (al menos 10 caracteres).";
    specialistComment.focus();
    return;
  }
  specialistConfirm.disabled = true;
  try {
    const response = await fetch(`/quality/registros/${pending.id}/decision/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": form.elements.csrfmiddlewaretoken.value },
      body: JSON.stringify({ decision: pending.choice, comentario: comment }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || "No se pudo registrar la decisión.");
    const d = body.decision_especialista;
    specialistForm.hidden = true;
    specialistMsg.className = "specialist-msg";
    specialistMsg.replaceChildren(
      "Decisión final: ", Object.assign(document.createElement("strong"), { textContent: DECISION_VERB[d.decision] }),
      ` · ${d.usuario} · ${new Date(d.fecha).toLocaleString("es-CL")}`,
      d.coincide_con_recomendacion ? " · coincide con la recomendación" : " · difiere de la recomendación",
      d.comentario ? `. «${d.comentario}»` : "",
    );
    pending = null;
  } catch (error) {
    specialistMsg.className = "specialist-msg is-error";
    specialistMsg.textContent = error.message;
  } finally {
    specialistConfirm.disabled = false;
  }
});
