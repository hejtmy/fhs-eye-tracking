<script setup>
import { computed } from "vue";
import { addStep, anchor, availability, kinds, state } from "../store.js";
import { iconFor } from "../icons.js";

const groups = computed(() => state.catalog.groups.map((g) => ({ ...g, nodes: state.catalog.nodes.filter((n) => n.group === g.id) })).filter((g) => g.nodes.length));
const anchorTitle = computed(() => {
  const node = state.nodes.find((n) => n.id === anchor.value);
  return node ? kinds.value[node.kind].title : "";
});
</script>

<template>
  <section class="library" aria-label="Steps you can add">
    <h2>Add a step</h2>
    <p class="library-hint" :class="{ branching: state.branchFrom }">
      <template v-if="state.branchFrom">The next step you pick starts a new branch after “{{ anchorTitle }}”. <button class="link" @click="state.branchFrom = null">Cancel</button></template>
      <template v-else-if="anchorTitle">It is placed after “{{ anchorTitle }}”.</template>
      <template v-else>Start with “Load recording”.</template>
    </p>
    <section v-for="group in groups" :key="group.id" :style="{ '--stage': `var(--g-${group.id})` }">
      <h3 :title="group.hint"><i class="stage-dot"></i>{{ group.title }}</h3>
      <button
        v-for="node in group.nodes" :key="node.kind" class="library-item" :class="{ unavailable: !availability(node.kind).ok }"
        :title="availability(node.kind).why || node.summary" :aria-disabled="!availability(node.kind).ok"
        @click="availability(node.kind).ok ? addStep(node.kind) : (state.problem = availability(node.kind).why)"
      >
        <component :is="iconFor(node.icon)" :size="15" /><span>{{ node.title }}</span>
      </button>
    </section>
  </section>
</template>
