import { qsList, qs, el, getJSON, getText, fmtDuration, fmtCost, fmtNum, showMessage, badge, runDir, buildGameFrame } from "./common.js";
import { summarizeToolCalls } from "./transcript.js";

const slug = qs("p");
const ids = qsList("r");
const main = document.getElementById("main");
const columnsEl = document.getElementById("columns");
const pickerEl = document.getElementById("file-picker");

if (!slug || ids.length < 1) {
  showMessage(main, "Missing ?p=<slug>&r=<id>,<id>[,<id>] in the URL.", "error");
} else {
  try {
    const page = await getJSON(`data/${slug}/page.json`).catch(() => null);
    if (page) {
      const link = document.getElementById("page-link");
      link.textContent = page.title;
      link.href = `page.html?p=${encodeURIComponent(slug)}`;
      document.getElementById("title").textContent = `Compare – ${page.title}`;
    }
    const runs = await Promise.all(
      ids.map(async (id) => {
        try {
          return await getJSON(`${runDir(slug, id)}run.json`);
        } catch {
          return { id, missing: true };
        }
      })
    );
    render(runs);
  } catch (err) {
    showMessage(main, `Could not load comparison: ${err.message}`, "error");
  }
}

async function render(runs) {
  const fileNames = new Set();
  for (const r of runs) if (r.source && r.source.files) for (const f of r.source.files) fileNames.add(f);

  const sourceViews = new Map();
  for (const r of runs) {
    if (r.missing) {
      columnsEl.append(el("div", { class: "compare-col" }, [el("h3", { text: r.id }), showMsgFragment("Run not found.")]));
      continue;
    }
    const base = runDir(slug, r.id);
    const col = el("div", { class: "compare-col" });
    col.append(el("h3", { text: `${r.model} · ${r.effort}` }));
    col.append(
      el("div", { class: "muted", text: `${fmtDuration(r.metrics?.duration_ms)} · ${fmtCost(r.metrics?.cost_usd)} · ${fmtNum(r.metrics?.tokens_total)} tok` })
    );

    if (r.game) {
      col.append(buildGameFrame(base + r.game.entry, r.thumb ? base + r.thumb : null));
    } else {
      col.append(el("p", { class: "muted", text: "No game recorded." }));
    }

    col.append(el("h2", { text: "Tool calls" }));
    const toolList = el("ul", { class: "tool-summary-list" });
    col.append(toolList);
    if (r.session && r.session.conversation) {
      getJSON(base + r.session.conversation)
        .then((conv) => {
          const calls = summarizeToolCalls(conv);
          if (!calls.length) {
            toolList.append(el("li", { class: "muted", text: "(no tool calls)" }));
          } else {
            for (const c of calls) {
              toolList.append(el("li", {}, [c.isError ? badge("✗", "bad") : badge("✓", "good"), el("span", { text: c.name })]));
            }
          }
        })
        .catch(() => toolList.append(el("li", { class: "muted", text: "(transcript unavailable)" })));
    } else {
      toolList.append(el("li", { class: "muted", text: "(no transcript)" }));
    }

    col.append(el("h2", { text: "Source" }));
    const view = el("pre", { text: "Pick a file above." });
    col.append(view);
    sourceViews.set(r.id, { run: r, base, view });

    columnsEl.append(col);
  }

  if (fileNames.size) {
    for (const name of [...fileNames].sort()) {
      const btn = el("button", { class: "chip", text: name, attrs: { type: "button" } });
      btn.addEventListener("click", async () => {
        for (const b of pickerEl.children) b.classList.remove("chip-active");
        btn.classList.add("chip-active");
        for (const { run, base, view } of sourceViews.values()) {
          if (run.source && run.source.files && run.source.files.includes(name)) {
            try {
              view.textContent = await getText(base + run.source.root + name);
            } catch (err) {
              view.textContent = `Could not load: ${err.message}`;
            }
          } else {
            view.textContent = "(not present in this run)";
          }
        }
      });
      pickerEl.append(btn);
    }
  }
}

function showMsgFragment(text) {
  return el("p", { class: "msg msg-error", text });
}
