<script setup>
// The “Recording” setting of the Load step: choose or upload a dataset, see how it was read, map its columns.
import { computed, ref, watch } from "vue";
import { FilePlus2, Image, Trash2, Upload, X } from "lucide-vue-next";
import { del, patch, post, upload } from "../api.js";
import { datasetInfo, forgetUpload, rememberUpload, state } from "../store.js";
import ParamForm from "./ParamForm.vue";

const props = defineProps({ param: Object, value: Object, values: Object, nodeId: String });
const emit = defineEmits(["change"]);

const source = computed(() => props.value || { dataset: "", reader: "auto", options: {}, mapping: {}, extra: [] });
const dataset = ref(null);
const probe = ref(null);
const busy = ref("");
const problem = ref("");
const dragging = ref(false);
const filePicker = ref(null), morePicker = ref(null), imagePicker = ref(null);
const reader = computed(() => state.catalog.readers.find((r) => r.id === probe.value?.reader));
const columnNames = computed(() => (probe.value?.columns || []).map((c) => c.name));

async function attempt(label, work) {
  busy.value = label;
  problem.value = "";
  try {
    return await work();
  } catch (error) {
    problem.value = error.message;
  } finally {
    busy.value = "";
  }
}

// Read the first file and, when asked, take over the suggested mapping and settings.
async function inspect(id, readerId, options, adopt) {
  await attempt("Reading the file…", async () => {
    dataset.value = await datasetInfo(id, true);
    if (!dataset.value.files.length) return (probe.value = null);
    probe.value = await post(`datasets/${id}/probe`, { reader: readerId, options });
    if (adopt) {
      const s = probe.value.suggestion;
      emit("change", { ...s.params, source: { dataset: id, reader: readerId, options: probe.value.options, mapping: s.mapping, extra: s.extra } });
    }
  });
}

watch(() => source.value.dataset, (id) => {
  dataset.value = probe.value = null;
  if (id) inspect(id, source.value.reader, source.value.options, !Object.keys(source.value.mapping || {}).length);
}, { immediate: true });

const choose = (id) => (id ? inspect(id, "auto", {}, true) : emit("change", { source: { ...source.value, dataset: "" } }));
const setSource = (changes) => emit("change", { source: { ...source.value, ...changes } });

// Images dropped together with recordings (e.g. a WebGazer workbook and its stimuli) become stimulus images.
const isImage = (file) => /\.(png|jpe?g|webp)$/i.test(file.name);
const RECORDINGS = ".csv,.tsv,.txt,.dat,.asc,.json,.gz,.xlsx";
const isRecording = (file) => RECORDINGS.split(",").some((end) => file.name.toLowerCase().endsWith(end));

// What was dropped, with folders opened (a WebGazer folder holds the workbook and its images). Hidden files such as .DS_Store are left out.
async function droppedFiles(transfer) {
  const entries = [...transfer.items].map((item) => item.webkitGetAsEntry?.()).filter(Boolean); // read now: the drop data is gone after the first await
  if (!entries.length) return [...transfer.files];
  const files = [];
  async function walk(entry) {
    if (entry.name.startsWith(".")) return;
    if (entry.isFile) return files.push(await new Promise((done, fail) => entry.file(done, fail)));
    const reader = entry.createReader();
    for (let batch; (batch = await new Promise((done, fail) => reader.readEntries(done, fail))).length; ) {
      for (const inner of batch) await walk(inner);
    }
  }
  for (const entry of entries) await walk(entry);
  return files;
}
async function dropped(event) {
  dragging.value = false;
  receive(await droppedFiles(event.dataTransfer));
}

