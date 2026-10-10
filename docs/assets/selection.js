// The runs ticked for a side-by-side compare. Kept per page in sessionStorage, so the selection survives switching
// views, changing filters and reloading; ids of runs that no longer exist are dropped.

import { el } from "./dom.js";

export function createSelection(slug, validIds) {
  const key = `bench.selected.${slug}`;
  let ids = new Set();
  try {
    ids = new Set((JSON.parse(sessionStorage.getItem(key)) ?? []).filter((id) => validIds.includes(id)));
  } catch {} // storage blocked or unreadable: start empty
  const changed = () => {
    try { sessionStorage.setItem(key, JSON.stringify([...ids])); } catch {}
    selection.onChange?.();
  };
  const selection = {
    onChange: null,
    has: (id) => ids.has(id),
    get ids() { return [...ids]; },
    set(id, on) {
      if (on) ids.add(id);
      else ids.delete(id);
      changed();
    },
    clear() {
      ids.clear();
      changed();
    },
  };
  return selection;
}

// The checkbox of one run, in a table row or on a card. It never expands the row or follows a link.
export function selectBox(run, selection) {
  const box = el("input", {
    class: "run-select",
    attrs: { type: "checkbox", "data-id": run.id, "aria-label": `Select ${run.model} ${run.effort} to compare` },
    on: { click: (e) => e.stopPropagation(), change: (e) => selection.set(run.id, e.target.checked) },
  });
  box.checked = selection.has(run.id);
  return box;
}
