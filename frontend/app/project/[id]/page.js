"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { Tier, LossProfile, Loading, ErrorBox, DimRow } from "../../../components/ui";
import { IconScale, IconFlag, IconLayers, IconUsers, IconTarget } from "../../../components/icons";
import { PortfolioGraph } from "../../../components/graph";

const fmtEur = (n) => {
  const a = Math.abs(n);
  const s = a >= 1000 ? `€${Math.round(a / 1000)}k` : `€${Math.round(a)}`;
  return n < 0 ? `-${s}` : s;
};

export default function ProjectPage() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [status, setStatus] = useState(null);
  const [children, setChildren] = useState([]);
  const [graph, setGraph] = useState(null);
  const [rollup, setRollup] = useState(null);
  const [audit, setAudit] = useState([]);
  const [asView, setAsView] = useState(null);
  const [error, setError] = useState(null);

  async function load() {
    try {
      const p = await api.project(id);
      setProject(p);
      setStatus(await api.status(id));
      setAudit(await api.audit(id));
      const kids = await api.children(id);
      setChildren(kids);
      if (kids.length > 0) {
        setRollup(await api.rollup(id));
        setGraph(await api.graph(id));
      } else {
        setRollup(null);
        setGraph(null);
      }
    } catch (e) {
      setError(e);
    }
  }
  useEffect(() => {
    load();
  }, [id]);

  async function decide(decision) {
    const actor = asView ? asView.stakeholder.name : "team";
    await api.decision(id, decision, actor, `${decision} logged from project view`);
    load();
  }

  if (error) return <ErrorBox error={error} />;
  if (!project || !status) return <Loading what="Loading project" />;

  const isPortfolio = children.length > 0 && graph;

  return (
    <div>
      <a href="/" className="back-link">← Portfolio</a>
      <div className="page-head">
        <div>
          <h1>{project.name}</h1>
          <p className="sub">{project.description}</p>
        </div>
        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <div className="tiny muted" style={{ marginBottom: 4 }}>Overall risk</div>
          <Tier value={status.overall_tier} />
        </div>
      </div>

      {/* PORTFOLIO / MANAGER VIEW (graph) */}
      {isPortfolio && <PortfolioView projectId={id} graph={graph} children={children} onChanged={load} />}

      {/* SINGLE PROJECT VIEW */}
      {!isPortfolio && (
        <>
          {status.recommit_required && (
            <div className="alert danger">
              <strong>Decision needed before continuing.</strong>
              <ul className="small" style={{ margin: "8px 0 0 18px" }}>
                {status.recommit_reasons.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
              <div className="row" style={{ marginTop: 10 }}>
                <button onClick={() => decide("continue")}>Continue</button>
                <button className="danger" onClick={() => decide("stop")}>Stop</button>
              </div>
            </div>
          )}
          {status.drift_flag && (
            <div className="alert warn">
              <strong>Drifting toward ROI thinking.</strong> {status.drift_reason}
            </div>
          )}
          <div className="alert ok">
            <strong>Suggested next move</strong>
            <div style={{ marginTop: 2 }}>{status.recommended_action}</div>
          </div>

          <div className="grid cols-2">
            <div className="card">
              <div className="row" style={{ marginBottom: 12 }}>
                <div className="chip coral"><IconScale /></div>
                <h3 style={{ margin: 0 }}>What's at stake</h3>
              </div>
              <LossProfile dimensions={status.dimensions} />
              {status.days_to_reevaluation !== null && (
                <p className="small muted" style={{ marginTop: 10 }}>
                  Re-check in {status.days_to_reevaluation} days.
                </p>
              )}
            </div>

            <div className="card">
              <div className="row" style={{ marginBottom: 12 }}>
                <div className="chip blue"><IconFlag /></div>
                <h3 style={{ margin: 0 }}>Next step</h3>
              </div>
              <div className="kv"><span className="k">Hypothesis</span><span>{project.hypothesis || "Not set"}</span></div>
              <div className="kv"><span className="k">Smallest test</span><span>{project.smallest_test || "Not set"}</span></div>
              <div className="kv"><span className="k">Talk to</span><span>{project.contact_person || "Not set"}</span></div>
              <div className="kv"><span className="k">Ask them</span><span>{project.contact_question || "Not set"}</span></div>
              <div className="kv"><span className="k">Keep going if</span><span>{project.signal_keep || "Not set"}</span></div>
              <div className="kv"><span className="k">Stop if</span><span>{project.signal_stop || "Not set"}</span></div>
            </div>
          </div>
        </>
      )}

      {/* Sony: stakeholder switcher */}
      {project.stakeholders?.length > 0 && (
        <StakeholderPanel projectId={id} stakeholders={project.stakeholders} asView={asView} setAsView={setAsView} />
      )}

      {/* Portfolio rollup: show for any project that has sub-projects */}
      {isPortfolio && rollup && (
        <RollupPanel rollup={rollup} children={children} />
      )}

      {/* Ask the AI, with portfolio context */}
      <AskPanel projectId={id} onApplied={load} />

      {/* History */}
      <div className="card" style={{ marginTop: 16 }}>
        <h3>History</h3>
        {audit.length === 0 && <p className="muted small">No entries yet.</p>}
        {audit.map((a) => (
          <div key={a.id} className="audit-item small">
            <span className="muted">{new Date(a.timestamp).toLocaleString()}</span>{" "}
            · <strong>{a.actor}</strong> · {a.action}
            {a.detail ? <span className="muted"> {a.detail}</span> : null}
          </div>
        ))}
      </div>
    </div>
  );
}