async function receive(all) {
  if (!all.length) return;
  const images = all.filter(isImage), recordings = all.filter(isRecording);
  const skipped = all.filter((f) => !isImage(f) && !isRecording(f)).map((f) => f.name);
  if (!recordings.length) {
    return (problem.value = images.length ? "These are only images. Upload the recording first, then add the images to it."
      : `None of these is a recording this app can read (${skipped.join(", ")}). Use CSV/TSV/text, EyeLink .asc, Tobii livedata.json(.gz) or a WebGazer .xlsx.`);
  }
  const created = await attempt("Uploading…", () => upload("datasets", recordings));
  if (created) {
    rememberUpload(created);
    const pictured = images.length && (await attempt("Uploading images…", () => upload(`datasets/${created.id}/stimuli`, images)));
    if (pictured) rememberUpload(pictured);
    await inspect(created.id, "auto", {}, true);
    if (skipped.length && !problem.value) problem.value = `Left out, as neither a recording nor an image: ${skipped.join(", ")}.`;
  }
}
async function change(label, work) {
  const updated = await attempt(label, work);
  if (updated) {
    rememberUpload(updated);
    await inspect(updated.id, source.value.reader, source.value.options, false);
    setSource({}); // the files changed: run again
  }
}
const id = () => source.value.dataset;
const addFiles = (files) => files.length && change("Uploading…", async () => {
  const images = files.filter(isImage), recordings = files.filter((f) => !isImage(f));
  const added = recordings.length ? await upload(`datasets/${id()}/files`, recordings) : null;
  return images.length ? upload(`datasets/${id()}/stimuli`, images) : added;
});
const addImages = (files) => files.length && change("Uploading…", () => upload(`datasets/${id()}/stimuli`, files));
const rename = (file, label) => label.trim() && label !== file.label && change("Renaming…", () => patch(`datasets/${id()}/files/${encodeURIComponent(file.name)}`, { label }));
const removeFile = (file) => change("Removing…", () => del(`datasets/${id()}/files/${encodeURIComponent(file.name)}`));
const removeImage = (name) => change("Removing…", () => del(`datasets/${id()}/stimuli/${encodeURIComponent(name)}`));

async function removeDataset() {
  await attempt("Removing…", () => del(`datasets/${id()}`));
  forgetUpload(id());
  emit("change", { source: { dataset: "", reader: "auto", options: {}, mapping: {}, extra: [] } });
}
function toggleExtra(name) {
  const extra = source.value.extra || [];
  setSource({ extra: extra.includes(name) ? extra.filter((c) => c !== name) : [...extra, name] });
}
const picked = (event, handler) => {
  handler([...event.target.files]);
  event.target.value = "";
};
</script>

