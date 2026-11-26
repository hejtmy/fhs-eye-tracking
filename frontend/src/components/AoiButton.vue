<script setup>
import { ref } from "vue";
import { PenLine } from "lucide-vue-next";
import AoiEditor from "./AoiEditor.vue";

const props = defineProps({ param: Object, value: Array, values: Object, nodeId: String });
const emit = defineEmits(["change"]);
const editing = ref(false);
const names = () => [...new Set((props.value || []).map((a) => a.name))];

function done(areas) {
  editing.value = false;
  if (areas) emit("change", { [props.param.key]: areas });
}
</script>

<template>
  <div class="field">
    <label>{{ param.label }}</label>
    <p class="aoi-names">{{ names().length ? names().join(", ") : "None drawn yet." }}</p>
    <button class="secondary" @click="editing = true"><PenLine :size="15" />{{ names().length ? "Edit the areas" : "Draw areas" }}</button>
    <AoiEditor v-if="editing" :areas="value || []" :node-id="nodeId" @close="done" />
  </div>
</template>