function PortfolioView({ projectId, graph, children, onChanged }) {
  const [selected, setSelected] = useState(null);
  const [adding, setAdding] = useState(false);
  const [view, setView] = useState("graph"); // "graph" | "tree"
  const t = graph.totals;
  const center = graph.nodes.find((n) => n.is_center);

  return (
    <>
      <div className="grid cols-4" style={{ marginBottom: 4 }}>
        <div className="card stat">
          <div className="chip blue"><IconLayers /></div>
          <div className="big">{t.node_count}</div>
          <div className="cap">Projects</div>
        </div>
        <div className="card stat">
          <div className="chip green"><IconTarget /></div>
          <div className="big">{t.profit_count}</div>
          <div className="cap">In profit</div>
        </div>
        <div className="card stat">
          <div className="chip coral"><IconTarget /></div>
          <div className="big">{t.loss_count}</div>
          <div className="cap">In loss</div>
        </div>
        <div className="card stat">
          <div className="chip" style={{ background: "#eceef3", color: "#9aa1ac" }}><IconTarget /></div>
          <div className="big">{t.neutral_count ?? 0}</div>
          <div className="cap">No forecast</div>
        </div>
      </div>

      <div className="card graph-wrap" style={{ marginTop: 16 }}>
        <button className="add-btn" title="Add a project" onClick={() => setAdding(true)}>+</button>
        <div className="spread" style={{ marginBottom: 6 }}>
          <div className="row">
            <div className="chip blue"><IconLayers /></div>
            <h3 style={{ margin: 0 }}>Project map</h3>
          </div>
          <div className="pill-row small">
            <span className="pill-row"><Dot c="#34c759" /> profit</span>
            <span className="pill-row"><Dot c="#f15a4a" /> loss</span>
            <span className="pill-row"><Dot c="#c2c7d0" /> no forecast</span>
            <span className="muted">net {fmtEur(t.pnl_eur)}</span>
          </div>
        </div>

        <div className="seg">
          <button className={view === "graph" ? "active" : ""} onClick={() => setView("graph")}>Graph</button>
          <button className={view === "tree" ? "active" : ""} onClick={() => setView("tree")}>Tree</button>
        </div>

        {view === "graph" && (
          <>
            <p className="small muted" style={{ marginTop: 0 }}>
              Each node is a project. Bigger node means more money committed. Click one to see it.
            </p>
            <PortfolioGraph graph={graph} selectedId={selected?.id} onSelect={setSelected} />
          </>
        )}
        {view === "tree" && (
          <PortfolioTree center={center} nodes={graph.nodes} selectedId={selected?.id} onSelect={setSelected} />
        )}

        {selected && !selected.is_center && (
          <div className="card" style={{ background: "var(--panel-2)", marginTop: 8 }}>
            <div className="spread">
              <h3 style={{ margin: 0 }}>{selected.name}</h3>
              {selected.pnl_eur == null ? (
                <span className="badge gray">No forecast yet</span>
              ) : (
                <span className={`badge ${selected.pnl_eur >= 0 ? "Low" : "Critical"}`}>
                  {selected.pnl_eur >= 0 ? "Profit" : "Loss"} {fmtEur(selected.pnl_eur)}
                </span>
              )}
            </div>
            <div className="kv" style={{ marginTop: 8 }}>
              <span className="k">Committed</span><span>{fmtEur(selected.money_committed)}</span>
            </div>
            <div className="kv"><span className="k">Risk</span><span><Tier value={selected.overall_tier} /></span></div>
            <a className="btn secondary" href={`/project/${selected.id}`} style={{ marginTop: 8 }}>
              Open project →
            </a>
          </div>
        )}
      </div>

      {adding && (
        <AddNodeModal
          parentId={Number(projectId)}
          onClose={() => setAdding(false)}
          onAdded={() => { setAdding(false); onChanged && onChanged(); }}
        />
      )}
    </>
  );
}

