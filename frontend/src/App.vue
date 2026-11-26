<script setup>
import { onMounted } from "vue";
import { start, state } from "./store.js";
import TopBar from "./components/TopBar.vue";
import StepLibrary from "./components/StepLibrary.vue";
import PipelineList from "./components/PipelineList.vue";
import GuideStrip from "./components/GuideStrip.vue";
import DataPanel from "./components/DataPanel.vue";
import Inspector from "./components/Inspector.vue";
import ExamplesDialog from "./components/ExamplesDialog.vue";

onMounted(start);
</script>

<template>
  <p v-if="state.offline" class="app-message">{{ state.offline }}</p>
  <p v-else-if="!state.catalog" class="app-message">Starting Gaze Lab…</p>
  <div v-else class="app">
    <TopBar />
    <aside class="side">
      <PipelineList />
      <StepLibrary />
    </aside>
    <main class="work">
      <GuideStrip v-if="state.guide" />
      <DataPanel />
    </main>
    <Inspector />
    <ExamplesDialog v-if="state.showExamples" />
  </div>
</template>
