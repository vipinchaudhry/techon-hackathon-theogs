// One place for all backend calls. Base URL comes from an env var so you can
// point the frontend at a different host without editing code.
export const API =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function req(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} — ${text}`);
  }
  return res.json();
}

export const api = {
  health: () => req("/health"),
  reset: () => req("/reset", { method: "POST" }),

  projects: (topOnly = false) =>
    req(`/projects${topOnly ? "?top_level_only=true" : ""}`),
  project: (id) => req(`/projects/${id}`),
  children: (id) => req(`/projects/${id}/children`),
  status: (id) => req(`/projects/${id}/status`),
  rollup: (id) => req(`/projects/${id}/rollup`),
  graph: (id) => req(`/projects/${id}/graph`),
  audit: (id) => req(`/projects/${id}/audit`),

  stakeholders: (id) => req(`/projects/${id}/stakeholders`),
  viewAs: (id, sid) => req(`/projects/${id}/as/${sid}`),

  chat: (message, project_id = null) =>
    req("/chat", { method: "POST", body: JSON.stringify({ message, project_id }) }),

  ask: (message, project_id) =>
    req("/ask", { method: "POST", body: JSON.stringify({ message, project_id }) }),

  chatHistory: (project_id) => req(`/projects/${project_id}/chat`),
  clearChat: (project_id) =>
    req(`/projects/${project_id}/chat`, { method: "DELETE" }),

  analyze: (idea, history = []) =>
    req("/analyze", { method: "POST", body: JSON.stringify({ idea, history }) }),

  addNode: (payload) =>
    req("/projects/add-node", { method: "POST", body: JSON.stringify(payload) }),

  decision: (id, decision, actor = "team", note = "") =>
    req(`/projects/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, actor, note }),
    }),

  compare: (ids) => req(`/compare?ids=${ids.join(",")}`),

  scenarios: () => req("/scenarios"),
  scenario: (key) => req(`/scenarios/${key}`),
  outcome: (key) => req(`/cases/${key}/outcome`),
};
