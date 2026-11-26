// Every call to the server goes through here. Errors become Error objects with the server's own wording.

async function parse(response) {
  if (response.ok) return response;
  let message = `The server answered ${response.status}.`;
  try {
    const body = await response.json();
    if (typeof body.detail === "string") message = body.detail;
    else if (Array.isArray(body.detail)) message = body.detail.map((d) => d.msg).join(" ");
  } catch {
    /* keep the generic message */
  }
  throw new Error(message);
}

const send = (method) => async (path, body) =>
  (await parse(await fetch(`/api/${path}`, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body && JSON.stringify(body) }))).json();

export const get = send("GET");
export const post = send("POST");
export const patch = send("PATCH");
export const del = send("DELETE");

export async function upload(path, files) {
  const form = new FormData();
  for (const file of files) form.append("files", file, file.name);
  return (await parse(await fetch(`/api/${path}`, { method: "POST", body: form }))).json();
}

// Ask the server for a file and hand it to the browser as a download.
export async function download(path, body, fallbackName) {
  const response = await parse(await fetch(`/api/${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }));
  const name = /filename="([^"]+)"/.exec(response.headers.get("Content-Disposition") || "")?.[1] || fallbackName;
  saveBlob(await response.blob(), name);
}

export function saveBlob(blob, name) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}
