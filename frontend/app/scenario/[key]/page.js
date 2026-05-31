"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { Loading, ErrorBox } from "../../../components/ui";

export default function ScenarioPage() {
  const { key } = useParams();
  const [scenario, setScenario] = useState(null);
  const [step, setStep] = useState(0);
  const [showOutcome, setShowOutcome] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setStep(0);
    setShowOutcome(false);
    api.scenario(key).then(setScenario).catch(setError);
  }, [key]);

  if (error) return <ErrorBox error={error} />;
  if (!scenario) return <Loading what="Loading walkthrough" />;

  const steps = scenario.steps;
  const s = steps[step];
  const last = step === steps.length - 1;

  return (
    <div>
      <a href="/" className="back-link">← Portfolio</a>
      <h1>{scenario.title}</h1>
      <p className="sub">{steps.length} steps</p>

      <div className="step-dots">
        {steps.map((_, i) => (
          <div
            key={i}
            className={`dot ${i === step ? "active" : i < step ? "done" : ""}`}
            onClick={() => setStep(i)}
            style={{ cursor: "pointer" }}
          >
            {i + 1}
          </div>
        ))}
      </div>

      <div className="card" style={{ minHeight: 180 }}>
        <h2 style={{ marginTop: 0 }}>
          Step {step + 1}: {s.title}
        </h2>
        <p style={{ fontSize: 17, lineHeight: 1.6 }}>{s.narration}</p>
      </div>

      <div className="row" style={{ marginTop: 16 }}>
        <button
          className="secondary"
          onClick={() => setStep((x) => Math.max(0, x - 1))}
          disabled={step === 0}
        >
          ← Back
        </button>
        {!last ? (
          <button onClick={() => setStep((x) => x + 1)}>Next →</button>
        ) : (
          <>
            {!showOutcome && (
              <button onClick={() => setShowOutcome(true)}>
                Would it have changed the outcome? →
              </button>
            )}
            {scenario.project_id && (
              <a className="btn secondary" href={`/project/${scenario.project_id}`}>
                Open project →
              </a>
            )}
          </>
        )}
      </div>

      {showOutcome && <OutcomePanel caseKey={key} />}
    </div>
  );
}

function OutcomePanel({ caseKey }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.outcome(caseKey).then(setData).catch(setError);
  }, [caseKey]);

  if (error) return <ErrorBox error={error} />;
  if (!data) return <div style={{ marginTop: 16 }}><Loading what="Asking the Navigator" /></div>;

  const t = data.tool;
  return (
    <div style={{ marginTop: 20 }}>
      <h2>Would it have changed the outcome?</h2>
      <div className="grid cols-2">
        <div className="card" style={{ borderTop: "3px solid var(--critical)" }}>
          <h3 style={{ color: "var(--critical)" }}>What actually happened</h3>
          <div className="kv"><span className="k">They asked</span><span>{data.historical.wrong_question}</span></div>
          <div className="kv"><span className="k">They decided</span><span>{data.historical.actual_decision}</span></div>
          <div className="kv"><span className="k">It cost</span><span>{data.historical.cost}</span></div>
        </div>

        <div className="card" style={{ borderTop: "3px solid var(--green)" }}>
          <h3 style={{ color: "var(--green)" }}>What the Navigator says</h3>
          {t.reframe && <p style={{ marginTop: 0 }}>{t.reframe}</p>}
          {t.verdict && (
            <div className="alert ok" style={{ marginTop: 8 }}>{t.verdict}</div>
          )}
          {t.next_step && (
            <div className="kv"><span className="k">Next step</span><span>{t.next_step}</span></div>
          )}
          {t.portfolio_flags?.length > 0 && (
            <ul className="small" style={{ margin: "8px 0 0 18px" }}>
              {t.portfolio_flags.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          )}
          {t.stakeholder_views?.length > 0 && (
            <div className="pill-row" style={{ marginTop: 8 }}>
              {t.stakeholder_views.map((v) => (
                <span key={v.name} className={`badge ${v.overall_tier}`}>
                  {v.name}: {v.overall_tier}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="hero" style={{ marginTop: 16 }}>
        <div className="eyebrow">The averted outcome</div>
        <p style={{ marginTop: 8, fontSize: 15.5 }}>{data.averted}</p>
      </div>
    </div>
  );
}
