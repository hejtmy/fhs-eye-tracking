<script setup>
// Draws a figure description from the server with Plotly, in the app's own typography and colours.
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({ figure: Object, name: { type: String, default: "figure" } });
const emit = defineEmits(["zoom"]);
const el = ref(null);
const FONT = '"IBM Plex Sans", system-ui, sans-serif';
let Plotly = null, drawing = false, observer = null;

function themed(layout) {
  const out = { ...layout, font: { family: FONT, size: 12, color: "#16202b" }, paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "#ffffff",
    margin: { l: 64, r: 18, t: 40, b: 46 }, uirevision: props.name, hoverlabel: { font: { family: FONT, size: 12 }, bgcolor: "#ffffff", bordercolor: "#dde2e8" } };
  for (const key of Object.keys(out))
    if (/^[xy]axis\d*$/.test(key))
      out[key] = { gridcolor: "#eef1f4", linecolor: "#dde2e8", zerolinecolor: "#dde2e8", ticks: "outside", tickcolor: "#dde2e8", ticklen: 4, automargin: true, ...out[key],
        title: { font: { size: 12, color: "#4a5868" }, standoff: 8, ...(out[key].title || {}) } };
  return out;
}

async function draw() {
  if (!props.figure || !el.value) return;
  Plotly ||= (await import("plotly.js-cartesian-dist-min")).default;
  if (!el.value) return;
  drawing = true;
  const first = !el.value.data;
  await Plotly.react(el.value, props.figure.data, themed(props.figure.layout), { responsive: true, displaylogo: false,
    modeBarButtonsToRemove: ["select2d", "lasso2d", "autoScale2d", "toImage"], doubleClick: "reset" });
  drawing = false;
  if (first) el.value.on("plotly_relayout", relayout);
}

// Long recordings arrive thinned; when the person zooms, ask for that stretch in full detail.
function relayout(event) {
  if (drawing || !props.figure?.info?.zoomable) return;
  if (event["xaxis.range[0]"] !== undefined) emit("zoom", [event["xaxis.range[0]"], event["xaxis.range[1]"]]);
  else if (event["xaxis.autorange"] || event["xaxis.range"] === undefined && event["xaxis.showspikes"] === undefined && Object.keys(event).some((k) => k.startsWith("xaxis"))) emit("zoom", null);
}

function savePng() {
  Plotly?.downloadImage(el.value, { format: "png", scale: 2, filename: props.name, width: el.value.clientWidth, height: el.value.clientHeight });
}
defineExpose({ savePng });

onMounted(() => {
  draw();
  observer = new ResizeObserver(() => Plotly && el.value?.data && Plotly.Plots.resize(el.value));
  observer.observe(el.value);
});
watch(() => props.figure, draw);
onBeforeUnmount(() => {
  observer?.disconnect();
  if (Plotly && el.value) Plotly.purge(el.value);
});
</script>

<template>
  <div ref="el" class="plot"></div>
</template>
