// The order and indentation of steps in the pipeline list. The main line of an analysis runs
// straight down; a side branch is listed directly under the step it leaves from, indented.

export function arrange(nodes, edges) {
  const children = Object.fromEntries(nodes.map((n) => [n.id, []]));
  const parent = {};
  for (const edge of edges) {
    if (children[edge.source] && children[edge.target] && !(edge.target in parent)) {
      children[edge.source].push(edge.target);
      parent[edge.target] = edge.source;
    }
  }
  const rows = []; // { id, depth }
  const seen = new Set();
  const visit = (id, depth) => {
    if (seen.has(id)) return; // a loop; the server reports it
    seen.add(id);
    rows.push({ id, depth });
    const [main, ...sides] = children[id];
    for (const side of sides) visit(side, depth + 1);
    if (main) visit(main, depth);
  };
  for (const node of nodes) if (!(node.id in parent)) visit(node.id, 0);
  for (const node of nodes) visit(node.id, 0);
  return { rows, order: rows.map((r) => r.id), parent, children };
}

export function ancestors(parent, id) {
  const chain = [];
  for (let at = parent[id]; at && !chain.includes(at); at = parent[at]) chain.push(at);
  return chain;
}
