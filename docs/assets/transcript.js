// Renders a session `conversation.json` array as a chat-like transcript,
// pairing toolCall blocks with their toolResult by toolCallId, and (when
// available) tool durations from `events.jsonl`.

import { el, fmtElapsed, fmtNum, fmtDuration, renderMarkdown, badge } from "./common.js";

export function parseEvents(text) {
  const starts = new Map();
  const spans = new Map();
  if (!text) return spans;
  for (const line of text.split("\n")) {
    if (!line.trim()) continue;
    let e;
    try {
      e = JSON.parse(line);
    } catch {
      continue;
    }
    if (e.type === "tool_execution_start" && e.toolCallId) {
      starts.set(e.toolCallId, e.observedAt);
    } else if (e.type === "tool_execution_end" && e.toolCallId && starts.has(e.toolCallId)) {
      spans.set(e.toolCallId, { startMs: starts.get(e.toolCallId), endMs: e.observedAt });
    }
  }
  return spans;
}

function roleLabel(role) {
  return { system: "System", user: "User", assistant: "Assistant" }[role] || role;
}

function blocksToText(content) {
  if (content == null) return "";
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content.map((b) => (b.type === "text" ? b.text : JSON.stringify(b))).join("\n\n");
  }
  return JSON.stringify(content);
}

function systemText(message) {
  if (typeof message.content === "string" && message.content) return message.content;
  if (message.sections && typeof message.sections === "object") {
    return Object.values(message.sections).filter(Boolean).join("\n\n");
  }
  return "(empty system prompt)";
}

function argLine(args) {
  if (!args || typeof args !== "object") return "";
  return Object.entries(args)
    .map(([k, v]) => `${k}: ${typeof v === "string" ? v : JSON.stringify(v)}`)
    .join("\n");
}

function renderOutput(text, isError) {
  const body = text == null ? "" : String(text);
  const lines = body.split("\n");
  const pre = el("pre", { class: isError ? "out out-error" : "out", text: body });
  if (lines.length > 20) {
    return el("details", { class: "out-collapse" }, [
      el("summary", { text: `Output (${lines.length} lines)` }),
      pre,
    ]);
  }
  return pre;
}

function resultText(resultMsg) {
  if (!resultMsg) return "(no result recorded)";
  const content = resultMsg.content;
  if (Array.isArray(content)) return content.map((c) => c.text ?? JSON.stringify(c)).join("\n");
  return String(content ?? "");
}

function renderToolBlock(block, resultMsg, span) {
  const isError = !!(resultMsg && resultMsg.isError);
  const head = el("div", { class: "tool-head" }, [el("span", { class: "tool-name", text: block.name })]);
  if (span) head.append(el("span", { class: "tool-duration", text: fmtDuration(Math.max(0, span.endMs - span.startMs)) }));
  if (isError) head.append(badge("✗ error", "error"));
  const wrap = el("div", { class: "tool-block" }, [head]);
  const args = block.arguments || {};

  if (block.name === "bash") {
    wrap.append(el("pre", { class: "cmd", text: `$ ${args.command ?? ""}` }));
    wrap.append(renderOutput(resultText(resultMsg), isError));
  } else if (block.name === "write") {
    wrap.append(el("div", { class: "tool-path", text: args.path ?? "" }));
    wrap.append(el("pre", { class: "code", text: args.content ?? "" }));
  } else if (block.name === "edit") {
    wrap.append(el("div", { class: "tool-path", text: args.path ?? "" }));
    const edits = Array.isArray(args.edits) ? args.edits : [{ oldText: args.oldText, newText: args.newText }];
    for (const e of edits) {
      wrap.append(el("pre", { class: "code diff-old", text: `- ${e.oldText ?? ""}` }));
      wrap.append(el("pre", { class: "code diff-new", text: `+ ${e.newText ?? ""}` }));
    }
  } else if (block.name === "read" || block.name === "ls") {
    const line = argLine(args);
    if (line) wrap.append(el("pre", { class: "tool-args", text: line }));
    wrap.append(renderOutput(resultText(resultMsg), isError));
  } else {
    wrap.append(el("pre", { class: "tool-args", text: JSON.stringify(args, null, 2) }));
    wrap.append(renderOutput(resultText(resultMsg), isError));
  }
  return wrap;
}

