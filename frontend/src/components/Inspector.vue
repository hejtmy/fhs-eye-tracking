<script setup>
import { computed, ref, watch } from "vue";
import { CircleAlert, GitBranch, Lightbulb, Trash2 } from "lucide-vue-next";
import { defaults, kinds, patchParams, removeStep, selectedNode, state } from "../store.js";
import RichText from "./RichText.vue";
import ParamForm from "./ParamForm.vue";

const node = selectedNode;
const spec = computed(() => node.value && kinds.value[node.value.kind]);
const step = computed(() => node.value && state.steps[node.value.id]);
const group = computed(() => state.catalog.groups.find((g) => g.id === spec.value?.group));
const changed = computed(() => (step.value?.tables || []).filter((t) => t.change !== "same"));
const pack = computed(() => spec.value?.package && { name: spec.value.package, ...state.catalog.packages?.[spec.value.package] });
const more = ref(false);
const copied = ref(false);
watch(() => node.value?.id, () => (more.value = copied.value = false));

async function copyScript() {
  await navigator.clipboard.writeText(step.value.script);
  copied.value = true;
  setTimeout(() => (copied.value = false), 2000);
}

function reset() {
  const fresh = defaults(node.value.kind);
  if (node.value.kind === "load") delete fresh.source; // keep the chosen recording
  patchParams(node.value.id, fresh);
}
</script>

<template>
  <aside class="inspector" aria-label="Selected step">
    <template v-if="node && spec">
      <header class="inspector-head" :style="{ '--stage': `var(--g-${spec.group})` }">
        <span class="stage-tag"><i class="stage-dot"></i>{{ group.title }}</span>
        <h2>{{ spec.title }}</h2>
        <p v-if="pack" class="package">Calculated by <a :href="pack.url" target="_blank" rel="noopener">{{ pack.name }}</a> {{ pack.version }}</p>
        <div class="inspector-actions">
          <button v-if="!spec.source || true" title="Start a new branch after this step, e.g. to compare two methods" :class="{ on: state.branchFrom === node.id }" @click="state.branchFrom = state.branchFrom === node.id ? null : node.id">
            <GitBranch :size="15" />Branch
          </button>
          <button title="Remove this step; the steps after it stay connected" @click="removeStep(node.id)"><Trash2 :size="15" />Remove</button>
        </div>
      </header>
      <div class="inspector-body">
        <p v-if="step?.status === 'error'" class="alert" role="alert"><CircleAlert :size="16" /><span>{{ step.error }}</span></p>
        <p v-else-if="step?.status === 'blocked'" class="alert quiet"><CircleAlert :size="16" /><span>This step has not run because an earlier step needs attention.</span></p>

        <section class="explain">
          <RichText :text="spec.explain" :first-only="!more" />
          <button class="link" @click="more = !more">{{ more ? "Show less" : "Read the full explanation" }}</button>
        </section>

        <section v-if="spec.params.length">
          <h3>Settings</h3>
          <ParamForm :params="spec.params" :values="node.params" :tables="step?.inputs || []" :node-id="node.id" @change="patchParams(node.id, $event)" />
          <button class="link reset" @click="reset">Reset to the defaults</button>
        </section>

        <section v-if="step?.status === 'ok' && (step.notes.length || changed.length)">
          <h3>What this step did</h3>
          <ul class="notes">
            <li v-for="note in step.notes" :key="note">{{ note }}</li>
          </ul>
          <dl v-if="changed.length" class="changes">
            <template v-for="t in changed" :key="t.name">
              <dt :class="t.change">{{ t.title }}<small>{{ t.change }}</small></dt>
              <dd>{{ t.detail }}</dd>
            </template>
          </dl>
        </section>

        <section v-if="spec.question" class="question">
          <Lightbulb :size="16" />
          <p>{{ spec.question }}</p>
        </section>

        <details v-if="step?.script" class="code">
          <summary>Do this step in your own Python script</summary>
          <p>The same {{ pack.name }} calls this step makes, with your current settings. The script runs without Gaze Lab.</p>
          <pre>{{ step.script }}</pre>
          <button class="link" @click="copyScript">{{ copied ? "Copied" : "Copy the script" }}</button>
        </details>
        <details class="code">
          <summary>Show this step's code in Gaze Lab</summary>
          <pre>{{ spec.code }}</pre>
        </details>
      </div>
    </template>
    <p v-else class="inspector-empty">Select a step in the pipeline to read what it does and change its settings.</p>
  </aside>
</template>
