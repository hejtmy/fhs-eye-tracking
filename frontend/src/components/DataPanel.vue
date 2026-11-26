<script setup>
// The data at the selected step: what came in, what went out, as figures or as tables.
import { computed, reactive, ref, watch } from "vue";
import { Download } from "lucide-vue-next";
import { download, post } from "../api.js";
import { graph, kinds, selectedNode, state } from "../store.js";
import PlotFigure from "./PlotFigure.vue";
import DataTable from "./DataTable.vue";

const LIMIT = 100;
const wanted = ref("output");
const compare = ref(true);
const remembered = reactive({});
const zoom = ref(null), offset = ref(0);
const figure = ref(null), page = ref(null), failure = ref(""), busy = ref(false);
const plot = ref(null);

const step = computed(() => state.steps[state.selected]);
const spec = computed(() => selectedNode.value && kinds.value[selectedNode.value.kind]);
const side = computed(() => (step.value?.status === "ok" ? wanted.value : "input"));
const tables = computed(() => (side.value === "input" ? step.value?.inputs : step.value?.tables) || []);
const views = computed(() => (side.value === "input" ? step.value?.input_views : step.value?.views) || []);
const valid = (tab) => !!tab && (tab.startsWith("table:") ? tables.value.some((t) => "table:" + t.name === tab) : views.value.some((v) => v.id === tab));
const key = computed(() => `${state.selected}:${side.value}`);
const tab = computed({
  get() {
    if (valid(remembered[key.value])) return remembered[key.value];
    if (side.value === "output" && valid(step.value?.view)) return step.value.view;
    return views.value[0]?.id || (tables.value[0] ? "table:" + tables.value[0].name : "");
  },
  set: (value) => (remembered[key.value] = value),
});
const table = computed(() => (tab.value.startsWith("table:") ? tables.value.find((t) => "table:" + t.name === tab.value) : null));
const view = computed(() => views.value.find((v) => v.id === tab.value));

const rawFile = computed(() => side.value === "input" && step.value?.is_source);
const participants = computed(() => Object.keys(step.value?.trials || {}));
const trialOptions = computed(() => {
  const all = step.value?.trials || {};
  return state.participant && all[state.participant] ? all[state.participant] : [...new Set(Object.values(all).flat())];
});
watch([participants, trialOptions], () => {
  if (state.participant && participants.value.length && !participants.value.includes(state.participant)) state.participant = "";
  if (state.trial && trialOptions.value.length && !trialOptions.value.includes(state.trial)) state.trial = "";
});

watch([() => state.selected, tab, side, () => state.participant, () => state.trial], () => {
  zoom.value = null;
  offset.value = 0;
});

const request = computed(() => {
  if (!step.value || !tab.value) return null;
  const base = { node: state.selected, side: side.value, participant: state.participant, trial: state.trial };
  return table.value ? { path: "table", body: { ...base, table: table.value.name, offset: offset.value, limit: LIMIT } }
    : { path: "view", body: { ...base, view: tab.value, compare: compare.value && side.value === "output", window: zoom.value } };
});
let ticket = 0;
watch(() => JSON.stringify([request.value, step.value?.fingerprint, step.value?.status]), async () => {
  const mine = ++ticket;
  if (!request.value) return (figure.value = page.value = null), (failure.value = "");
  busy.value = true;
  try {
    const answer = await post(request.value.path, { ...request.value.body, graph: graph() });
    if (mine !== ticket) return;
    failure.value = "";
    if (request.value.path === "table") (page.value = answer), (figure.value = null);
    else (figure.value = answer), (page.value = null);
  } catch (error) {
    if (mine === ticket) (failure.value = error.message), (figure.value = page.value = null);
  } finally {
    if (mine === ticket) busy.value = false;
  }
}, { immediate: true });

