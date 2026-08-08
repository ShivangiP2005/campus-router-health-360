# 📡 Campus Router Health 360

**DigiPlus IT Agentic AI Hackathon** — Thakur College of Engineering & Technology

A router health monitoring system that automatically detects failing Wi-Fi routers across a campus fleet, diagnoses the root cause, and recommends a fix — grounded entirely in real telemetry data, with zero invented evidence.

🔗 **Live Demo:** https://campus-router-health-360-t6e9qf8pwzttgntaeux5r9.streamlit.app/
🔗 **API Docs:** https://campus-router-health-360-n8om.onrender.com/docs

---

## The Problem

The college has issued thousands of Wi-Fi routers through its ISP partner. A subset perform badly — slow speeds, frequent disconnects, dead zones — but nobody knows which ones, where, or why. Complaints arrive one at a time by email, and IT investigates each router from scratch, every time.

## Our Solution

1. **Health Score** — every router is scored 0–100 from its hourly telemetry
2. **Worst-10 Dashboard** — instantly surfaces the routers that need attention
3. **AI Copilot** — ask "why is router R-1042 bad?" and get a real answer: cause, evidence, and one recommended fix
4. **Firmware Batch Detection** — our differentiator: instead of reporting N individual router failures, we detect when many routers share a bad firmware version and flag it as one root cause

---

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Streamlit   │─────▶│   FastAPI Backend │─────▶│  Gemini API      │
│  Frontend    │◀─────│   (pandas, rules) │◀─────│  (phrasing only) │
└─────────────┘      └──────────────────┘      └─────────────────┘
                              │
                              ▼
                     routers.csv / metrics.csv
                       / complaints.csv
```

**Key design principle:** the AI never decides facts. A deterministic, rule-based Python engine (`diagnosis.py`) computes the cause, evidence, and fix from real data first. The LLM is called *only* to phrase that pre-computed diagnosis into a natural sentence — it never sees raw data and cannot invent numbers.

### Health Score Formula
- 0–100 scale, weighted penalty across 5 metrics: latency (30%), packet loss (30%), disconnects (20%), speed deficit (10%), signal weakness (10%)
- Each metric normalized 0–1 across the fleet before weighting
- `bad_hour_count`: counts how many of a router's 24 hourly readings were individually bad — this is what separates a router with *sustained* problems from one with a single bad hour

### Diagnosis Rules (in order)
1. Healthy metrics + complaints exist → **user education** (never hardware replacement)
2. Healthy metrics, no complaints → **healthy**
3. Firmware version shared by 3+ underperforming routers → **firmware update** (our differentiator)
4. Weak average signal (< -70 dBm) → **relocate**
5. Sustained bad metrics, no firmware/signal cause → **replace** (hardware degradation)

Full design rationale: see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, pandas |
| AI | Google Gemini (`gemini-2.0-flash`) — phrasing only |
| Frontend | Streamlit, Plotly |
| Data | In-memory CSVs (routers, metrics, complaints) — no database needed |
| Deployment | Render (backend) + Streamlit Community Cloud (frontend) |

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/rankings` | GET | Worst-N routers ranked by health score |
| `/router/{router_id}` | GET | Full detail: info, score, 24h metrics, complaints |
| `/copilot` | POST | Ask a question, get a grounded diagnosis |
| `/firmware-stats` | GET | Firmware-wide batch failure detection |

Full interactive docs available at `/docs` on the deployed backend.

---

## Running Locally

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
# create a .env file with: GEMINI_API_KEY=your_key_here
python -m uvicorn app.main:app --reload
```
Visit `http://localhost:8000/docs`

### Frontend
```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```
Visit `http://localhost:8501`

---

## Validation

Tested against all scenarios specified in the problem statement:
- ✅ A router with sustained bad metrics ranks in the worst-10; a router with one bad hour does not
- ✅ Copilot cites real numbers from the dataset and recommends exactly one fix — never invented evidence
- ✅ A healthy router is correctly identified as healthy, with numbers shown
- ✅ A router with complaints but healthy metrics points to user education, not replacement

---

## Team

Built in a 6-hour hackathon by a team of 2.

## License

Built for DigiPlus IT Agentic AI Hackathon, 2026.