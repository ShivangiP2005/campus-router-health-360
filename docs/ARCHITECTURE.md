# Architecture — Campus Router Health 360

## Dataset reality
- 60 routers (`routers.csv`), 24 hourly readings each for a single day
  (`metrics.csv`, 1440 rows), 30 complaints across 13 routers (`complaints.csv`)
- Because there's only one day of data, "sustained bad" is measured as
  *how many of a router's 24 hourly readings were individually bad*, not a
  multi-day rolling average.

## Health Score (scoring.py)
- 0–100 scale. Each router's 24 hourly readings are averaged, then 5 metrics
  are min-max normalized (0–1) across the whole fleet and combined as a
  weighted penalty:
  - latency 0.30, packet_loss 0.30, disconnects 0.20, speed_deficit 0.10,
    signal_weakness 0.10
- `bad_hour_count`: number of the 24 hours where ANY metric crossed a bad
  threshold (latency > 60ms, packet_loss > 2%, disconnects > 2, signal <
  -70dBm). `sustained_bad` = True when bad_hour_count >= 5.
- This directly implements the rule "one bad hour ≠ a bad router."

## Diagnosis Engine (diagnosis.py)
Fully deterministic, rule-based — **no LLM involved in deciding the cause**.
Order matters (first match wins):
1. Healthy metrics + has complaints → `user_education` (never "replace")
2. Healthy metrics + no complaints → `healthy`
3. Router's firmware version fleet-wide shows high bad_hour_count on 3+
   routers → `firmware` (this is our differentiator — batch detection)
4. Weak average signal (< -70dBm) → `relocate`
5. Sustained bad metrics, no firmware/signal cause → `replace`
   (hardware degradation)
6. Fallback: borderline case, low confidence → `user_education`

Each branch returns `{cause, evidence, fix, confidence}` where every
number in `evidence` is pulled directly from the data — nothing invented.

## AI Copilot layer
The LLM (Claude API) is called **only** to turn the diagnosis dict into a
natural-language sentence. It receives the structured JSON output above —
**never raw CSVs** — so it is structurally incapable of inventing evidence.

```
User question --> diagnose_router() [Python, deterministic]
               --> structured {cause, evidence, fix, confidence}
               --> Claude API: "phrase this diagnosis in 2-3 sentences,
                   using only the numbers given, no new numbers"
               --> natural language answer + raw evidence shown alongside
```

## API (main.py) — 3 endpoints
- `GET /rankings` → worst-N routers with scores (calls scoring.py)
- `GET /router/{router_id}` → single router's metrics + complaints + score
- `POST /copilot` → {router_id, question} → diagnosis dict + phrased answer

## Differentiator: firmware batch detection
`get_firmware_batch_flags()` in diagnosis.py groups routers by firmware
version and flags any version where 3+ routers show high bad_hour_count.
On our real data, **firmware v5.1 is flagged** (4 affected routers, fleet
avg health ~55) — this is the "we found the root cause, not just symptoms"
moment for the demo.

## Stack
- Backend: FastAPI + pandas, in-memory (CSVs loaded at startup, no DB)
- Frontend: Streamlit
- AI: Claude API (Sonnet), phrasing only
- Deployment: Render/Railway (backend) + Streamlit Community Cloud (frontend)
