<script setup>
// Draws a settings form from the parameter descriptions a step (or file reader) publishes.
// A new kind of control is one more entry in `special` plus its component.
import { computed } from "vue";
import SourceEditor from "./SourceEditor.vue";
import AoiButton from "./AoiButton.vue";
import ColumnPicker from "./ColumnPicker.vue";

const props = defineProps({ params: Array, values: Object, tables: { type: Array, default: () => [] }, nodeId: { type: String, default: "" } });
const emit = defineEmits(["change"]);
const special = { source: SourceEditor, aois: AoiButton };

const visible = computed(() => props.params.filter((p) => !p.when || Object.entries(p.when).every(([key, value]) => props.values[key] === value)));
const set = (key, value) => emit("change", { [key]: value });
const resultTables = computed(() => props.tables.filter((t) => !["samples", "events", "aois", "trials"].includes(t.name)));

function number(param, event) {
  const value = parseFloat(String(event.target.value).replace(",", "."));
  if (Number.isFinite(value)) set(param.key, value);
  else event.target.value = props.values[param.key];
}
const unit = (param) => (typeof param.unit === "object" ? param.unit[props.values[param.unit_from]] : param.unit); // a unit can follow another setting
function columnsFor(param) {
  const name = param.table_from ? props.values[param.table_from] : param.table;
  return props.tables.find((t) => t.name === name)?.columns || null;
}
</script>

<template>
  <div class="form">
    <template v-for="p in visible" :key="p.key">
      <component :is="special[p.control]" v-if="special[p.control]" :param="p" :value="values[p.key]" :values="values" :node-id="nodeId" @change="emit('change', $event)" />
      <label v-else-if="p.control === 'toggle'" class="field toggle">
        <input type="checkbox" :checked="values[p.key]" @change="set(p.key, $event.target.checked)" />
        <span>{{ p.label }}<small v-if="p.help">{{ p.help }}</small></span>
      </label>
      <div v-else class="field">
        <label :for="nodeId + p.key">{{ p.label }}</label>
        <div v-if="p.control === 'number'" class="with-unit">
          <input :id="nodeId + p.key" type="number" :value="values[p.key]" :min="p.min" :max="p.max" :step="p.step" @change="number(p, $event)" />
          <span v-if="unit(p)">{{ unit(p) }}</span>
        </div>
        <select v-else-if="p.control === 'select'" :id="nodeId + p.key" :value="values[p.key]" @change="set(p.key, $event.target.value)">
          <option v-for="[value, label] in p.options" :key="value" :value="value">{{ label }}</option>
        </select>
        <select v-else-if="p.control === 'table'" :id="nodeId + p.key" :value="values[p.key]" @change="emit('change', { [p.key]: $event.target.value, by: [] })">
          <option value="">Automatic (the latest result table)</option>
          <option v-for="t in resultTables" :key="t.name" :value="t.name">{{ t.title }}</option>
        </select>
        <ColumnPicker v-else-if="p.control === 'columns'" :id="nodeId + p.key" :param="p" :value="values[p.key]" :columns="columnsFor(p)" @change="set(p.key, $event)" />
        <textarea v-else-if="p.multiline" :id="nodeId + p.key" :value="values[p.key]" rows="6" spellcheck="false" @change="set(p.key, $event.target.value)"></textarea>
        <input v-else :id="nodeId + p.key" type="text" :value="values[p.key]" :placeholder="p.placeholder" spellcheck="false" @change="set(p.key, $event.target.value)" />
        <small v-if="p.help">{{ p.help }}</small>
      </div>
    </template>
  </div>
</template>
