import { qs, el, getJSON, fmtNum, fmtDuration, fmtCost, showMessage, badge, runDir } from "./common.js";

const slug = qs("p");
const main = document.getElementById("main");

const COLUMNS = [
  { key: "model", label: "Model", get: (r) => r.model, num: false,
    help: "The model that ran the task (provider/model)." },
  { key: "effort", label: "Effort", get: (r) => r.effort, num: false,
    help: "Reasoning effort the model was run at (low / medium / high). Higher effort lets it think longer before acting." },
  { key: "verified", label: "Verified", get: (r) => r.verified, num: false,
    help: "Whether the exported web build booted in headless Chrome: a WebGL canvas rendered, two screenshots differed (it animates), and no console or page errors. – means no check was recorded." },
  { key: "duration_ms", label: "Duration", get: (r) => r.metrics.duration_ms, num: true, fmt: fmtDuration,
    help: "Wall-clock time of the agent session, from start to finish." },
  { key: "tokens_total", label: "Tokens", get: (r) => r.metrics.tokens_total, num: true, fmt: fmtNum,
    help: "Input + output tokens reported by the provider. Excludes input served from the prompt cache." },
  { key: "tokens_output", label: "Output tok", get: (r) => r.metrics.tokens_output, num: true, fmt: fmtNum,
    help: "Tokens the model generated: messages, tool-call arguments and file contents it wrote. Includes reasoning tokens when the provider counts them as output (OpenAI does)." },
  { key: "tokens_reasoning", label: "Reasoning tok", get: (r) => r.metrics.tokens_reasoning, num: true, fmt: fmtNum,
    help: "Tokens spent on hidden internal reasoning (thinking) before answering. Not shown in the transcript beyond short summaries, but billed as output." },
  { key: "cost_usd", label: "Cost", get: (r) => r.metrics.cost_usd, num: true, fmt: fmtCost,
    help: "Cost in USD for the whole session as reported by the provider, including cached input at its discounted rate." },
  { key: "tool_calls", label: "Tool calls", get: (r) => r.metrics.tool_calls, num: true, fmt: fmtNum,
    help: "Number of tools the agent invoked (bash, read, write, edit, ls, …)." },
  { key: "turns", label: "Turns", get: (r) => r.metrics.turns, num: true, fmt: fmtNum,
    help: "Number of model responses in the session. Each turn can make tool calls; the last one is usually the final answer." },
];

if (!slug) {
  showMessage(main, "Missing ?p=<slug> – pick a page from the home page.", "error");
} else {
  try {
    const [page, runs] = await Promise.all([
      getJSON(`data/${slug}/page.json`),
      getJSON(`data/${slug}/results.json`),
    ]);
    render(page, runs);
  } catch (err) {
    showMessage(main, `Could not load page "${slug}": ${err.message}`, "error");
  }
}

function render(page, runs) {
  document.title = `${page.title} – llm-bench`;
  document.getElementById("title").textContent = page.title;
  if (page.prompt) {
    document.getElementById("prompt").textContent = page.prompt;
    document.getElementById("prompt-box").hidden = false;
  }

  const selected = new Set();
  const compareBtn = document.getElementById("compare-btn");
  compareBtn.addEventListener("click", () => {
    if (!selected.size) return;
    location.href = `compare.html?p=${encodeURIComponent(slug)}&r=${[...selected].join(",")}`;
  });

  let sortKey = "duration_ms";
  let sortDir = 1;
  const table = document.getElementById("runs-table");
  const thead = table.querySelector("thead");
  const tbody = table.querySelector("tbody");

  const headRow = el("tr", {}, [
    el("th", { attrs: { title: "Select runs, then press Compare selected to view them side by side." } }),
    el("th", { attrs: { title: "Screenshot of the running game taken during verification. Click to open the run." } }),
    ...COLUMNS.map((c) =>
      el("th", { text: c.label, class: "has-help", attrs: { "data-key": c.key, title: `${c.help}\n\nClick to sort.` }, on: { click: () => sortBy(c.key) } })
    ),
  ]);
  thead.append(headRow);

  function sortBy(key) {
    sortDir = key === sortKey ? -sortDir : 1;
    sortKey = key;
    drawTable();
  }

  function drawTable() {
    for (const th of headRow.querySelectorAll("th[data-key]")) {
      th.removeAttribute("aria-sort");
      if (th.dataset.key === sortKey) th.setAttribute("aria-sort", sortDir === 1 ? "ascending" : "descending");
    }
    const col = COLUMNS.find((c) => c.key === sortKey);
    const rows = [...runs].sort((a, b) => {
      const va = col.get(a);
      const vb = col.get(b);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (va < vb) return -1 * sortDir;
      if (va > vb) return 1 * sortDir;
      return 0;
    });

    const maxes = {};
    for (const c of COLUMNS) if (c.num) maxes[c.key] = Math.max(1, ...runs.map((r) => c.get(r) || 0));

    tbody.replaceChildren();
    for (const r of rows) {
      const cb = el("input", { attrs: { type: "checkbox" } });
      cb.checked = selected.has(r.id);
      cb.addEventListener("change", () => {
        if (cb.checked) selected.add(r.id);
        else selected.delete(r.id);
        compareBtn.disabled = selected.size === 0;
      });
      const runUrl = `run.html?p=${encodeURIComponent(slug)}&r=${encodeURIComponent(r.id)}`;
      const thumb = r.thumb
        ? el("a", { attrs: { href: runUrl } }, [el("img", { class: "row-thumb", attrs: { src: runDir(slug, r.id) + r.thumb, alt: "", loading: "lazy" } })])
        : el("span", { class: "muted", text: "–" });
      const tds = [el("td", {}, [cb]), el("td", { class: "thumb-cell" }, [thumb])];
      for (const c of COLUMNS) {
        const v = c.get(r);
        if (c.key === "model") {
          tds.push(el("td", {}, [el("a", { text: v, attrs: { href: runUrl } })]));
        } else if (c.key === "verified") {
          tds.push(el("td", {}, [v === true ? badge("✓", "good") : v === false ? badge("✗", "bad") : el("span", { class: "muted", text: "–" })]));
        } else if (c.num) {
          const pct = Math.max(0, Math.min(100, ((v || 0) / maxes[c.key]) * 100));
          tds.push(
            el("td", {}, [
              el("div", { class: "bar-cell" }, [
                el("span", { class: "bar", attrs: { style: `width:${pct}%` } }),
                el("span", { class: "val", text: c.fmt ? c.fmt(v) : v ?? "–" }),
              ]),
            ])
          );
        } else {
          tds.push(el("td", { text: v ?? "–" }));
        }
      }
      tbody.append(el("tr", {}, tds));
    }
  }
  drawTable();
}
