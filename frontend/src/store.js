// The one place that holds the pipeline and talks to the server about it.
import { computed, reactive, watch } from "vue";
import { download, get, post, saveBlob } from "./api.js";
import { ancestors, arrange } from "./layout.js";

const SAVED = "gazelab.pipeline.v2";
const UPLOADS = "gazelab.uploads.v2";

export const state = reactive({
  catalog: null,
  offline: "",
  name: "Untitled pipeline",
  nodes: [], // { id, kind, params }
  edges: [], // { source, target }
  selected: null,
  branchFrom: null, // when set, the next step added starts a new branch here
  steps: {}, // what the server reported for each step
  running: false,
  problem: "",
  guide: null, // { title, tasks, at }
  uploads: [], // datasets this browser uploaded: { id, name }
  datasets: {}, // dataset descriptions by id
  participant: "",
  trial: "",
  showExamples: false,
});

export const kinds = computed(() => Object.fromEntries((state.catalog?.nodes || []).map((n) => [n.kind, n])));
export const arrangement = computed(() => arrange(state.nodes, state.edges));
export const selectedNode = computed(() => state.nodes.find((n) => n.id === state.selected) || null);
export const graph = () => ({ nodes: state.nodes.map(({ id, kind, params }) => ({ id, kind, params })), edges: state.edges.map(({ source, target }) => ({ source, target })) });

const clone = (value) => JSON.parse(JSON.stringify(value ?? null));
const freshId = () => "s" + Math.random().toString(36).slice(2, 8);

export function defaults(kind) {
  const params = Object.fromEntries(kinds.value[kind].params.map((p) => [p.key, clone(p.default)]));
  if (kind === "load") params.source = { dataset: "", reader: "auto", options: {}, mapping: {}, extra: [] };
  return params;
}

// The step a new one would be attached to, and what data exists there.
export const anchor = computed(() => {
  if (state.branchFrom && state.nodes.some((n) => n.id === state.branchFrom)) return state.branchFrom;
  if (state.selected) return state.selected;
  const { rows, children } = arrangement.value;
  return rows.findLast((r) => r.depth === 0 && !children[r.id].length)?.id || rows.at(-1)?.id || null; // the end of the main line
});

export function availability(kind) {
  const spec = kinds.value[kind];
  if (spec.source) return { ok: true, why: "" };
  if (!anchor.value) return { ok: false, why: "Start with “Load recording”." };
  const step = state.steps[anchor.value];
  if (!step || step.status !== "ok") return { ok: true, why: "" };
  const have = new Set(step.tables.map((t) => t.name));
  const missing = spec.needs.filter((t) => !have.has(t));
  if (!missing.length) return { ok: true, why: "" };
  const makers = state.catalog.nodes.filter((n) => n.makes.includes(missing[0])).map((n) => `“${n.title}”`);
  return { ok: false, why: `Needs ${missing[0].replaceAll("_", " ")}. Add ${makers.slice(0, 2).join(" or ")} first.` };
}

export function addStep(kind) {
  const node = { id: freshId(), kind, params: defaults(kind) };
  const at = kinds.value[kind].source ? null : anchor.value;
  if (at) {
    if (!state.branchFrom) for (const edge of state.edges) if (edge.source === at) edge.source = node.id; // slot in between
    state.edges.push({ source: at, target: node.id });
  }
  state.nodes.push(node);
  state.branchFrom = null;
  state.selected = node.id;
}

export function removeStep(id) {
  const parent = arrangement.value.parent[id];
  state.edges = state.edges.filter((e) => e.target !== id);
  for (const edge of state.edges) if (edge.source === id) edge.source = parent;
  state.edges = state.edges.filter((e) => e.source);
  state.nodes = state.nodes.filter((n) => n.id !== id);
  state.selected = parent || state.nodes[0]?.id || null;
  state.branchFrom = null;
}

export function patchParams(id, changes) {
  const node = state.nodes.find((n) => n.id === id);
  if (node) Object.assign(node.params, clone(changes));
}

// The Load step that feeds a given step, e.g. to find its stimulus images.
export function loadStepFor(id) {
  const chain = [id, ...ancestors(arrangement.value.parent, id)];
  return state.nodes.find((n) => n.id === chain.at(-1) && n.kind === "load") || null;
}

