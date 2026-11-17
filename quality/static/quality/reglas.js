const form = document.querySelector("#ask-form");
const input = document.querySelector("#ask-input");
const thread = document.querySelector("#thread");
const chips = document.querySelector("#area-chips");
const areas = JSON.parse(document.querySelector("#areas-data").textContent);
const areaByKey = Object.fromEntries(areas.map((a) => [a.key, a]));

const LEVEL_TEXT = { continuar: "Continuar", corregir: "Corregir", escalar: "Escalar", detener: "Detener" };
let currentArea = new URLSearchParams(location.search).get("area") || "";

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "dataset") Object.assign(node.dataset, v);
    else node.setAttribute(k, v);
  }
  for (const child of children) if (child !== null && child !== undefined && child !== "") node.append(child);
  return node;
}

function setArea(key) {
  currentArea = key;
  for (const chip of chips.querySelectorAll(".stage-tab")) {
    const active = chip.dataset.area === key;
    chip.classList.toggle("is-active", active);
    chip.setAttribute("aria-pressed", String(active));
  }
}

function ruleCard(rule, { open = false, main = false } = {}) {
  const card = el("details", { class: `rule-card${main ? " is-main" : ""}`, dataset: { level: rule.nivel } });
  if (open) card.open = true;
  const summary = el("summary", {},
    el("span", { class: "level", dataset: { level: rule.nivel } }, LEVEL_TEXT[rule.nivel] || rule.nivel),
    el("span", { class: "rule-title" },
      el("strong", {}, rule.control),
      el("span", {}, rule.condicion)),
    el("span", { class: "rule-area" }, rule.area_label));
  const steps = el("ol", { class: "steps" }, ...rule.acciones.map((a) => el("li", {}, a)));
  const meta = el("dl", { class: "rule-meta" });
  if (rule.escalar) meta.append(el("dt", {}, "Avisar a"), el("dd", {}, rule.escalar));
  if (rule.impacto) meta.append(el("dt", {}, "Impacto"), el("dd", {}, rule.impacto));
  meta.append(el("dt", {}, "Origen"), el("dd", {}, `${rule.documento} · ${rule.area_label} · ${rule.seccion}`));
  const warn = rule.incompleto
    ? el("p", { class: "rule-warning" }, "El texto de esta regla está incompleto en el documento entregado. Confirma los pasos en el documento vigente o con el Soporte de Calidad.")
    : null;
  card.append(summary, el("div", { class: "rule-body" }, steps, meta, warn));
  return card;
}

function addExchange(question, label) {
  const block = el("article", { class: "exchange" });
  block.append(el("p", { class: "bubble-question" }, question), el("p", { class: "answer-state" }, label));
  thread.prepend(block);
  return block;
}

async function fetchRules(q, area) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (area) params.set("area", area);
  const response = await fetch(`/quality/reglas/buscar/?${params}`, { headers: { Accept: "application/json" } });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "No se pudo consultar las reglas.");
  return body.resultados;
}

async function ask(question) {
  const q = question.trim();
  if (!q) { input.focus(); return; }
  const scope = currentArea ? ` (${areaByKey[currentArea]?.label})` : "";
  const block = addExchange(q + scope, "Buscando la regla…");
  const state = block.querySelector(".answer-state");
  try {
    const results = await fetchRules(q, currentArea);
    if (!results.length) {
      state.textContent = "No encontré una regla para eso. Prueba con otras palabras (el parámetro y lo que ves) o elige un área. Si el desvío no tiene regla, avisa al Soporte de Calidad.";
      block.classList.add("is-empty");
      return;
    }
    const [best, ...others] = results;
    state.textContent = others.length ? "Esta es la regla que mejor responde:" : "Encontré esta regla:";
    block.append(ruleCard(best, { open: true, main: true }));
    if (others.length) {
      block.append(el("p", { class: "answer-more" }, "También podría ser:"));
      for (const r of others.slice(0, 4)) block.append(ruleCard(r));
    }
  } catch (error) {
    state.textContent = error.message;
    block.classList.add("is-error");
  }
}

async function browse(areaKey) {
  const area = areaByKey[areaKey];
  const block = addExchange(`Ver reglas de ${area.label}`, area.descripcion);
  if (area.sin_reglas) { block.classList.add("is-empty"); return; }
  try {
    const results = await fetchRules("", areaKey);
    let section = null;
    for (const r of results) {
      if (r.seccion !== section) {
        section = r.seccion;
        block.append(el("h3", { class: "section-title" }, section));
      }
      block.append(ruleCard(r));
    }
  } catch (error) {
    block.querySelector(".answer-state").textContent = error.message;
    block.classList.add("is-error");
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  ask(input.value);
});

chips.addEventListener("click", (event) => {
  const chip = event.target.closest(".stage-tab");
  if (!chip) return;
  setArea(chip.dataset.area);
  if (input.value.trim()) ask(input.value);
  else if (chip.dataset.area) browse(chip.dataset.area);
});

document.querySelector("#examples").addEventListener("click", (event) => {
  const example = event.target.closest(".example");
  if (!example) return;
  input.value = example.textContent;
  setArea("");
  ask(input.value);
});

document.querySelector("#docs").addEventListener("click", (event) => {
  const link = event.target.closest(".doc-link");
  if (!link) return;
  setArea(link.dataset.area);
  browse(link.dataset.area);
  thread.scrollIntoView({ behavior: "smooth", block: "start" });
});

// Llegada desde el analisis de lote (?q=...&area=...)
setArea(currentArea);
if (input.value.trim()) ask(input.value);