const figureName = computed(() => `${spec.value?.title || "figure"} ${view.value?.title || ""} ${state.participant} ${state.trial}`.trim().replace(/\s+/g, "-").toLowerCase());
const saveCsv = (excel = false) => download("download", { graph: graph(), node: state.selected, side: side.value, table: table.value.name, excel }, `${table.value.name}.csv`).catch((e) => (failure.value = e.message));
const rows = (n) => new Intl.NumberFormat("en").format(n).replaceAll(",", " ");
</script>

<template>
  <section class="data" aria-label="Data at the selected step">
    <p v-if="!state.selected" class="data-empty">Select a step to see the data that goes into it and comes out of it.</p>
    <template v-else>
      <header class="data-head">
        <div class="segmented" role="tablist" aria-label="Which side of the step">
          <button role="tab" :aria-selected="side === 'input'" :class="{ on: side === 'input' }" @click="wanted = 'input'">{{ step?.is_source ? "File as read" : "Input" }}</button>
          <button role="tab" :aria-selected="side === 'output'" :class="{ on: side === 'output' }" :disabled="step?.status !== 'ok'" @click="wanted = 'output'">Output</button>
        </div>
        <div class="tabs" role="tablist" aria-label="Figures and tables">
          <button v-for="v in views" :key="v.id" role="tab" :aria-selected="tab === v.id" :class="{ on: tab === v.id }" @click="tab = v.id">{{ v.title }}</button>
          <i v-if="views.length && tables.length" class="tab-gap"></i>
          <button v-for="t in tables" :key="t.name" role="tab" :aria-selected="tab === 'table:' + t.name" :class="['table-tab', { on: tab === 'table:' + t.name }]" :title="t.about" @click="tab = 'table:' + t.name">
            {{ t.title }}<small>{{ rows(t.rows) }}</small><b v-if="side === 'output' && t.change !== 'same'" :class="t.change">{{ t.change }}</b>
          </button>
        </div>
      </header>
      <div class="data-bar">
        <p class="data-title">
          <template v-if="failure">{{ failure }}</template>
          <template v-else-if="table">{{ table.about }} <span v-if="side === 'output' && table.detail">{{ table.detail }}</span></template>
          <template v-else-if="figure"><strong>{{ figure.info.title }}</strong> <span>{{ figure.info.hint }}</span></template>
          <template v-else-if="step?.status !== 'ok' && !tables.length">{{ step?.is_source ? "Choose a recording in the settings on the right to see its contents here." : "This step has not produced data yet." }}</template>
        </p>
        <div v-if="participants.length" class="data-controls">
          <label v-if="!rawFile">Participant
            <select v-model="state.participant"><option value="">{{ view?.single_trial ? "First" : "All" }}</option><option v-for="p in participants" :key="p">{{ p }}</option></select>
          </label>
          <label v-if="!rawFile">Trial
            <select v-model="state.trial"><option value="">{{ view?.single_trial ? "First" : "All" }}</option><option v-for="t in trialOptions" :key="t">{{ t }}</option></select>
          </label>
          <label v-if="view?.compares && side === 'output' && !step?.is_source" class="check" title="Draw the data as it was before this step, in grey, underneath">
            <input v-model="compare" type="checkbox" />Show input in grey
          </label>
          <template v-if="table">
            <button class="secondary" title="The whole table, all participants and trials. For JASP, jamovi, R and Python." @click="saveCsv(false)"><Download :size="14" />CSV</button>
            <button class="secondary" title="The same table with semicolons and decimal commas, which Excel expects with Czech and most European settings. Opens by double-click." @click="saveCsv(true)"><Download :size="14" />CSV for Excel</button>
          </template>
          <button v-else-if="figure" class="secondary" @click="plot?.savePng()"><Download :size="14" />PNG</button>
        </div>
      </div>
      <div class="data-body" :class="{ busy }">
        <PlotFigure v-if="figure" ref="plot" :figure="figure" :name="figureName" @zoom="zoom = $event" />
        <DataTable v-else-if="page" :page="page" :limit="LIMIT" @offset="offset = $event" />
      </div>
    </template>
  </section>
</template>
