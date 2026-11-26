<script setup>
// The pipeline, drawn like a scanpath: numbered points joined by lines, read from top to bottom.
import { computed, nextTick, ref, watch } from "vue";
import { arrangement, kinds, state } from "../store.js";

const ROW = 46, INDENT = 20, LEFT = 24, DOT = 24;
const list = ref(null);

const rows = computed(() =>
  arrangement.value.rows.map(({ id, depth }, index) => {
    const node = state.nodes.find((n) => n.id === id);
    const step = state.steps[id];
    const status = step?.status || "pending";
    const sub = status === "ok" ? step.headline || "Done" : status === "error" ? "Needs attention" : status === "blocked" ? "Waiting for an earlier step" : "Running…";
    return { id, depth, index, spec: kinds.value[node.kind], status, sub };
  }),
);
const wires = computed(() => {
  const at = Object.fromEntries(rows.value.map((r) => [r.id, r]));
  const x = (r) => LEFT + r.depth * INDENT, y = (r) => r.index * ROW + ROW / 2;
  return state.edges.filter((e) => at[e.source] && at[e.target]).map((e) => {
    const a = at[e.source], b = at[e.target];
    const d = a.depth === b.depth ? `M${x(a)} ${y(a)}V${y(b)}` : `M${x(a)} ${y(a)}V${y(b) - 8}q0 8 8 8H${x(b)}`;
    return { key: e.source + e.target, d, dim: b.status === "blocked" || b.status === "error" };
  });
});

watch(() => state.selected, async (id) => {
  await nextTick();
  list.value?.querySelector(`[data-step="${id}"]`)?.scrollIntoView({ block: "nearest" });
});
</script>

<template>
  <section class="pipeline" aria-label="Pipeline">
    <h2>Pipeline</h2>
    <p v-if="!state.nodes.length" class="pipeline-empty">No steps yet. Add “Load recording” below.</p>
    <div v-else ref="list" class="pipeline-list" :style="{ height: rows.length * ROW + 'px' }">
      <svg class="wires" width="100%" :height="rows.length * ROW" aria-hidden="true">
        <path v-for="wire in wires" :key="wire.key" :d="wire.d" :class="{ dim: wire.dim }" />
      </svg>
      <button
        v-for="row in rows" :key="row.id" class="step" :class="[row.status, { selected: state.selected === row.id, branching: state.branchFrom === row.id }]"
        :data-step="row.id" :style="{ top: row.index * ROW + 'px', paddingLeft: LEFT - DOT / 2 + row.depth * INDENT + 'px', '--stage': `var(--g-${row.spec.group})` }"
        :aria-pressed="state.selected === row.id" :title="row.spec.title" @click="state.selected = row.id"
      >
        <span class="step-number">{{ row.index + 1 }}</span>
        <span class="step-text"><strong>{{ row.spec.title }}</strong><small>{{ row.sub }}</small></span>
      </button>
    </div>
  </section>
</template>
