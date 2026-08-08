# Campus Router Health 360 — Agent Rules

## Health score
- 0-100 scale, weighted penalty formula (see ARCHITECTURE.md)
- Use rolling 24h averages, NOT single readings
- Normalize all metrics 0-1 before weighting
- Weights: latency 0.3, packet_loss 0.3, disconnects 0.2, speed_deficit 0.1, signal_weakness 0.1

## Diagnosis engine (CRITICAL)
- Diagnosis MUST be rule-based / deterministic, computed in Python
- LLM is ONLY used to phrase the final answer in natural language
- LLM must NEVER see raw CSV data — only the structured diagnosis JSON
- LLM must NEVER output numbers not present in the input JSON

## Stack
- Backend: FastAPI + pandas, in-memory data (no DB)
- Frontend: Streamlit
- AI: Claude API (Sonnet), called only for phrasing step

## Non-negotiables
- Never invent evidence
- Healthy router → says healthy, shows numbers
- Complaints + healthy metrics → user education, not replacement
- One bad hour ≠ bad router (must use rolling window)