/** Builds toolbar (filters + show-thinking) and the transcript into `root`. */
export async function renderTranscript(root, conversation, eventsText) {
  root.replaceChildren();
  const toolbar = el("div", { class: "transcript-toolbar" });
  const list = el("div", { class: "transcript" });
  list.dataset.filter = "all";
  list.dataset.showThinking = "false";

  const filterBtns = [["all", "All"], ["tools", "Tool calls"], ["errors", "Errors"]].map(([key, label]) =>
    el("button", { class: key === "all" ? "chip chip-active" : "chip", text: label, attrs: { type: "button", "data-filter-btn": key },
      on: { click: () => {
        list.dataset.filter = key;
        for (const b of toolbar.querySelectorAll("[data-filter-btn]")) b.classList.toggle("chip-active", b.dataset.filterBtn === key);
      } },
    })
  );
  const thinkToggle = el("button", { class: "chip", text: "Show thinking", attrs: { type: "button" },
    on: { click: () => {
      const shown = list.dataset.showThinking === "true";
      list.dataset.showThinking = shown ? "false" : "true";
      thinkToggle.classList.toggle("chip-active", !shown);
    } },
  });
  toolbar.append(...filterBtns, el("span", { class: "sep", attrs: { "aria-hidden": "true" } }), thinkToggle);
  root.append(toolbar);

  const messages = conversation.filter((e) => e.type === "message");
  const toolResults = new Map();
  for (const m of messages) if (m.message.role === "toolResult") toolResults.set(m.message.toolCallId, m.message);
  const events = parseEvents(eventsText);
  const sessionStartMs = Date.parse(conversation[0]?.timestamp ?? messages[0]?.timestamp);

  for (const m of messages) {
    const role = m.message.role;
    if (role === "toolResult") continue;
    const turn = el("div", { class: `turn turn-${role}` });
    const elapsedMs = Date.parse(m.timestamp) - sessionStartMs;
    const head = el("div", { class: "turn-head" }, [el("span", { class: "role-badge", text: roleLabel(role) })]);
    const elapsed = fmtElapsed(elapsedMs);
    if (elapsed) head.append(el("span", { class: "elapsed", text: elapsed }));
    if (m.message.usage) head.append(el("span", { class: "usage", text: `${fmtNum(m.message.usage.totalTokens)} tok` }));
    turn.append(head);

    if (role === "system") {
      const details = el("details", { class: "system-block" }, [el("summary", { text: "System prompt" })]);
      details.append(el("div", { class: "content-plain", text: systemText(m.message) }));
      turn.append(details);
    } else if (role === "user") {
      turn.append(el("div", { class: "content-plain", text: blocksToText(m.message.content) }));
    } else if (role === "assistant") {
      let hasTool = false;
      let hasError = false;
      for (const block of m.message.content || []) {
        if (block.type === "thinking") {
          turn.append(el("div", { class: "thinking-block", text: block.thinking }));
        } else if (block.type === "text") {
          const div = el("div", { class: "content-md" });
          await renderMarkdown(div, block.text);
          turn.append(div);
        } else if (block.type === "toolCall") {
          hasTool = true;
          const resultMsg = toolResults.get(block.id);
          if (resultMsg && resultMsg.isError) hasError = true;
          turn.append(renderToolBlock(block, resultMsg, events.get(block.id)));
        }
      }
      if (hasTool) turn.dataset.hasTool = "1";
      if (hasError) turn.dataset.hasError = "1";
    }
    list.append(turn);
  }
  root.append(list); // all at once, after every message has rendered (markdown loads async)
  return list;
}
