// Column help for the runs table (page.js): shown as a tooltip after a short hover, so the table code reads as code.
export const COLUMN_HELP = {
  rank: "The page owner's own ranking of the runs (🥇🥈🥉, then #4, #5…; ties allowed). – means not ranked.",
  model: "The model that ran the task (provider/model).",
  effort: "Reasoning effort the model was run at (minimal / low / medium / high / xhigh / max; the bars show the level). Higher effort lets it think longer before acting. Level names are the harness's; the same name can mean different budgets at different providers.",
  harness: "The agent program that ran the model and executed its tool calls (pi or claude-code), with its version. Every run is one direct agent with only file and shell tools.",
  started_at: "When the agent session started, in your local time. Click to sort.",
  verified: "Game pages: whether the exported web build booted in headless Chrome (a WebGL canvas rendered, two screenshots differed, no page errors). Web pages: whether the packaged page loaded offline in a sandboxed iframe with no page errors and no network requests. Media pages: whether every output file was a readable image or video within the limits. – means no check was recorded.",
  duration_ms: "Wall-clock time of the agent session, from start to finish. ★ marks the fastest completed run.",
  tokens_total: "Input + output tokens reported by the provider. Excludes input served from the prompt cache. ★ marks the completed run that used the fewest.",
  tokens_reasoning: "Tokens spent on hidden internal reasoning (thinking) before answering. Not shown in the transcript beyond short summaries, but billed as output.",
  cost_usd: "Cost in USD for the whole session as reported by the provider, including cached input at its discounted rate. For Claude Code runs it's Claude Code's own estimate at API prices (also when run on a subscription). ★ marks the cheapest completed run.",
  tool_calls: "Number of tools the agent invoked (bash, read, write, edit, ls, …).",
};

// The two unlabeled leading columns' help depends on the page's kind.
export function rowHelp(isMedia) {
  return {
    expand: isMedia ? "Click a row to expand it and see that run's output files." : "Click a row to expand it and play that run's game inline.",
    thumb: isMedia ? "The run's first output (a video shows its poster frame). Click to open the run." : "Screenshot of the running game taken during verification. Click to open the run.",
  };
}
