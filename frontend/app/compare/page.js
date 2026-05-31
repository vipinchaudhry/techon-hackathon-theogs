"use client";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Tier, ErrorBox, DimRow } from "../../components/ui";

export default function ComparePage() {
  const [projects, setProjects] = useState([]);
  const [selected, setSelected] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.projects(false).then(setProjects).catch(setError);
  }, []);

  function toggle(id) {
    setSelected((s) =>
      s.includes(id) ? s.filter((x) => x !== id) : [...s, id]
    );
  }

  async function run() {
    try {
      setResult(await api.compare(selected));
    } catch (e) {
      setError(e);
    }
  }

  return (
    <div>
      <h1>Compare</h1>
      <p className="sub">
        Put projects side by side. It shows the stakes, it does not rank or pick for you.
      </p>
      <ErrorBox error={error} />

      <div className="card">
        <h3>Pick two or more</h3>
        <div className="pill-row">
          {projects.map((p) => (
            <button
              key={p.id}
              className={selected.includes(p.id) ? "" : "secondary"}
              onClick={() => toggle(p.id)}
            >
              {p.name}
            </button>
          ))}
        </div>
        <div style={{ marginTop: 12 }}>
          <button onClick={run} disabled={selected.length < 2}>
            Compare {selected.length} selected
          </button>
        </div>
      </div>

      {result && (
        <div className="grid cols-2" style={{ marginTop: 16 }}>
          {result.items.map((it) => (
            <div key={it.id} className="card">
              <div className="spread">
                <h3>{it.name}</h3>
                <Tier value={it.overall_tier} />
              </div>
              <DimRow label="Money" tier={it.dimensions.money?.tier} />
              <DimRow label="Time" tier={it.dimensions.time?.tier} />
              <DimRow label="Reputation" tier={it.dimensions.reputation?.tier} />
              <DimRow label="Relationships" tier={it.dimensions.relationships?.tier} />
              <DimRow label="Reversibility" tier={it.dimensions.reversibility?.tier} />
              {it.recommit_required && (
                <p className="small" style={{ marginTop: 8 }}>
                  <span className="badge Critical">Decision needed</span>
                </p>
              )}
            </div>
          ))}
        </div>
      )}
      {result && (
        <p className="small muted" style={{ marginTop: 12 }}>
          {result.note}
        </p>
      )}
    </div>
  );
}
