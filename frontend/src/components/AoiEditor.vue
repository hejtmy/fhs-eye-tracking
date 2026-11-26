<script setup>
// Draw rectangles and ellipses on the stimulus. Coordinates are screen pixels, as in the data.
import { computed, onMounted, reactive, ref } from "vue";
import { Circle, MousePointer2, Square, Trash2, X } from "lucide-vue-next";
import { post } from "../api.js";
import { datasetInfo, graph, loadStepFor, state } from "../store.js";

const props = defineProps({ areas: Array, nodeId: String });
const emit = defineEmits(["close"]);

const shapes = reactive(JSON.parse(JSON.stringify(props.areas)));
const load = loadStepFor(props.nodeId);
const width = load?.params.width_px || 1920, height = load?.params.height_px || 1080;
const datasetId = load?.params.source?.dataset;
const stimuli = ref([]);
const current = ref(""); // the stimulus on screen; "" when the data have none
const fixations = ref([]);
const tool = ref("rect");
const selected = ref(-1);
const svg = ref(null);
let drag = null;

const visible = computed(() => shapes.map((s, i) => ({ s, i })).filter(({ s }) => !s.stimulus || s.stimulus === current.value));
const dots = computed(() => fixations.value.filter((f) => !current.value || f.stimulus == null || f.stimulus === current.value));
const unit = Math.max(width, height) / 400; // one “screen pixel” of line width, whatever the zoom

onMounted(async () => {
  try {
    stimuli.value = (await datasetInfo(datasetId))?.stimuli || [];
    current.value = stimuli.value.find((n) => shapes.some((s) => s.stimulus === n)) || stimuli.value[0] || "";
  } catch { /* no images: draw on a blank screen */ }
  try {
    const page = await post("table", { graph: graph(), node: props.nodeId, side: "input", table: "fixations", limit: 500 });
    const at = Object.fromEntries(page.columns.map((c, i) => [c.name, i]));
    fixations.value = page.rows.map((r) => ({ x: r[at.x], y: r[at.y], stimulus: at.stimulus === undefined ? null : r[at.stimulus] }));
  } catch { /* no fixations before this step: nothing to show underneath */ }
  if (shapes.length) tool.value = "select";
});

function point(event) {
  const p = new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.value.getScreenCTM().inverse());
  return { x: Math.round(p.x), y: Math.round(p.y) };
}
function down(event, index = -1, mode = "move") {
  const p = point(event);
  if (tool.value !== "select" && index < 0) {
    let n = shapes.length + 1;
    while (shapes.some((s) => s.name === `Area ${n}`)) n++;
    shapes.push({ name: `Area ${n}`, shape: tool.value, x: p.x, y: p.y, w: 1, h: 1, stimulus: current.value });
    selected.value = shapes.length - 1;
    drag = { mode: "draw", origin: p, shape: shapes.at(-1) };
  } else if (index >= 0) {
    selected.value = index;
    drag = { mode, origin: p, shape: shapes[index], start: { ...shapes[index] } };
  } else selected.value = -1;
  if (drag) svg.value.setPointerCapture(event.pointerId);
}
function move(event) {
  if (!drag) return;
  const p = point(event), s = drag.shape;
  if (drag.mode === "draw") Object.assign(s, { x: Math.min(p.x, drag.origin.x), y: Math.min(p.y, drag.origin.y), w: Math.abs(p.x - drag.origin.x), h: Math.abs(p.y - drag.origin.y) });
  else if (drag.mode === "move") Object.assign(s, { x: drag.start.x + p.x - drag.origin.x, y: drag.start.y + p.y - drag.origin.y });
  else Object.assign(s, { w: Math.max(8, drag.start.w + p.x - drag.origin.x), h: Math.max(8, drag.start.h + p.y - drag.origin.y) });
}
function up() {
  if (drag?.mode === "draw") {
    if (drag.shape.w < 8 || drag.shape.h < 8) shapes.splice(shapes.indexOf(drag.shape), 1), (selected.value = -1);
    else tool.value = "select";
  }
  drag = null;
}
function remove(index) {
  shapes.splice(index, 1);
  selected.value = -1;
}
const problem = computed(() => (shapes.some((s) => !String(s.name).trim()) ? "Every area needs a name." : ""));
</script>

