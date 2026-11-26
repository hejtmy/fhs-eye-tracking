<script setup>
import { ChevronLeft, ChevronRight } from "lucide-vue-next";

const props = defineProps({ page: Object, limit: Number });
const emit = defineEmits(["offset"]);
const plain = new Intl.NumberFormat("en", { maximumFractionDigits: 2, useGrouping: false });
const spaced = new Intl.NumberFormat("en", { useGrouping: true });
const count = (n) => spaced.format(n).replaceAll(",", " ");

function show(value, column) {
  if (value === null || value === undefined || value === "") return "";
  if (column.type === "yes/no") return value ? "yes" : "";
  if (typeof value === "number") return plain.format(value);
  return String(value);
}
</script>

<template>
  <div class="table-wrap">
    <div class="table-scroll">
      <table>
        <thead>
          <tr><th v-for="c in page.columns" :key="c.name" :class="c.type === 'number' ? 'num' : ''" :title="c.about || c.name">{{ c.name }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="(row, r) in page.rows" :key="r">
            <td v-for="(value, i) in row" :key="i" :class="[page.columns[i].type === 'number' ? 'num' : '', { empty: value === null || value === '' }]">{{ show(value, page.columns[i]) }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="!page.rows.length" class="hint pad">This table has no rows for the chosen participant and trial.</p>
    </div>
    <footer class="pager">
      <span>Rows {{ count(page.total ? page.offset + 1 : 0) }}–{{ count(Math.min(page.total, page.offset + limit)) }} of {{ count(page.total) }}. Empty cells are missing values. Hover a column name to see what it means.</span>
      <button :disabled="page.offset === 0" title="Previous rows" @click="emit('offset', Math.max(0, page.offset - limit))"><ChevronLeft :size="16" /></button>
      <button :disabled="page.offset + limit >= page.total" title="Next rows" @click="emit('offset', page.offset + limit)"><ChevronRight :size="16" /></button>
    </footer>
  </div>
</template>