<template>
  <div class="source">
    <div class="field">
      <label :for="nodeId + 'dataset'">Recording</label>
      <select :id="nodeId + 'dataset'" :value="source.dataset" @change="choose($event.target.value)">
        <option value="">Choose…</option>
        <optgroup label="Examples (simulated)">
          <option v-for="d in state.catalog.examples.datasets" :key="d.id" :value="d.id">{{ d.name }}</option>
        </optgroup>
        <optgroup v-if="state.uploads.length" label="Your uploads">
          <option v-for="d in state.uploads" :key="d.id" :value="d.id">{{ d.name }}</option>
        </optgroup>
      </select>
    </div>
    <button
      class="dropzone" :class="{ over: dragging }" @click="filePicker.click()" @dragover.prevent="dragging = true" @dragleave="dragging = false"
      @drop.prevent="dropped"
    >
      <Upload :size="18" />
      <span><strong>Upload your own files</strong>Drop them here or click. One file per participant, plus the stimulus images if you have them (a whole folder works too); up to {{ state.catalog.limits.upload_mb }} MB.</span>
    </button>
    <input ref="filePicker" type="file" multiple hidden :accept="`${RECORDINGS},image/png,image/jpeg,image/webp`" @change="picked($event, receive)" />
    <p v-if="busy" class="source-status">{{ busy }}</p>
    <p v-if="problem" class="alert" role="alert">{{ problem }}</p>

    <template v-if="dataset">
      <p v-if="dataset.description" class="source-about">{{ dataset.description }}</p>
      <div class="files">
        <div v-for="file in dataset.files" :key="file.name" class="file">
          <input v-if="!dataset.example" :value="file.label" :aria-label="`Participant label for ${file.name}`" title="Used as the participant's name" @change="rename(file, $event.target.value)" />
          <strong v-else>{{ file.label }}</strong>
          <span :title="file.name">{{ file.name }}</span>
          <button v-if="!dataset.example" class="icon" :title="`Remove ${file.name}`" @click="removeFile(file)"><Trash2 :size="14" /></button>
        </div>
      </div>
      <p v-if="dataset.stimuli.length" class="images">
        <Image :size="14" />{{ dataset.stimuli.length }} stimulus image{{ dataset.stimuli.length > 1 ? "s" : "" }}:
        <span v-for="name in dataset.stimuli" :key="name">{{ name }}<button v-if="!dataset.example" class="icon" :title="`Remove image ${name}`" @click="removeImage(name)"><X :size="12" /></button></span>
      </p>
      <div v-if="!dataset.example" class="file-actions">
        <button class="link" @click="morePicker.click()"><FilePlus2 :size="14" />Add recordings</button>
        <button class="link" title="An image is shown behind the gaze of trials whose stimulus has the same name; a single image is used for all trials" @click="imagePicker.click()"><Image :size="14" />Add stimulus images</button>
        <button class="link danger" @click="removeDataset"><Trash2 :size="14" />Delete upload</button>
        <input ref="morePicker" type="file" multiple hidden :accept="`${RECORDINGS},image/png,image/jpeg,image/webp`" @change="picked($event, addFiles)" />
        <input ref="imagePicker" type="file" multiple hidden accept="image/png,image/jpeg,image/webp" @change="picked($event, addImages)" />
      </div>
      <p v-if="!dataset.example" class="source-about">Uploads stay on this server for {{ Math.round(state.catalog.limits.keep_hours / 24) }} days after their last use and are reachable only through this pipeline.</p>
    </template>

    <template v-if="probe">
      <details class="group" :open="!dataset?.example">
        <summary>File format<span>{{ reader?.title }}</span></summary>
        <div class="field">
          <label :for="nodeId + 'reader'">Read the files as</label>
          <select :id="nodeId + 'reader'" :value="source.reader" @change="inspect(source.dataset, $event.target.value, {}, true)">
            <option value="auto">Detect automatically</option>
            <option v-for="r in state.catalog.readers" :key="r.id" :value="r.id">{{ r.title }}</option>
          </select>
          <small>{{ reader?.about }}</small>
        </div>
        <ParamForm v-if="reader?.options.length" :params="reader.options" :values="probe.options" :node-id="nodeId + 'reader'" @change="inspect(source.dataset, source.reader, { ...probe.options, ...$event }, true)" />
      </details>
      <details class="group" open>
        <summary>Columns<span>{{ probe.columns.length }} in the file</span></summary>
        <div v-for="role in state.catalog.roles" :key="role.id" class="field map">
          <label :for="nodeId + role.id">{{ role.label }}<em v-if="role.required">needed</em></label>
          <select :id="nodeId + role.id" :value="source.mapping[role.id] || ''" :class="{ missing: role.required && !columnNames.includes(source.mapping[role.id]) }" :title="role.help"
                  @change="setSource({ mapping: { ...source.mapping, [role.id]: $event.target.value } })">
            <option value="">{{ role.required ? "Choose a column…" : "None" }}</option>
            <option v-for="c in probe.columns" :key="c.name" :value="c.name">{{ c.name }}{{ c.example ? `  (e.g. ${c.example})` : "" }}</option>
          </select>
        </div>
      </details>
      <details class="group">
        <summary>Extra columns to keep<span>{{ source.extra.length }} kept</span></summary>
        <p class="source-about">Only the columns above are carried through the pipeline. Tick others that later steps need, such as AOI hit columns or the tracker's own eye movement type.</p>
        <div class="picker-list tall">
          <label v-for="c in probe.columns" :key="c.name"><input type="checkbox" :checked="source.extra.includes(c.name)" @change="toggleExtra(c.name)" />{{ c.name }}</label>
        </div>
      </details>
    </template>
  </div>
</template>