function AddNodeModal({ parentId, onClose, onAdded }) {
  const [mode, setMode] = useState(null); // null | "budget" | "concern"

  return (
    <div className="modal-back" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>Close</button>
        {!mode && (
          <>
            <h3>Add to the portfolio</h3>
            <p className="small muted">Pick one.</p>
            <button className="opt-card" onClick={() => setMode("budget")}>
              <div className="chip blue"><IconLayers /></div>
              <div>
                <div className="t">Add project and budget</div>
                <div className="d">Name it and set what you can commit. Added as a grey node with no forecast yet.</div>
              </div>
            </button>
            <button className="opt-card" onClick={() => setMode("concern")}>
              <div className="chip coral"><IconScale /></div>
              <div>
                <div className="t">Rectify a concern</div>
                <div className="d">Describe an idea or worry. The AI checks it across the five dimensions and tells you if it is safe to try.</div>
              </div>
            </button>
          </>
        )}
        {mode === "budget" && <BudgetForm parentId={parentId} onAdded={onAdded} onBack={() => setMode(null)} />}
        {mode === "concern" && <ConcernAnalyzer parentId={parentId} onAdded={onAdded} onBack={() => setMode(null)} />}
      </div>
    </div>
  );
}

function BudgetForm({ parentId, onAdded, onBack }) {
  const [name, setName] = useState("");
  const [budget, setBudget] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      await api.addNode({ parent_id: parentId, name: name.trim(), money_committed: Number(budget) || 0 });
      onAdded();
    } catch (e) {
      alert("Could not add: " + e.message);
      setBusy(false);
    }
  }

  return (
    <>
      <a className="back-link" onClick={onBack} style={{ cursor: "pointer" }}>← Back</a>
      <h3>Add project and budget</h3>
      <label className="small muted">Project name</label>
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Cloud backup pilot" />
      <label className="small muted" style={{ marginTop: 10, display: "block" }}>Budget you can commit (EUR)</label>
      <input value={budget} onChange={(e) => setBudget(e.target.value)} placeholder="e.g. 15000" inputMode="numeric" />
      <div className="row" style={{ marginTop: 14 }}>
        <button onClick={submit} disabled={busy || !name.trim()}>{busy ? "Adding..." : "Add node"}</button>
      </div>
      <p className="tiny muted" style={{ marginTop: 10 }}>It joins the map as a grey node. Add a forecast later to turn it green or red.</p>
    </>
  );
}

