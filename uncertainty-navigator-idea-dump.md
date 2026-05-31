# Uncertainty Navigator — Idea Dump & Functional Requirements

> **Status:** Pre-build brainstorm. Treat this as a living document.  
> **Context:** Challenge 02 — Intraprise 48-hour hackathon.  
> **Core constraint:** The tool must make Affordable Loss the primary decision driver, not expected return.

---

## The concept

A **project tracker / management tool** built around Affordable Loss — not ROI. Instead of forcing users to fill in spreadsheet-style fields, a built-in LLM acts as the primary interface: users express things in natural language ("we have about two months and maybe €15k to burn on this") and the LLM parses intent, asks clarifying questions, and populates the structured fields behind the scenes.

Manual entry is always available. The LLM is an interface layer, not a replacement for user control.

Projects can have sub-projects. Sub-project status and loss profiles roll up to the parent, so the tool can surface portfolio-level patterns — not just per-experiment snapshots. (This is the Google 20% case: no single project looked dangerous; the program as a whole was dying.)

The backend logic that determines project status, risk level, and re-commitment triggers is treated as a **black box** at this stage. What it outputs matters; how it computes it is a separate design problem.

---

## High-level architecture

```
User (natural language or manual input)
        ↓
  LLM Interface Layer
  (parse, clarify, populate)
        ↓
  Structured Project Data Model
  (fields, dimensions, history)
        ↓
  Black Box Status Engine
  (risk level, drift detection, re-commitment trigger)
        ↓
  Output Layer
  (dashboard, commitment card, next step, stop/go signal)
```

---

## Project data model — fields to define (TBD / open questions)

These are the dimensions a project record needs to carry. Some are certain; others need more thought.

### Core identity fields (certain)

| Field | Notes |
|---|---|
| Project name | — |
| Description | Free text. LLM can generate a draft from the user's initial prompt. |
| Owner | Person accountable for the commitment |
| Stakeholders | Multiple. Each stakeholder may have a different loss profile (see Sony case: Kutaragi vs. Ohga). |
| Parent project | Optional. Enables sub-project hierarchy. |
| Created date | — |
| Status | Active / Paused / Stopped / Complete |

### Affordable Loss dimensions (certain — from research literature)

These five must all be captured. The LLM's job is to elicit them without triggering loss aversion.

| Dimension | What to capture | Framing note |
|---|---|---|
| **Time** | Hours/weeks of team time committed | Ask: "how long could this run before it starts hurting other work?" |
| **Money** | Budget that can disappear entirely without affecting operations | Avoid "how much are you willing to lose?" — triggers under-commitment |
| **Reputation** | Visibility / credibility exposure the team accepts | Often the binding constraint inside large companies |
| **Relationships** | Stakeholder trust or political capital being put at risk | Who finds out if this fails, and does that matter? |
| **Reversibility** | What becomes impossible to undo once started | Vendor contracts, headcount, data commitments, public announcements |

> **Design note:** The LLM must frame loss questions deliberately. "What could you absorb without changing your operating budget?" produces a more honest answer than "What would you be willing to lose?" The framing is itself a functional requirement.

### Experiment / next step fields (certain)

| Field | Notes |
|---|---|
| Hypothesis | What specific thing are we testing? |
| Smallest test | The minimum action that produces a real signal |
| Specific person / group to contact | Not "talk to users" — a name or role |
| Question to ask them | The actual question |
| Signal: keep going | What observable outcome says continue? |
| Signal: stop | What observable outcome says stop? |
| Re-evaluation date | Hard deadline; cannot be left blank |

### Uncertainty type (open question)

The challenge identifies four distinct types. The tool might need to classify or let the user choose:

- **Technology** — does the approach even work?
- **Market** — do users want or need this?
- **Stakeholder** — who can approve, block, or redirect?
- **Resource** — do we have the skills, data, and tooling?

Each type should probably suggest a different default "smallest test."

### History / audit trail (certain)

Every change to the project — whether made via LLM or manually — should be logged with a timestamp and actor. Re-commitment decisions (continue / stop) are especially important to log explicitly. No silent continuation.

---

## Sub-project / hierarchy behavior

- A project can contain sub-projects to arbitrary depth (at minimum: parent → child).
- Sub-project loss profiles and status **roll up** to the parent.
- The parent's Affordable Loss boundary should be the **sum of active sub-project commitments** — if sub-projects collectively exceed the boundary, that is a signal.
- The Google case is the reference: a program's health is not the same as any individual experiment's health. The tool should be able to surface: "your 20% time program has quietly crossed its affordable loss boundary across 12 projects even though no single project looks dangerous."

**Open question:** How does rollup work for non-numeric dimensions like reputation and relationships? Probably requires a qualitative tier system (Low / Medium / High / Critical) rather than arithmetic.

---

## LLM interface — what it does

The LLM is not making decisions. It is an interface that:

1. **Parses natural language input** into structured field values ("we can spend about two months and €15k" → Time: 8 weeks, Money: €15,000).
2. **Asks clarifying questions** when input is ambiguous or incomplete, especially for the loss dimensions.
3. **Frames loss questions carefully** to avoid triggering loss aversion (this is a hard UX requirement, not a nice-to-have).
4. **Drafts outputs** — hypothesis statements, next-step descriptions, commitment summaries — for the user to review and confirm.
5. **Detects drift** — flags when the team's language shifts from Affordable Loss reasoning ("what can we absorb?") toward expected-return reasoning ("what will this get us?"). This is Focus 03 from the challenge brief: protect the decision.
6. **Summarises portfolio state** on request: "here is what your three active projects look like compared to their loss boundaries."

