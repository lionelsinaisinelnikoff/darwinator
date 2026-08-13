# Darwinator

**Hybrid Innovation Tournament Platform**

Inspired by the research of **Karan Girotra, Christian Terwiesch & Karl T. Ulrich**  
(*Idea Generation and the Quality of the Best Idea*, Management Science; *The Innovation Tournament Handbook*)

---

## Why Darwinator?

In innovation, **value is driven by the exceptional few**, not the average.

A pure team brainstorming process often underperforms. The hybrid process — individuals generate ideas independently first, then the group evaluates and selects — reliably produces:

- More ideas
- Higher average quality
- Better identification of the *best* ideas
- Higher variance (more outliers)

Interactive “build-up” of ideas in groups frequently produces weaker ideas on average.

Darwinator operationalizes this science for MBA and executive education classrooms.

---

## Features

- **Round 1** — Individual idea generation (up to 10 ideas per participant)
- **Evaluation** — Structured 0–10 ratings + optional comments
- **My Reports** — Personal performance with average scores and global ranks
- **Round 2** — Advance one solution with a short presentation
- **Admin Console** — Live stats, top ideas, round control, CSV export
- Clean, modern, mobile-friendly interface

---

## Quick Start (Local)

```bash
# 1. Clone
git clone https://github.com/lionelsinaisinelnikoff/darwinator.git
cd darwinator

# 2. Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate          # Mac / Linux
# venv\\Scripts\\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python app.py
```

Open **http://127.0.0.1:5001**

### Demo Credentials

| Role     | Username          | Password   |
|----------|-------------------|------------|
| Admin    | `admin`           | `stern2026`|
| Students | `rafiki_mba`, `elisa_innovate`, `lionel_strategist`, `cintia_esg`, `alex_vc`, … | `demo2026` |

Tournament code for registration: **`NSAD-TPMI-F25-R1`**

---

## Classroom Flow

1. Students register with the tournament code and submit up to 10 ideas (Round 1).
2. Everyone evaluates a large sample of ideas.
3. Instructor reviews top ideas and advances the tournament to Round 2.
4. Students advance one solution with a short presentation.
5. Class evaluates the advanced solutions.
6. Instructor closes Round 2 and forms project teams around the strongest ideas.

---

## Production Notes

- Default port is **5001** (avoids common macOS conflicts on port 5000).
- SQLite is used for simplicity (excellent for single-class use). For concurrent multi-section production, migrate to Postgres.
- Set `SECRET_KEY` and `DATABASE_PATH` environment variables in production.
- For public deployment: Railway, Render, Fly.io, or a small VPS work well.

---

## Research Foundation

- Girotra, K., Terwiesch, C., & Ulrich, K. T. (2010). Idea Generation and the Quality of the Best Idea. *Management Science*.
- Terwiesch, C. & Ulrich, K. T. *The Innovation Tournament Handbook* (Wharton School Press).

Core principles embedded in the product:
1. Value is driven by exceptional ideas, not average ones.
2. Winners are rarely obvious at the start — they must be discovered through validation.
3. Invest a little to learn a lot.

---

Built for NYU Stern Abu Dhabi Tech Product Management and similar programs.