const REQ_LABELS = { name: "Name", goal: "Goal", budget_eur: "Budget", time_weeks: "Time" };
const REQ_ORDER = ["name", "goal", "budget_eur", "time_weeks"];

function ConcernAnalyzer({ parentId, onAdded, onBack }) {
  const [text, setText] = useState("");
  const [history, setHistory] = useState([]);   // accepted user messages
  const [log, setLog] = useState([]);           // chat bubbles
  const [result, setResult] = useState(null);   // last "ready" result
  const [collected, setCollected] = useState({});
  const [busy, setBusy] = useState(false);

  async function send() {
    if (!text.trim()) return;
    const msg = text.trim();
    setLog((l) => [...l, { who: "user", text: msg }]);
    setText("");
    setBusy(true);
    try {
      const res = await api.analyze(msg, history);

      if (res.status === "blocked") {
        // rejected input: do NOT add to history, just show why
        setLog((l) => [...l, { who: "bot", text: "Blocked: " + res.reason }]);
        setResult(null);
        return;
      }

      // accepted: keep the message in history for context
      setHistory((h) => [...h, msg]);
      setCollected(res.collected || {});

      if (res.status === "needs_input") {
        setResult(null);
        setLog((l) => [...l, { who: "bot", text: res.question || "Tell me more." }]);
      } else if (res.status === "ready") {
        setResult(res);
        const v = res.verdict === "safe" ? "Safe to try"
          : res.verdict === "caution" ? "Needs care" : "Too risky";
        setLog((l) => [...l, { who: "bot", text: `All set. Verdict: ${v}. ${res.summary || ""}` }]);
      } else {
        setLog((l) => [...l, { who: "bot", text: "Could not read that. Please rephrase." }]);
      }
    } catch (e) {
      setLog((l) => [...l, { who: "bot", text: "Error: " + e.message }]);
    } finally {
      setBusy(false);
    }
  }

  async function addIt() {
    setBusy(true);
    try {
      const d = result.dimensions || {};
      await api.addNode({
        parent_id: parentId,
        name: result.suggested_name || result.collected?.name || "New project",
        money_committed: Number(result.suggested_budget ?? result.collected?.budget_eur) || 0,
        description: result.collected?.goal || result.summary || "",
        reputation_tier: d.reputation?.tier || "Low",
        relationships_tier: d.relationships?.tier || "Low",
        reversibility_tier: d.reversibility?.tier || "Low",
      });
      onAdded();
    } catch (e) {
      alert("Could not add: " + e.message);
      setBusy(false);
    }
  }

  const dims = result?.dimensions || {};
  const dimOrder = ["time", "money", "reputation", "relationships", "reversibility"];

  return (
    <>
      <a className="back-link" onClick={onBack} style={{ cursor: "pointer" }}>← Back</a>
      <h3>Rectify a concern</h3>
      <p className="small muted">
        Describe the project. I will ask for anything missing and only assess it once
        I have the required details.
      </p>

      {/* required-field checklist */}
      <div className="pill-row" style={{ marginBottom: 10 }}>
        {REQ_ORDER.map((k) => {
          const have = collected[k] !== undefined && collected[k] !== null && collected[k] !== "";
          return (
            <span key={k} className={`badge ${have ? "Low" : "gray"}`}>
              {have ? "✓ " : ""}{REQ_LABELS[k]}
            </span>
          );
        })}
      </div>

      <div className="chat-log">
        {log.map((m, i) => <div key={i} className={`bubble ${m.who}`}>{m.text}</div>)}
      </div>

      {!result && (
        <>
          <textarea value={text} onChange={(e) => setText(e.target.value)}
            placeholder="e.g. Trial an AI tool that drafts marketing emails. About 4 weeks, 6k budget." />
          <div className="row" style={{ marginTop: 10 }}>
            <button onClick={send} disabled={busy || !text.trim()}>
              {busy ? "Reading..." : history.length ? "Send" : "Start"}
            </button>
          </div>
        </>
      )}

      {result && (
        <div className="card" style={{ background: "var(--panel-2)", marginTop: 6 }}>
          <div className="spread">
            <strong>Assessment</strong>
            <span className={`verdict ${result.verdict}`}>
              {result.verdict === "safe" ? "Safe to try" : result.verdict === "caution" ? "Needs care" : "Too risky"}
            </span>
          </div>
          {dimOrder.map((k) => dims[k] && (
            <div className="dim" key={k}>
              <div className="label" style={{ textTransform: "capitalize" }}>{k}</div>
              <div className="small muted">{dims[k].note}</div>
              <div style={{ textAlign: "right" }}><Tier value={dims[k].tier} /></div>
            </div>
          ))}
          {result.verdict === "safe" ? (
            <button onClick={addIt} disabled={busy} style={{ marginTop: 14 }}>
              {busy ? "Adding..." : `Add "${result.suggested_name || result.collected?.name}" as a node`}
            </button>
          ) : (
            <div style={{ marginTop: 12 }}>
              <p className="tiny muted">Not safe enough to add yet. Make it smaller or cheaper, then keep talking.</p>
              <button className="secondary" onClick={() => setResult(null)}>Keep refining</button>
            </div>
          )}
        </div>
      )}
    </>
  );
}

