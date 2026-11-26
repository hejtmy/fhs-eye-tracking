<script setup>
import { ChevronLeft, ChevronRight, X } from "lucide-vue-next";
import { state } from "../store.js";

const turn = (by) => (state.guide.at = Math.min(state.guide.tasks.length - 1, Math.max(0, state.guide.at + by)));
</script>

<template>
  <div class="guide">
    <strong>Try this, {{ state.guide.at + 1 }} of {{ state.guide.tasks.length }}</strong>
    <p>{{ state.guide.tasks[state.guide.at] }}</p>
    <button title="Previous suggestion" :disabled="state.guide.at === 0" @click="turn(-1)"><ChevronLeft :size="16" /></button>
    <button title="Next suggestion" :disabled="state.guide.at === state.guide.tasks.length - 1" @click="turn(1)"><ChevronRight :size="16" /></button>
    <button title="Hide these suggestions" @click="state.guide = null"><X :size="15" /></button>
  </div>
</template>