The LLM does **not**:
- Make the stop/go decision.
- Produce a score that replaces human judgment.
- Auto-update fields without user confirmation (though it can suggest updates).

---

## Black box status engine — inputs and outputs (interface only)

We are not defining the internals yet. We need to define what goes in and what comes out.

**Inputs (from the project data model):**
- Current loss dimension values (time spent vs. committed, money spent vs. committed, etc.)
- Reversibility level
- Re-evaluation date (and whether it has been reached)
- Number of active sub-projects and their statuses
- Time since last explicit continue/stop decision
- Uncertainty type

**Outputs (what the rest of the UI consumes):**
- **Risk level** — some tier (e.g. Low / Elevated / High / Critical) per dimension and overall
- **Drift flag** — boolean or signal indicating the team is drifting toward expected-return logic
- **Re-commitment required** — boolean: the team must make an explicit continue/stop decision before proceeding
- **Portfolio pattern flag** — signal visible at the parent level when sub-projects collectively exceed loss boundaries
- **Recommended action** — not a decision, but a suggested next step for the team to consider (e.g. "you are past your re-evaluation date without a logged decision")

---

## Output layer — what users see

### Per-project view
- Affordable Loss profile across all five dimensions, with current consumption vs. committed boundary
- Current hypothesis and next step
- Stop / keep going signals (defined upfront, referenced at re-evaluation)
- Re-evaluation date — with a hard prompt when it arrives
- Status history / audit log
- Commitment card: a summary designed to be shared with leadership (satisfies the "make commitments visible" requirement)

### Portfolio / parent view
- All sub-projects, their statuses, and their individual loss profiles
- Rollup: total loss consumed across the portfolio vs. the parent's boundary
- Any portfolio-level pattern flags from the status engine
- Comparison view: allows side-by-side of multiple experiments (challenge requirement 5: comparison across experiments — the tool supports the comparison, it does not rank or decide)

### Notification / trigger layer
- Re-evaluation date reminder
- Re-commitment required block (team cannot mark "continue" without logging the decision explicitly)
- Drift alert (LLM detected expected-return language creeping in)
- Portfolio boundary alert

---

## Interaction modes

### Natural language (primary)

User types or speaks in plain language. LLM parses and asks follow-up questions. Structured fields are populated as a result. User reviews and confirms before saving.

Example flow:
> "We're thinking about running an internal AI pilot for contract review. We've got about 6 weeks and can probably get €20k from the innovation budget. If it doesn't work, honestly the biggest risk is looking bad in front of the CFO."

LLM response:
> "Got it. Let me map that out. Time boundary: 6 weeks. Money boundary: €20k. Reputation risk: CFO visibility — I'd call that Medium-High. A couple of things I need to pin down before we start: what's the specific thing you'd be testing in those 6 weeks — is it whether the technology works, or whether people will actually use it? And is there a specific person or meeting where you'd present findings at the end?"

### Manual (always available)

Every field has a direct input. No LLM involvement required. Useful for users who know exactly what they want to enter, and for auditing / correcting LLM-populated fields.

---

## Key design decisions still open

- **Stakeholder differentiation:** Does each stakeholder get their own loss profile within a project, or does the project have one shared profile? The Sony case suggests separate profiles matter (Kutaragi vs. Ohga had completely different stakes). Probably need at least a per-stakeholder "role" with a loss tier.
- **Reversibility scoring:** How do we make "reversibility" concrete enough to track over time? It changes as the project progresses (a €5k vendor PoC is reversible; a signed 12-month contract is not).
- **Rollup for qualitative dimensions:** Reputation and relationships can't be summed arithmetically. Needs a tiering / weighting scheme.
- **What triggers re-commitment?** Options: time elapsed (hard date), loss dimension consumption reaching a threshold, a specific event (new stakeholder, leadership visibility), or any combination.
- **Vendor-partner routing:** The MIT NANDA case found vendor-partnered pilots succeeded ~67% of the time vs. ~22% for internal builds. Should the tool surface this and recommend a partnered structure? If so, when and how?
- **How many stakeholder types?** At minimum: Team, Sponsor, Steering Committee. May need to be configurable.

---

## Case study mapping — which cases test which features

| Case | Primary feature tested |
|---|---|
| **Kodak (1975)** | Reframing from expected-return to Affordable Loss; generating the first concrete next step |
| **3M (1968)** | Handling uncertainty where the team has no product hypothesis; directing toward people conversations and signal definition |
| **Google (2004–2013)** | Portfolio rollup; detecting silent erosion of a program-level loss boundary across many sub-projects |
| **Sony (late 1980s)** | Multi-stakeholder loss profiles; showing different outputs for Kutaragi vs. Ohga |
| **MIT NANDA (2025)** | Re-commitment triggers at week 1, week 8, month 6; blocking silent continuation; vendor routing |

---

## What this tool must not do

- Replace ROI with another score or ranking
- End a session with an open-ended business case or speculative forecast
- Allow a team to continue a pilot without an explicit re-commitment decision
- Collapse multiple stakeholders with different loss profiles into one shared number
- Ask loss questions in ways that trigger loss aversion
- Make the stop/go decision for the team
