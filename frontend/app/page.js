"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Tier, Loading, ErrorBox } from "../components/ui";
import { IconGrid, IconLayers, IconUsers, IconTarget } from "../components/icons";

const CASE_META = {
  kodak: { chip: "coral", Icon: IconTarget },
  google: { chip: "blue", Icon: IconLayers },
  sony: { chip: "amber", Icon: IconUsers },
};

export default function Home() {
  const [projects, setProjects] = useState(null);
  const [statuses, setStatuses] = useState({});
  const [scenarios, setScenarios] = useState({});
  const [error, setError] = useState(null);

  async function load() {
    try {
      const top = await api.projects(true);
      setProjects(top);
      setScenarios(await api.scenarios());
      const entries = await Promise.all(top.map(async (p) => [p.id, await api.status(p.id)]));
      setStatuses(Object.fromEntries(entries));
    } catch (e) {
      setError(e);
    }
  }
  useEffect(() => { load(); }, []);

  async function reset() {
    await api.reset();
    setProjects(null); setStatuses({}); load();
  }

  const needsDecision = projects?.filter((p) => statuses[p.id]?.recommit_required).length || 0;
  const drifting = projects?.filter((p) => statuses[p.id]?.drift_flag).length || 0;

  return (
    <div>
      <div className="hero">
        <div className="eyebrow">The Uncertainty Navigator</div>
        <h1>Commit to the next step, even when you cannot predict the outcome.</h1>
        <p>
          95% of corporate pilots fail, usually because nobody decided to stop them.
          This tool replaces ROI guesses with Affordable Loss: what you can put on the
          table and be fine losing if it fails. See every bet, judge it across five
          dimensions, and act before it drifts.
        </p>
        <div className="hero-tags">
          <span className="htag">Time</span>
          <span className="htag">Money</span>
          <span className="htag">Reputation</span>
          <span className="htag">Relationships</span>
          <span className="htag">Reversibility</span>
        </div>
      </div>

      <div className="page-head">
        <div>
          <h1>Portfolio</h1>
          <p className="sub">Decisions driven by what you can afford to lose, not ROI guesses.</p>
        </div>
        <button className="secondary" onClick={reset}>Reset demo</button>
      </div>

      <ErrorBox error={error} />

      {/* summary stats, iffee style */}
      <div className="grid cols-3">
        <StatCard chip="blue" Icon={IconLayers} value={projects?.length ?? "–"} cap="Active projects" />
        <StatCard chip="coral" Icon={IconTarget} value={needsDecision} cap="Need a decision" />
        <StatCard chip="amber" Icon={IconGrid} value={drifting} cap="Drifting to ROI" />
      </div>

      <h2>Walkthroughs</h2>
      <div className="grid cols-3">
        {Object.entries(scenarios).map(([key, s]) => {
          const m = CASE_META[key] || { chip: "blue", Icon: IconGrid };
          return (
            <Link key={key} href={`/scenario/${key}`} className="card link">
              <div className={`chip ${m.chip}`}><m.Icon /></div>
              <h3 style={{ marginTop: 14 }}>{s.title}</h3>
              <p className="small muted">{s.steps} steps</p>
            </Link>
          );
        })}
      </div>

      <h2>Projects</h2>
      {!projects && !error && <Loading what="Loading projects" />}
      <div className="grid cols-2">
        {projects?.map((p) => {
          const st = statuses[p.id];
          return (
            <Link key={p.id} href={`/project/${p.id}`} className="card link">
              <div className="spread">
                <h3>{p.name}</h3>
                {st && <Tier value={st.overall_tier} />}
              </div>
              <p className="small muted" style={{ minHeight: 38 }}>
                {p.description?.slice(0, 110)}{p.description?.length > 110 ? "…" : ""}
              </p>
              <div className="pill-row">
                {p.uncertainty_type && <span className="badge gray">{p.uncertainty_type}</span>}
                {st?.recommit_required && <span className="badge Critical">Decision needed</span>}
                {st?.drift_flag && <span className="badge High">ROI drift</span>}
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function StatCard({ chip, Icon, value, cap }) {
  return (
    <div className="card stat">
      <div className={`chip ${chip}`}><Icon /></div>
      <div className="big">{value}</div>
      <div className="cap">{cap}</div>
    </div>
  );
}
