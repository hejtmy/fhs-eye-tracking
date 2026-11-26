<script setup>
import { computed } from "vue";
import { Upload, X } from "lucide-vue-next";
import { newPipeline, openPipeline, state } from "../store.js";

const datasets = computed(() => Object.fromEntries(state.catalog.examples.datasets.map((d) => [d.id, d])));
</script>

<template>
  <div class="overlay" @click.self="state.nodes.length && (state.showExamples = false)">
    <div class="dialog examples" role="dialog" aria-modal="true" aria-labelledby="examples-title">
      <header>
        <h2 id="examples-title">What would you like to work on?</h2>
        <button v-if="state.nodes.length" class="icon" title="Close" @click="state.showExamples = false"><X :size="17" /></button>
      </header>
      <button class="own-data" @click="newPipeline">
        <Upload :size="20" />
        <span><strong>Analyse your own recording</strong>
          Upload a Tobii Pro Lab export, a Tobii Glasses 2 <code>livedata.json.gz</code>, an EyeLink ASC file or any CSV of gaze samples.</span>
      </button>
      <h3>Or learn with a worked example</h3>
      <div class="example-list">
        <button v-for="example in state.catalog.examples.pipelines" :key="example.id" class="example" @click="openPipeline(example)">
          <strong>{{ example.name }}</strong>
          <span>{{ example.description }}</span>
          <small>{{ datasets[example.dataset]?.name }}, {{ example.graph.nodes.length }} steps</small>
        </button>
      </div>
      <p class="fine-print">The example recordings are simulated, so that the true eye movements are known. They support no scientific conclusion.
        Opening an example replaces the pipeline on screen; save yours first if you want to keep it.</p>
    </div>
  </div>
</template>
