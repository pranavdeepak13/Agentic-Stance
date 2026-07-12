# Baseline results: no_kg, immigration policy

**Condition:** `no_kg` (LODAS replication — no memory)
**Topic:** immigration policy
**Agents:** 140 (truncated Gaussian: FL=14, L=28, N=56, R=28, FR=14)
**Days:** 10
**Seed:** 42
**Model:** llama3.2 via Ollama
**Total exchanges:** 1,400 (140 agents x 10 days)
**Completed:** 2026-07-07

---

## Stance distribution over time

| Day | FAR_LEFT | LEFT | NEUTRAL | RIGHT | FAR_RIGHT | Entropy (bits) |
|-----|----------|------|---------|-------|-----------|----------------|
| 0 (initial) | 14 | 28 | 56 | 28 | 14 | 2.1219 |
| 1 | 4 | 54 | 40 | 40 | 2 | 1.7970 |
| 2 | 3 | 68 | 30 | 39 | 0 | 1.6147 |
| 3 | 3 | 66 | 28 | 43 | 0 | 1.6177 |
| 4 | 1 | 73 | 21 | 45 | 0 | 1.4776 |
| 5 | 5 | 75 | 25 | 34 | 1 | 1.6447 |
| 6 | 7 | 75 | 22 | 35 | 1 | 1.6690 |
| 7 | 6 | 75 | 21 | 38 | 0 | 1.5983 |
| 8 | 2 | 72 | 27 | 38 | 1 | 1.6004 |
| 9 | 3 | 77 | 21 | 38 | 1 | 1.5653 |
| 10 | 6 | 78 | 20 | 35 | 1 | 1.6169 |

---

## Key metrics

| Metric | Value |
|--------|-------|
| Entropy H(0) | 2.1219 bits |
| Entropy H(10) | 1.6169 bits |
| Entropy delta | -0.5050 bits |
| Left-leaning at day 0 | 42 agents (30.0%) |
| Left-leaning at day 10 | 84 agents (60.0%) |
| Right-leaning at day 0 | 42 agents (30.0%) |
| Right-leaning at day 10 | 36 agents (25.7%) |
| Neutral at day 0 | 56 agents (40.0%) |
| Neutral at day 10 | 20 agents (14.3%) |
| FAR_RIGHT at day 10 | 1 agent (0.7%) |

---

## Acceptance rate by stance gap

| Stance gap | Accepted | Total | P(shift) | Note |
|------------|----------|-------|----------|------|
| 0 (same stance) | 395 | 1020 | 0.387 | Any shift |
| 1 | 343 | 984 | 0.349 | Toward partner |
| 2 | 150 | 746 | 0.201 | Toward partner |
| 3 | 25 | 48 | 0.521 | Small sample — unreliable |
| 4 | 2 | 2 | 1.000 | Tiny sample — discard |

---

## Findings

**1. Directional left drift.** The population is not drifting randomly. It is drifting left. Center (NEUTRAL) collapsed from 56 to 20 agents. LEFT grew from 28 to 78. FAR_RIGHT fell from 14 to 1. This reflects a pro-immigration prior in llama3.2: when a CENTER agent discusses immigration with any partner, it shifts left more often than right. This is a model bias, not a social dynamics effect, and it is the reference behavior that KG conditions should be compared against.

**2. Entropy settled fast.** The largest single-day drop was Day 0 to Day 1 (-0.33 bits). By Day 2 the system had reached a rough equilibrium around 1.60 bits. Oscillation persisted but no further trend was visible. Ten-day runs are sufficient to characterize the dynamics.

**3. Selective agreement at scale.** P(shift toward partner) at stance gap 1 = 34.9%. At gap 2 = 20.1%. This is a 42% reduction from gap-1 to gap-2, consistent with the EPJ paper's selective-agreement finding. Agents are substantially more likely to shift toward a close-stance partner than a far-stance one.

**4. Same-stance instability.** 38.7% of exchanges between same-stance agents result in a stance change. There is no social pressure to shift, so this is pure model noise in the annotation. KG memory of one's own prior positions should suppress this number.

---

## Reference conditions (planned)

| Condition | Status | Expected behavior vs no_kg |
|-----------|--------|---------------------------|
| `no_kg` | Complete | Baseline |
| `general_only` | Pending | Moderate drift reduction |
| `tom_only` | Pending | Strongest pushback, lowest acceptance at high gap |
| `full_kg` | Pending | Most stable entropy |

---

## Compute note

140 agents x 10 days x ~102 sec/exchange (Ollama, llama3.2, CPU) = ~40 hours wall time.

With vLLM on GPU + `LLM_MAX_CONCURRENCY=16` + `PARALLEL_EXCHANGE_JOBS=4`: estimated 2-3 hours per condition.
