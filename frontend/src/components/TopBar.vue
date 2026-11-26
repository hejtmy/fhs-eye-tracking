<script setup>
import { computed, ref } from "vue";
import { BookOpen, Download, FolderOpen, Save } from "lucide-vue-next";
import { exportResults, openPipelineFile, savePipelineFile, state } from "../store.js";

const picker = ref(null);
const exporting = ref(false);
const failing = computed(() => state.nodes.filter((n) => state.steps[n.id]?.status === "error"));
const status = computed(() => {
  if (state.problem) return { tone: "bad", text: state.problem };
  if (state.running) return { tone: "busy", text: "Running…" };
  if (failing.value.length) return { tone: "bad", text: `${failing.value.length} step${failing.value.length > 1 ? "s need" : " needs"} attention` };
  return { tone: "ok", text: state.nodes.length ? "Up to date" : "" };
});

async function exportAll() {
  exporting.value = true;
  await exportResults();
  exporting.value = false;
}
function opened(event) {
  if (event.target.files[0]) openPipelineFile(event.target.files[0]);
  event.target.value = "";
}
</script>

<template>
  <header class="top">
    <div class="brand">
      <svg viewBox="0 0 32 32" width="22" height="22" aria-hidden="true"><circle cx="16" cy="16" r="14" fill="var(--accent)" /><circle cx="16" cy="16" r="6" fill="#fff" /></svg>
      Gaze Lab
    </div>
    <input v-model="state.name" class="pipeline-name" aria-label="Name of this pipeline" spellcheck="false" />
    <button v-if="status.text" class="run-status" :class="status.tone" :disabled="!failing.length" @click="state.selected = failing[0]?.id">
      <i></i>{{ status.text }}
    </button>
    <nav class="top-actions">
      <button @click="state.showExamples = true"><BookOpen :size="15" />Examples</button>
      <button @click="picker.click()"><FolderOpen :size="15" />Open</button>
      <button @click="savePipelineFile"><Save :size="15" />Save</button>
      <button class="primary" :disabled="exporting || !state.nodes.length" title="A zip with every result table as CSV and a script that reproduces them" @click="exportAll">
        <Download :size="15" />{{ exporting ? "Preparing…" : "Export results" }}
      </button>
      <input ref="picker" type="file" accept=".json,application/json" hidden @change="opened" />
    </nav>
  </header>
</template>