<template>
  <Teleport to="body">
    <div class="overlay">
      <div class="dialog aoi-editor" role="dialog" aria-modal="true" aria-labelledby="aoi-title">
        <header>
          <h2 id="aoi-title">Areas of interest</h2>
          <div class="tools" role="toolbar" aria-label="Drawing tools">
            <button :class="{ on: tool === 'select' }" @click="tool = 'select'"><MousePointer2 :size="15" />Move and resize</button>
            <button :class="{ on: tool === 'rect' }" @click="tool = 'rect'"><Square :size="15" />Rectangle</button>
            <button :class="{ on: tool === 'ellipse' }" @click="tool = 'ellipse'"><Circle :size="15" />Ellipse</button>
          </div>
          <label v-if="stimuli.length > 1" class="inline">Stimulus
            <select v-model="current"><option v-for="name in stimuli" :key="name" :value="name">{{ name }}</option></select>
          </label>
          <button class="icon" title="Close without saving" @click="emit('close', null)"><X :size="17" /></button>
        </header>
        <div class="aoi-main">
          <svg ref="svg" class="aoi-stage" :class="tool" :viewBox="`0 0 ${width} ${height}`" @pointerdown="down($event)" @pointermove="move" @pointerup="up" @pointercancel="up">
            <rect :width="width" :height="height" fill="#fff" />
            <image v-if="current" :href="`/api/datasets/${datasetId}/stimuli/${encodeURIComponent(current)}`" :width="width" :height="height" preserveAspectRatio="none" opacity="0.9" />
            <circle v-for="(f, i) in dots" :key="i" :cx="f.x" :cy="f.y" :r="unit * 1.6" class="aoi-dot" />
            <g v-for="{ s, i } in visible" :key="i" class="aoi-shape" :class="{ selected: selected === i }" :style="{ '--w': unit + 'px' }">
              <ellipse v-if="s.shape === 'ellipse'" :cx="s.x + s.w / 2" :cy="s.y + s.h / 2" :rx="s.w / 2" :ry="s.h / 2" @pointerdown.stop="down($event, i)" />
              <rect v-else :x="s.x" :y="s.y" :width="s.w" :height="s.h" @pointerdown.stop="down($event, i)" />
              <text :x="s.x + s.w / 2" :y="s.y - unit * 2" :font-size="unit * 5.5" text-anchor="middle">{{ s.name }}</text>
              <rect v-if="selected === i" class="handle" :x="s.x + s.w - unit * 2.5" :y="s.y + s.h - unit * 2.5" :width="unit * 5" :height="unit * 5" @pointerdown.stop="down($event, i, 'resize')" />
            </g>
          </svg>
          <div class="aoi-list">
            <p v-if="!shapes.length" class="hint">Choose Rectangle or Ellipse, then drag on the picture. The dots are fixations from the step before this one.</p>
            <div v-for="(s, i) in shapes" :key="i" class="aoi-row" :class="{ selected: selected === i, away: s.stimulus && s.stimulus !== current }" @click="(selected = i), s.stimulus && (current = s.stimulus)">
              <input v-model="s.name" maxlength="60" aria-label="Name of the area" />
              <button class="icon" title="Delete this area" @click.stop="remove(i)"><Trash2 :size="14" /></button>
              <select v-if="stimuli.length" v-model="s.stimulus" aria-label="Which stimulus this area belongs to">
                <option value="">Every stimulus</option>
                <option v-for="name in stimuli" :key="name" :value="name">Only {{ name }}</option>
              </select>
              <div class="aoi-numbers">
                <label v-for="k in ['x', 'y', 'w', 'h']" :key="k">{{ k }}<input v-model.number="s[k]" type="number" /></label>
              </div>
            </div>
          </div>
        </div>
        <footer>
          <p class="hint">{{ problem || "Where areas overlap, the one higher in the list wins. Sizes are in screen pixels." }}</p>
          <button @click="emit('close', null)">Cancel</button>
          <button class="primary" :disabled="!!problem" @click="emit('close', JSON.parse(JSON.stringify(shapes)))">Use these areas</button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>