export async function datasetInfo(id, refresh = false) {
  if (!id) return null;
  if (!state.datasets[id] || refresh) state.datasets[id] = await get(`datasets/${id}`);
  return state.datasets[id];
}

export function rememberUpload(dataset) {
  state.datasets[dataset.id] = dataset;
  state.uploads = [{ id: dataset.id, name: dataset.name }, ...state.uploads.filter((u) => u.id !== dataset.id)].slice(0, 30);
  localStorage.setItem(UPLOADS, JSON.stringify(state.uploads));
}

export function forgetUpload(id) {
  state.uploads = state.uploads.filter((u) => u.id !== id);
  localStorage.setItem(UPLOADS, JSON.stringify(state.uploads));
}

// ---------------------------------------------------------------- pipelines as a whole

export function openPipeline(spec, guide = true) {
  const known = (spec.graph?.nodes || []).filter((n) => kinds.value[n.kind]);
  state.nodes = known.map((n) => ({ id: n.id, kind: n.kind, params: { ...defaults(n.kind), ...clone(n.params), ...(n.kind === "load" ? { source: { ...defaults("load").source, ...clone(n.params?.source) } } : {}) } }));
  state.edges = clone(spec.graph?.edges || []).filter((e) => known.some((n) => n.id === e.source) && known.some((n) => n.id === e.target));
  state.name = spec.name || "Untitled pipeline";
  state.guide = guide && spec.tasks?.length ? { title: spec.name, tasks: spec.tasks, at: 0 } : null;
  state.steps = {};
  state.participant = state.trial = "";
  state.branchFrom = null;
  state.selected = state.nodes[0]?.id || null;
  state.showExamples = false;
}

export function newPipeline() {
  openPipeline({ name: "Untitled pipeline", graph: { nodes: [{ id: freshId(), kind: "load", params: {} }], edges: [] } });
}

export function savePipelineFile() {
  const file = { gazelab: state.catalog.version, name: state.name, graph: graph() };
  saveBlob(new Blob([JSON.stringify(file, null, 2)], { type: "application/json" }), `${state.name.replace(/[^\w-]+/g, "-").toLowerCase() || "pipeline"}.json`);
}

export async function openPipelineFile(file) {
  try {
    const spec = JSON.parse(await file.text());
    if (!spec.graph?.nodes) throw new Error();
    openPipeline(spec, false);
  } catch {
    state.problem = "That file is not a Gaze Lab pipeline (a .json file saved with “Save”).";
  }
}

export const exportResults = () => download("export", { graph: graph(), name: state.name }, "gaze-lab-results.zip").catch((e) => (state.problem = e.message));

// ---------------------------------------------------------------- running

let ticket = 0;
let timer = null;

export async function run() {
  if (!state.nodes.length) return (state.steps = {});
  const mine = ++ticket;
  state.running = true;
  try {
    const result = await post("run", { graph: graph() });
    if (mine !== ticket) return; // a newer change is already on its way
    state.steps = result.steps;
    state.problem = "";
  } catch (error) {
    if (mine === ticket) state.problem = error.message;
  } finally {
    if (mine === ticket) state.running = false;
  }
}

export async function start() {
  try {
    state.catalog = await get("catalog");
  } catch (error) {
    state.offline = "Gaze Lab cannot reach its server. Check that it is running, then reload this page.";
    return;
  }
  try {
    state.uploads = JSON.parse(localStorage.getItem(UPLOADS) || "[]");
    const saved = JSON.parse(localStorage.getItem(SAVED) || "null");
    if (saved?.graph?.nodes?.length) {
      openPipeline(saved, false);
      state.guide = saved.guide || null;
      state.selected = saved.selected && state.nodes.some((n) => n.id === saved.selected) ? saved.selected : state.selected;
    } else state.showExamples = true;
  } catch {
    state.showExamples = true;
  }
  // Any change to the pipeline is saved in this browser and re-run shortly after.
  watch(
    () => JSON.stringify(graph()),
    () => {
      clearTimeout(timer);
      timer = setTimeout(run, 250);
    },
    { immediate: true },
  );
  watch(
    () => [JSON.stringify(graph()), state.name, state.selected, state.guide],
    () => localStorage.setItem(SAVED, JSON.stringify({ name: state.name, graph: graph(), selected: state.selected, guide: state.guide })),
    { deep: true },
  );
}
