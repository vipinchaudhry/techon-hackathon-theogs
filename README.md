# 🧭 Uncertainty Navigator

A tool that helps a team decide what to do next when the future is unclear —
by focusing on **Affordable Loss** (what you can afford to put on the table and be
fine losing) instead of ROI guesses.

It has two parts:
- **backend/** — the brain (Python / FastAPI). Stores projects, runs the "status
  engine", talks to the AI.
- **frontend/** — the screens you click (Next.js / React).

You run both at the same time, in two terminal windows.

---

## What the demo shows (3 case studies, pre-loaded for you)

| Case | What to show the judges |
|---|---|
| **Kodak** | The tool reframes a scary "this will kill our business" decision into a small, affordable test. |
| **Google** | A program looks healthy project-by-project, but the tool **adds them up** and shows the whole program has quietly gone over budget. |
| **Sony** | One project, but each person (Kutaragi vs. Ohga) sees their **own** loss profile. Different stakes, different screen. |

---

## 0. What you need installed (one time)

- **Python 3.13** (NOT 3.14 — it breaks the install). Check with: `python3.13 --version`
- **Node.js** (v18 or newer). Check with: `node --version`

That's it. The database is just a file — nothing to install.

---

## 1. Start the BACKEND (terminal window #1)

Copy-paste these, one block at a time:

```bash
cd ~/Desktop/workspace/techon/backend

# make a clean Python environment (only needed the first time)
python3.13 -m venv .venv
.venv/bin/python -m ensurepip --upgrade
.venv/bin/python -m pip install -r requirements.txt

# start the server
.venv/bin/uvicorn app.main:app --reload --port 8000
```

✅ When you see **"Application startup complete"**, the backend is running.
Leave this window open.

Test it (optional): open http://localhost:8000/health in a browser.
You should see a small block of text with `"ok": true`.

**Next time** you only need the last line:
```bash
cd ~/Desktop/workspace/techon/backend
.venv/bin/uvicorn app.main:app --reload --port 8000
```

---

## 2. Start the FRONTEND (terminal window #2)

```bash
cd ~/Desktop/workspace/techon/frontend

# install the screens (only needed the first time)
npm install

# start it
npm run dev
```

✅ Open **http://localhost:3000** in your browser. You'll see the Portfolio page.

---

## 3. The AI key (already handled, but here's how it works)

- The AI key lives in the file **`techon/api.md`**. Just paste the OpenRouter key
  in there on its own line. The backend finds it automatically — no other setup.
- We use the **cheapest** model by default and there is a **$20 safety stop**: if
  test usage ever hits $20 the app stops calling the AI instead of spending more.
- **No key? No problem.** If `api.md` is missing, the app runs in **mock mode**:
  everything still works and demos fine, it just uses simple built-in logic and
  costs **$0**. The top-right corner of the app always tells you which mode you're in.

To force free mock mode even with a key (e.g. while practicing):
```bash
# in terminal #1, start the backend like this instead:
LLM_MOCK=1 .venv/bin/uvicorn app.main:app --reload --port 8000
```

---

## 4. How to run each demo (click-through)

On the home page there are **3 "Guided walkthrough" cards** at the top. Each one
walks you through the story step by step, then has a button to open the live project.

**Kodak demo**
1. Click the **Kodak** walkthrough card → click **Next** through the 5 steps.
2. Click **"Open the live project"**.
3. Point out: the **Affordable-Loss profile** (small, safe) and the **concrete next
   step** (who to talk to, what to ask, when to stop).

**Google demo (the strong one)**
1. Click the **Google** walkthrough card → step through it.
2. Open the live project. Scroll to **"Portfolio rollup"**.
3. Point out the red **"Program-level boundary breached"** box — no single project
   looked dangerous, but added up they blew the budget.

**Sony demo**
1. Click the **Sony** walkthrough card → step through it.
2. Open the live project. Scroll to **"Stakeholders"**.
3. Click **"Act as Ken Kutaragi"** then **"Act as Norio Ohga"** — show how the same
   project looks completely different to each person.

**Extra things you can show**
- On any project, type into the **chat box** in plain words
  (e.g. *"we have 6 weeks and €20k, biggest risk is looking bad to the CFO"*) and
  watch it fill in the loss profile.
- The **Compare** tab (top bar) puts experiments side by side.
- The red **"Re-commitment required"** box = the tool refusing to let a project
  drift on silently. Click continue/stop to log a real decision (shows in the audit log).

---

## 5. Reset between demos

Click **"↺ Reset demo data"** (top-right of the home page) to put the three case
studies back to their starting state. Do this before each fresh run-through.

---

## 6. If something breaks

| Problem | Fix |
|---|---|
| Frontend says **"Couldn't reach the backend"** | Terminal #1 isn't running. Start the backend (step 1). |
| `python3.13: command not found` | Install Python 3.13, or replace `python3.13` with `python3` **only if** `python3 --version` says 3.13.x. |
| Install fails with **"pydantic-core" / wheel error** | You're on Python 3.14. Use 3.13 (see step 0). |
| `pip: command not found` inside the venv | Run `.venv/bin/python -m ensurepip --upgrade` first, then the install line. |
| **Port already in use** (8000 or 3000) | Something's already running there. Close it, or on Mac run `lsof -ti:8000 \| xargs kill -9` (swap 8000/3000). |
| Page looks empty / stale data | Click **"↺ Reset demo data"**, then refresh the browser. |
| AI replies are weird or you want $0 | Start the backend with `LLM_MOCK=1` (see step 3). |
| Want to wipe everything and start clean | Stop the backend, delete `backend/navigator.db`, start it again. It re-creates the 3 demos. |

---

## 7. Where things live (quick map)

```
techon/
├─ api.md                  ← the AI key goes here (kept secret, not committed)
├─ README.md               ← this file
├─ backend/                ← the Python brain
│  ├─ app/
│  │  ├─ main.py           ← all the web addresses (API endpoints)
│  │  ├─ models.py         ← what a project / stakeholder / log looks like
│  │  ├─ status_engine.py  ← the rules: risk levels, rollup, re-commitment
│  │  ├─ llm.py            ← talks to the AI (and the free mock version)
│  │  ├─ seed.py           ← the Kodak / Google / Sony demo data + walkthroughs
│  │  └─ config.py         ← finds the key, picks the model, $20 stop
│  ├─ requirements.txt     ← Python packages to install
│  ├─ selftest.py          ← quick check that the backend logic works
│  └─ navigator.db         ← the database file (created automatically)
└─ frontend/               ← the screens
   ├─ app/                 ← the pages (home, project, compare, scenario)
   ├─ components/          ← reused pieces (badges, loss profile, top bar)
   └─ lib/api.js           ← how the screens talk to the backend
```
