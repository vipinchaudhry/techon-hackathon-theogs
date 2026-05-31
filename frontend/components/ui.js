"use client";
// Small shared presentational pieces.

const TIER_PCT = { Low: 25, Medium: 50, High: 75, Critical: 100 };

export function Tier({ value }) {
  const v = value || "Low";
  return <span className={`badge ${v}`}>{v}</span>;
}

// A single Affordable-Loss dimension row with a colored bar.
export function DimRow({ label, tier, detail }) {
  const t = tier || "Low";
  return (
    <div className="dim">
      <div className="label">{label}</div>
      <div className="bar">
        <span className={t} style={{ width: `${TIER_PCT[t]}%` }} />
      </div>
      <div className="small" style={{ textAlign: "right" }}>
        {detail ? <span className="muted">{detail}</span> : <Tier value={t} />}
      </div>
    </div>
  );
}

// Full 5-dimension loss profile from a /status response's `dimensions`.
export function LossProfile({ dimensions }) {
  if (!dimensions) return null;
  const money = dimensions.money || {};
  const time = dimensions.time || {};
  const fmt = (n) =>
    n >= 1000 ? `€${Math.round(n / 1000)}k` : `€${Math.round(n || 0)}`;
  return (
    <div>
      <DimRow
        label="Money"
        tier={money.tier}
        detail={`${fmt(money.spent)} / ${fmt(money.committed)}`}
      />
      <DimRow
        label="Time"
        tier={time.tier}
        detail={`${time.spent || 0} / ${time.committed || 0} wks`}
      />
      <DimRow label="Reputation" tier={dimensions.reputation?.tier} />
      <DimRow label="Relationships" tier={dimensions.relationships?.tier} />
      <DimRow label="Reversibility" tier={dimensions.reversibility?.tier} />
    </div>
  );
}

export function Loading({ what = "Loading" }) {
  return <p className="muted">{what}…</p>;
}

export function ErrorBox({ error }) {
  if (!error) return null;
  return (
    <div className="alert danger">
      <strong>Couldn’t reach the backend.</strong>
      <div className="small" style={{ marginTop: 6 }}>{String(error.message || error)}</div>
      <div className="tiny muted" style={{ marginTop: 6 }}>
        Is the backend running on port 8000? Start it with{" "}
        <code>uvicorn app.main:app --reload --port 8000</code> in the backend folder.
      </div>
    </div>
  );
}
