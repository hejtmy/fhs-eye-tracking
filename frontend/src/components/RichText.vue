<script setup>
// Just enough formatting for step explanations: paragraphs, bullet lists, **bold**, *italic*, `code`.
import { computed } from "vue";

const props = defineProps({ text: { type: String, default: "" }, firstOnly: Boolean });

const inline = (text) =>
  text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");

const html = computed(() => {
  const blocks = props.text.trim().split(/\n\s*\n/);
  const lead = blocks[0].trim().endsWith(":") ? 2 : 1; // an opening line that introduces a list is shown with its list
  return (props.firstOnly ? blocks.slice(0, lead) : blocks)
    .map((block) => {
      const lines = block.split("\n").map((l) => l.trim());
      if (lines.every((l) => l.startsWith("- "))) return `<ul>${lines.map((l) => `<li>${inline(l.slice(2))}</li>`).join("")}</ul>`;
      return `<p>${inline(lines.join(" "))}</p>`;
    })
    .join("");
});
</script>

<template>
  <div class="rich" v-html="html"></div>
</template>
