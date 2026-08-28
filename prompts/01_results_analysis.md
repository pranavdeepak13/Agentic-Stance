# Prompt 1: Results analysis, once the DGX runs finish

Use this prompt in a Claude Code session once Rossetti confirms all
three remaining conditions (general_only, tom_only, full_kg) have
finished, and the 30-day-realigned no_kg has been added.

---

## Prompt

```
Rossetti has finished the DGX ablation runs for general_only, tom_only,
and full_kg (30 days, 140 agents, immigration topic), and re-ran no_kg
at the same 30-day length for alignment. Results are expected under
data/immigration/{condition}/results.csv, matching the convention
scripts/run_dgx_ablation.sh already writes to.

1. Confirm all four condition directories exist and each results.csv
   has 140*30 = 4200 rows (140 agents x 30 days), plus header. Report
   any condition that is short and how many rows it actually has.

2. Run:
   PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B scripts/generate_ablation_report.py \
     --data-dir data/immigration \
     --output reports/full_ablation_comparison.md \
     --figures-dir reports/figures

3. Read the generated reports/full_ablation_comparison.md and the
   figures it references. Do not interpret yet, just confirm the
   numbers look sane: entropy values between 0 and log2(5) ≈ 2.32,
   acceptance rates between 0 and 1, no NaN or missing cells in the
   comparison tables.

4. Read paper/context/hypothesis_and_scope.md, specifically the "What
   would count as support" and "What would count against" sections.
   Compare the actual numbers in reports/full_ablation_comparison.md
   against each stated criterion, one at a time, and report which
   criteria are met, which are not, and which are ambiguous. Do not
   round up ambiguous results to "supports the hypothesis."

5. Report the left-drift figure (left-leaning share, start vs end) for
   each of the four conditions side by side. This is required, not
   optional, per the confound noted in hypothesis_and_scope.md.

6. Commit reports/full_ablation_comparison.md and reports/figures/ to
   a new branch (results/full-ablation-comparison), push it, and open
   a pull request against main with a summary of what the numbers show,
   written plainly, no premature conclusions about publication-readiness.

Do not draft any part of the paper in this session. This session is
analysis only. Paper drafting is prompt 2.
```

---

## What to tell Rossetti

Ask him to either:

- Run `scripts/run_dgx_ablation.sh` as-is, which already writes to the
  correct `data/immigration/{condition}/` paths this analysis expects, or
- If he ran the conditions some other way, confirm the actual output
  paths so the command above can be pointed at the right directory

Ask him to run the same analysis command himself if he wants to look at
the numbers independently before we do:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B scripts/generate_ablation_report.py \
  --data-dir data/immigration \
  --output reports/full_ablation_comparison.md \
  --figures-dir reports/figures
```

This reuses `analysis/metrics.py` and `analysis/plots.py`, both already
in the repo. It does not require pushing raw `results.csv` files to
GitHub, since `data/` is gitignored by design (results.csv for four
30-day conditions is small text, but exchanges.jsonl and the .db files
are not, and none of it needs to live in git). The script's own output,
the markdown report and the PNG figures, are what gets committed.
If he'd rather send the raw data directly, a `results.csv` per condition
is small enough to email or transfer directly. We do not need
exchanges.jsonl or the .db files for this analysis.
