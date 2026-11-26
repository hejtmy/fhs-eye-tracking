<script setup>
import { computed, ref } from "vue";

const props = defineProps({ id: String, param: Object, value: [Array, String], columns: Array });
const emit = defineEmits(["change"]);
const filter = ref("");
const chosen = computed(() => (props.param.multiple ? props.value || [] : props.value ? [props.value] : []));
const shown = computed(() => (props.columns || []).filter((c) => c.name.toLowerCase().includes(filter.value.toLowerCase())));
const matches = (name) => props.param.pattern && new RegExp("^" + props.param.pattern.replace(/[.+?^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*") + "$", "i").test(name);

function toggle(name) {
  emit("change", chosen.value.includes(name) ? chosen.value.filter((c) => c !== name) : [...chosen.value, name]);
}
</script>

<template>
  <p v-if="!columns" class="picker-empty">Columns appear here once the step before this one has run{{ param.table_from ? " and a table is chosen above" : "" }}.</p>
  <select v-else-if="!param.multiple" :id="id" :value="value" @change="emit('change', $event.target.value)">
    <option value="">Automatic{{ columns.find((c) => matches(c.name)) ? `: ${columns.find((c) => matches(c.name)).name}` : "" }}</option>
    <option v-for="c in columns" :key="c.name" :value="c.name">{{ c.name }}</option>
  </select>
  <div v-else class="picker">
    <input v-if="columns.length > 8" v-model="filter" type="search" placeholder="Find a column" :aria-label="`Find a column for ${param.label}`" />
    <div class="picker-list">
      <label v-for="c in shown" :key="c.name" :class="{ auto: !chosen.length && matches(c.name) }">
        <input type="checkbox" :checked="chosen.includes(c.name)" @change="toggle(c.name)" />{{ c.name }}
      </label>
    </div>
    <small>{{ chosen.length ? `${chosen.length} chosen.` : param.pattern ? "Nothing chosen: the highlighted columns are used automatically." : "Nothing chosen: decided automatically." }}
      <button v-if="chosen.length" class="link" @click="emit('change', [])">Clear</button></small>
  </div>
</template>
