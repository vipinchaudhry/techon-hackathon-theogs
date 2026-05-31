"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { Loading, ErrorBox } from "../../../components/ui";

export default function ScenarioPage() {
  const { key } = useParams();
  const [scenario, setScenario] = useState(null);
  const [step, setStep] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
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
          scenario.project_id && (
            <a className="btn" href={`/project/${scenario.project_id}`}>
              Open project →
            </a>
          )
        )}
      </div>
    </div>
  );
}
