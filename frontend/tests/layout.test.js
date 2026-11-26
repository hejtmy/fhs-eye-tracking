import { test } from "node:test";
import assert from "node:assert/strict";
import { ancestors, arrange } from "../src/layout.js";

const nodes = ["load", "clean", "ivt", "aoi", "idt", "summary"].map((id) => ({ id }));
const edges = [["load", "clean"], ["clean", "ivt"], ["ivt", "aoi"], ["clean", "idt"], ["idt", "summary"]].map(([source, target]) => ({ source, target }));

test("the main line runs straight down and side branches are listed under the step they leave", () => {
  const { rows, parent } = arrange(nodes, edges);
  assert.deepEqual(rows, [
    { id: "load", depth: 0 }, { id: "clean", depth: 0 }, { id: "idt", depth: 1 }, { id: "summary", depth: 1 }, { id: "ivt", depth: 0 }, { id: "aoi", depth: 0 },
  ]);
  assert.deepEqual(ancestors(parent, "summary"), ["idt", "clean", "load"]);
});

test("unconnected steps and loops are still listed once", () => {
  const { rows } = arrange([...nodes, { id: "alone" }], [...edges, { source: "aoi", target: "load" }]);
  assert.equal(rows.length, 7);
  assert.equal(new Set(rows.map((r) => r.id)).size, 7);
});