function Dot({ c }) {
  return <span style={{ width: 9, height: 9, borderRadius: 9, background: c, display: "inline-block" }} />;
}

// File-structure / `tree`-style view: expandable parent folder with sub-projects
// under it, each row prefixed by a connector and a left guide line per level.
function PortfolioTree({ center, nodes, selectedId, onSelect }) {
  const [open, setOpen] = useState(true);
  const subs = nodes.filter((n) => !n.is_center);
  const colorFor = (n) =>
    n.pnl_eur == null ? "#c2c7d0" : n.pnl_eur >= 0 ? "#34c759" : "#f15a4a";

  return (
    <div className="tree">
      <div className="tree-row folder" onClick={() => setOpen((o) => !o)}>
        <span className="tw">{open ? "▾" : "▸"}</span>
        <span className="ti">🗂</span>
        <span className="tn">{center?.name}</span>
        <span className="tmeta muted">{subs.length} sub-projects</span>
      </div>

      {open && (
        <div className="tree-children">
          {subs.map((n, i) => {
            const last = i === subs.length - 1;
            return (
              <div
                key={n.id}
                className={`tree-row leaf ${selectedId === n.id ? "sel" : ""}`}
                onClick={() => onSelect && onSelect(n)}
              >
                <span className="guide">{last ? "└─" : "├─"}</span>
                <span className="tdot" style={{ background: colorFor(n) }} />
                <span className="tn">{n.name}</span>
                <span className="tmeta">
                  {n.pnl_eur == null ? (
                    <span className="muted">no forecast</span>
                  ) : (
                    <span style={{ color: colorFor(n), fontWeight: 600 }}>{fmtEur(n.pnl_eur)}</span>
                  )}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function StakeholderPanel({ projectId, stakeholders, asView, setAsView }) {
  async function viewAs(sid) {
    if (asView?.stakeholder?.id === sid) { setAsView(null); return; }
    setAsView(await api.viewAs(projectId, sid));
  }
  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="row" style={{ marginBottom: 6 }}>
        <div className="chip amber"><IconUsers /></div>
        <h3 style={{ margin: 0 }}>Stakeholders</h3>
      </div>
      <p className="small muted">The same project looks different to each person. Pick one.</p>
      <div className="pill-row" style={{ marginBottom: 12 }}>
        {stakeholders.map((s) => (
          <button key={s.id} className={asView?.stakeholder?.id === s.id ? "" : "secondary"} onClick={() => viewAs(s.id)}>
            {s.name} · {s.role}
          </button>
        ))}
      </div>
      {asView && (
        <div className="card" style={{ background: "var(--panel-2)" }}>
          <div className="spread">
            <h3 style={{ margin: 0 }}>{asView.stakeholder.name} · {asView.stakeholder.role}</h3>
            <Tier value={asView.overall_tier} />
          </div>
          <p className="small muted">{asView.stakeholder.stake_note}</p>
          <DimRow label="Money" tier={asView.tiers.money} />
          <DimRow label="Time" tier={asView.tiers.time} />
          <DimRow label="Reputation" tier={asView.tiers.reputation} />
          <DimRow label="Relationships" tier={asView.tiers.relationships} />
          <DimRow label="Reversibility" tier={asView.tiers.reversibility} />
          <div className="alert ok" style={{ marginTop: 12 }}>{asView.framing}</div>
        </div>
      )}
    </div>
  );
}

function RollupPanel({ rollup, children }) {
  const t = rollup.totals;
  const b = rollup.program_boundary;
  const fmtk = (n) => `€${Math.round(n / 1000)}k`;
  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="row" style={{ marginBottom: 6 }}>
        <div className="chip blue"><IconLayers /></div>
        <h3 style={{ margin: 0 }}>Whole program</h3>
      </div>
      <p className="small muted">
        {rollup.active_child_count} active sub-projects added together.
      </p>
      {rollup.boundary_breached && (
        <div className="alert danger">
          <strong>The program as a whole has gone over what it can afford.</strong>
          <ul className="small" style={{ margin: "8px 0 0 18px" }}>
            {rollup.portfolio_flags.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
      )}
      <div className="kv">
        <span className="k">Money (total)</span>
        <span>{fmtk(t.money_committed)} of {fmtk(b.money_committed)} budget {t.money_committed > b.money_committed ? "over" : "within"}</span>
      </div>
    </div>
  );
}

function AskPanel({ projectId, onApplied }) {
  const [log, setLog] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  // Load the saved conversation when the panel mounts (survives refresh/navigation).
  useEffect(() => {
    let alive = true;
    api
      .chatHistory(Number(projectId))
      .then((msgs) => {
        if (alive) setLog(msgs.map((m) => ({ who: m.role, text: m.text })));
      })
      .catch(() => {})
      .finally(() => alive && setLoaded(true));
    return () => {
      alive = false;
    };
  }, [projectId]);

  async function send() {
    if (!text.trim()) return;
    const msg = text.trim();
    setLog((l) => [...l, { who: "user", text: msg }]);
    setText("");
    setBusy(true);
    try {
      const res = await api.ask(msg, Number(projectId));
      setLog((l) => [...l, { who: "bot", text: res.answer || "(no change)" }]);
      // If the navigator changed a parameter, refresh the page so the loss
      // profile, graph, and outcome reflect the new data.
      if (res.applied_fields && Object.keys(res.applied_fields).length && onApplied) {
        onApplied();
      }
    } catch (e) {
      setLog((l) => [...l, { who: "bot", text: "Error: " + e.message }]);
    } finally {
      setBusy(false);
    }
  }

  async function clear() {
    await api.clearChat(Number(projectId)).catch(() => {});
    setLog([]);
  }

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div className="spread" style={{ marginBottom: 6 }}>
        <div className="row">
          <div className="chip coral"><IconTarget /></div>
          <h3 style={{ margin: 0 }}>Navigator</h3>
        </div>
        {log.length > 0 && (
          <button className="secondary" onClick={clear}>Clear history</button>
        )}
      </div>
      <p className="small muted">
        Adjust the project or ask for a read. Try "the budget went down by 20k" or
        "which losing projects can we keep?" Changes are saved.
      </p>
      <div className="chat-log">
        {loaded && log.length === 0 && (
          <p className="small muted" style={{ margin: "4px 0" }}>No messages yet.</p>
        )}
        {log.map((m, i) => <div key={i} className={`bubble ${m.who}`}>{m.text}</div>)}
      </div>
      <div className="row">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Adjust a parameter or ask a question..."
        />
        <button onClick={send} disabled={busy}>{busy ? "..." : "Send"}</button>
      </div>
    </div>
  );
}
