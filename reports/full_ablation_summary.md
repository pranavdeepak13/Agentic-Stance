# Full ablation summary: four memory conditions, 30 days, 140 agents

Reconciled results file for paper drafting (created 2026-09-30). This is the
only results source a section writer should cite numbers from. Every number
below carries one of two provenance labels:

- **[R] Reproducible from this repo.** Computed by
  `scripts/compute_paper_numbers.py` from the four DGX-delivered CSVs in
  `results/`. Rerun with
  `.venv/bin/python -B scripts/compute_paper_numbers.py --results-dir results --bootstrap`.
  The full raw output is pasted in Appendix A.
- **[X] Supplied externally.** Read from the external HTML report
  "Opinion Dynamics — Research Report" via `reports/plain_language_summary.pdf`.
  No code in this repo produces these numbers. They may be cited only with
  the provenance stated, and only after the open questions in Section 5 are
  answered.

Numbers from the old 10-day Ollama baseline (`reports/baseline_no_kg_immigration.md`,
34.9% / 20.1% acceptance, left-drift 30% to 60%) are **superseded** and must
not be cited as results of this ablation. See Section 4.

## 1. Design facts recoverable from the data [R]

| Fact | Value | How verified |
|---|---|---|
| Conditions | no_kg, general_only, tom_only, full_kg | one CSV each in `results/` |
| Agents | 140 | agent ids in CSV |
| Initial distribution (SA, A, N, F, SF) | 14, 28, 56, 28, 14 | day-0 stances, identical in all four |
| Simulated days | 30 | `day_id` 1..30 |
| Rounds per simulated day | 24 | `hour_id` 0..23 |
| Simulated clock step per round | 1 hour | `sim_clock` advances by one hour per (day, hour) |
| Exchanges per round | 140 | every (day, hour) has exactly 140 rows |
| Distinct initiators per round | 140 | every agent initiates exactly once per round |
| Exchanges per condition | 100,800 | 140 x 24 x 30 |
| Exchanges, all conditions | 403,200 | 4 x 100,800 |
| Scored agent-updates per condition | 201,600 | both participants scored in each exchange |
| Times an agent is picked as partner in a round | 1 to 8 when picked (unbounded) | partner counts per (day, hour) |
| Turns per exchange | 2 to 5, mean 3.499 | `n_turns` |
| Pairing schedule and turn counts across conditions | identical in all four (100% row match) | `agent_a_id`, `agent_b_id`, `n_turns` compared row by row |
| Largest single-update stance change | 1 step, in every condition | confirms the +/-1 clamp was active |

Interpretation: every agent initiates one exchange per simulated hour, so each
agent initiates 24 exchanges per simulated day and takes part in about 48 on
average (as initiator or partner). The four conditions share one pairing
schedule, so they differ only in memory content and in the LLM outputs that
memory produces.

Not recoverable from the data: which LLM served the DGX run (the CSV has no
model column; `scripts/DGX_RUNBOOK.md` recommends
`meta-llama/Llama-3.1-8B-Instruct`, but what actually ran is unconfirmed), and
the loop code that produced the hourly cadence (see Section 5).

## 2. Population-level outcomes [R]

Stance scores: SA = -2 (Strongly Against), A = -1, N = 0, F = +1 (In Favor),
SF = +2 (Strongly In Favor). "Against side" = SA + A. "In Favor side" = F + SF.
H = Shannon entropy of the five-label distribution, in bits. C = effective
number of clusters, 1 / sum(p_i^2).

### 2.1 Day 0 and day 30

| Condition | SA | A | N | F | SF | Against side | In Favor side | Mean score | H (bits) | C |
|---|---|---|---|---|---|---|---|---|---|---|
| All, day 0 | 14 | 28 | 56 | 28 | 14 | 42 | 42 | 0.000 | 2.1219 | 3.846 |
| no_kg, day 30 | 6 | 48 | 21 | 65 | 0 | 54 | 65 | 0.036 | 1.6487 | 2.798 |
| general_only, day 30 | 3 | 44 | 18 | 75 | 0 | 47 | 75 | 0.179 | 1.5065 | 2.483 |
| tom_only, day 30 | 1 | 65 | 19 | 53 | 2 | 66 | 55 | -0.071 | 1.5740 | 2.649 |
| full_kg, day 30 | 3 | 42 | 31 | 63 | 1 | 45 | 64 | 0.121 | 1.6908 | 2.924 |

### 2.2 Entropy change and run-averaged dispersion

| Condition | H(0) - H(30), bits | Mean H, days 1-30 | Mean C, days 1-30 | Share of agent-updates with any stance change |
|---|---|---|---|---|
| no_kg | 0.4732 | 1.6304 | 2.771 | 0.331 |
| general_only | 0.6154 | 1.4916 | 2.409 | 0.267 |
| tom_only | 0.5479 | 1.5833 | 2.701 | 0.336 |
| full_kg | 0.4311 | 1.6628 | 2.933 | 0.479 |

Readings supported by these tables:

- Every condition loses most of its Neutral agents and both extremes by the end
  of day 1 (24 rounds). Neutral falls from 56 to between 17 and 30 on day 1
  (Appendix A). The distribution then fluctuates without a further monotone
  trend.
- general_only ends with the lowest entropy and the fewest effective clusters,
  and has the lowest mean entropy and cluster count over the run. It is the
  most convergent condition.
- full_kg ends with the highest entropy and cluster count, has the highest mean
  entropy and cluster count over the run, and has the smallest entropy drop
  from day 0. It is the most dispersed condition.
- full_kg has by far the highest per-update churn: 47.9% of scored
  agent-updates change stance, against 26.7% to 33.6% in the other conditions.
- Direction: general_only shows the largest shift toward the In Favor side
  (mean score +0.179; 75 of 140 agents, 53.6%, on the In Favor side). tom_only
  is the only condition whose mean score ends below zero (-0.071). no_kg ends
  near zero (+0.036).

### 2.3 Where Neutral agents go

| Condition | P(N to F) | P(N to A) |
|---|---|---|
| no_kg | 0.437 | 0.438 |
| general_only | 0.519 | 0.335 |
| tom_only | 0.492 | 0.434 |
| full_kg | 0.470 | 0.448 |

general_only has the clearest asymmetry in Neutral outflow, toward In Favor.
no_kg is the most symmetric.

## 3. Exchange-level outcomes [R]

Acceptance = the scored agent moved strictly toward the partner's
pre-exchange stance. Move away = moved strictly away. d = absolute stance
distance between the scored agent and the partner before the exchange.

### 3.1 Acceptance by distance (point estimates, all distances)

| Condition | d = 1 | d = 2 | d = 3 | d = 4 | d = 0 (any move) |
|---|---|---|---|---|---|
| no_kg | 0.2530 (n=57,608) | 0.1015 (n=67,118) | 0.3869 (n=6,686) | 0.8111 (n=90) | 0.3344 |
| general_only | 0.2720 (n=49,042) | 0.0994 (n=65,598) | 0.4227 (n=4,502) | 0.8750 (n=40) | 0.2268 |
| tom_only | 0.2750 (n=57,480) | 0.1147 (n=67,856) | 0.4101 (n=3,894) | 0.8235 (n=34) | 0.3385 |
| full_kg | 0.3529 (n=75,062) | 0.2674 (n=55,854) | 0.5176 (n=3,234) | 0.8750 (n=48) | 0.4680 |

### 3.2 Agent-clustered bootstrap, 95% intervals

1,000 resamples of the 140 scored agents, within the single run of each
condition. These intervals capture agent-to-agent variability inside one run.
They do not capture run-to-run variability, since each condition was run once
with one seed.

| Condition | P(acc, d=1) | P(acc, d=2) | Ratio d2/d1 | P(away, d=1) | P(away, d=2) | P(any move) |
|---|---|---|---|---|---|---|
| no_kg | 0.253 [0.243, 0.263] | 0.102 [0.092, 0.112] | 0.401 [0.373, 0.430] | 0.283 [0.268, 0.297] | 0.042 [0.032, 0.052] | 0.331 [0.308, 0.352] |
| general_only | 0.272 [0.262, 0.282] | 0.099 [0.092, 0.107] | 0.366 [0.346, 0.386] | 0.233 [0.222, 0.244] | 0.028 [0.020, 0.037] | 0.267 [0.250, 0.284] |
| tom_only | 0.275 [0.266, 0.283] | 0.115 [0.107, 0.123] | 0.417 [0.396, 0.438] | 0.283 [0.273, 0.294] | 0.025 [0.018, 0.032] | 0.336 [0.318, 0.352] |
| full_kg | 0.353 [0.346, 0.360] | 0.267 [0.257, 0.277] | 0.758 [0.740, 0.775] | 0.268 [0.262, 0.274] | 0.032 [0.026, 0.039] | 0.479 [0.466, 0.491] |

Readings supported by these tables:

- Acceptance falls from d = 1 to d = 2 in all four conditions. This is
  sensitivity to nearby opinions. Cau et al. (2025) report a similar pattern
  for Llama agents ("a form of bounded confidence"). It is not their
  definition of selective agreement, which is directional; see Section 3.4.
- no_kg, general_only, and tom_only have overlapping or near-overlapping
  d2/d1 ratios (0.366 to 0.417). tom_only's ratio interval
  [0.396, 0.438] overlaps no_kg's [0.373, 0.430].
- full_kg is the only condition with a clearly different curve. Its d2/d1
  ratio (0.758 [0.740, 0.775]) is almost double the others, because acceptance
  at d = 2 rises from about 0.10 to 0.267.
- The full_kg flattening comes from more acceptance of distant partners, not
  from more resistance. Move-away rates at d = 2 are low (0.025 to 0.042) in
  every condition.
- Acceptance at d = 3 and d = 4 is high in every condition, but those pairs
  almost always involve an agent at an extreme, and extreme agents move toward
  the centre in most updates (Section 3.3). Moving toward a distant partner
  and regressing toward the centre coincide for those pairs, so the d >= 3
  values do not isolate persuasion. d = 4 samples are also tiny (34 to 90).

### 3.3 Mobility by starting stance

| Starting stance | no_kg P(move) | general_only | tom_only | full_kg |
|---|---|---|---|---|
| SA | 0.620 (n=6,394) | 0.695 (n=3,340) | 0.647 (n=3,649) | 0.731 (n=2,351) |
| A | 0.237 | 0.195 | 0.215 | 0.367 |
| N | 0.875 | 0.853 | 0.926 | 0.919 |
| F | 0.178 | 0.139 | 0.199 | 0.293 |
| SF | 0.939 (n=1,418) | 0.947 (n=1,362) | 0.964 (n=1,005) | 0.920 (n=1,956) |

For SA and SF, every move is a move toward the centre (Appendix A).

Readings supported:

- The moderate stances A and F are the stickiest in every condition.
- Strongly In Favor agents leave that stance in more than 90% of their updates
  in every condition. Strongly Against agents leave it in 62% to 73%.
- Strongly Against is least mobile under no_kg (0.620) and more mobile under
  every memory condition.
- Neutral agents move in 85% to 93% of their updates.

### 3.4 Acceptance by signed distance, and directional asymmetry

Cau et al. (2025) define acceptance on the signed distance
dx = x_partner - x_agent and report that acceptance rises with dx: agents
accept partners whose opinion is more agreeable relative to the discussion
framing more readily than partners who are less agreeable. Here, positive dx
means the partner is further toward In Favor than the scored agent.

| Condition | dx=-4 | dx=-3 | dx=-2 | dx=-1 | dx=+1 | dx=+2 | dx=+3 | dx=+4 |
|---|---|---|---|---|---|---|---|---|
| no_kg | 0.956 (45) | 0.222 (3343) | 0.112 (33559) | 0.232 (28804) | 0.274 (28804) | 0.091 (33559) | 0.552 (3343) | 0.667 (45) |
| general_only | 0.950 (20) | 0.250 (2251) | 0.103 (32799) | 0.184 (24521) | 0.360 (24521) | 0.096 (32799) | 0.596 (2251) | 0.800 (20) |
| tom_only | 1.000 (17) | 0.263 (1947) | 0.132 (33928) | 0.249 (28740) | 0.301 (28740) | 0.098 (33928) | 0.557 (1947) | 0.647 (17) |
| full_kg | 0.958 (24) | 0.457 (1617) | 0.236 (27927) | 0.319 (37531) | 0.386 (37531) | 0.299 (27927) | 0.578 (1617) | 0.792 (24) |

Directional asymmetry, agent-clustered bootstrap 95% intervals:

| Condition | P(A, +1) - P(A, -1) | P(A, +2) - P(A, -2) |
|---|---|---|
| no_kg | +0.042 [+0.013, +0.073] | -0.022 [-0.040, -0.002] |
| general_only | +0.176 [+0.145, +0.206] | -0.007 [-0.024, +0.009] |
| tom_only | +0.052 [+0.018, +0.084] | -0.034 [-0.053, -0.015] |
| full_kg | +0.067 [+0.040, +0.094] | +0.062 [+0.036, +0.089] |

Readings supported:

- At one step, every condition shows a directional bias: agents accept a
  partner on their In Favor side more readily than one on their Against side.
  The bias is small under no_kg (+0.042) and tom_only (+0.052), moderate
  under full_kg (+0.067), and largest under general_only (+0.176), about four
  times the no_kg value. Its interval does not overlap any other condition's.
- general_only is also the condition with the strongest convergence and the
  largest shift toward In Favor (Section 2). The exchange-level asymmetry and
  the population-level outcome point the same way.
- At two steps, the asymmetry is near zero or slightly negative in three
  conditions. Only full_kg is positive (+0.062), because full_kg raises
  acceptance at dx = +2 to 0.299, against 0.091 to 0.098 elsewhere.
- The large gap between dx = -3 and dx = +3 is not clean evidence of
  direction. Those pairs are dominated by agents at the extremes, whose
  mobility differs by stance (Section 3.3).
- The positive side here is In Favor of an unstated proposition (Section
  6.1). Cau et al. anchored direction to an explicit framing statement, so
  the two directional findings are analogous but not the same measurement.

## 4. Superseded and non-comparable earlier numbers

`reports/baseline_no_kg_immigration.md` describes a 10-day no_kg run on
llama3.2 via Ollama with one exchange per agent per day (1,400 exchanges). Its
headline numbers (P(accept) 0.349 at one step, 0.201 at two steps; left-leaning
share 30% to 60%) come from a different backend, a different cadence, and a
different length. The 30-day DGX no_kg run does **not** reproduce the strong
left drift: at day 30 the Against side holds 54 agents and the In Favor side
65, with mean score +0.036. Treat the 10-day run as a pilot. Do not pool it
with the DGX data, and do not describe the left drift as a property of the
ablation's baseline.

## 5. Externally supplied numbers [X]

Source: external HTML report "Opinion Dynamics — Research Report", as condensed
in `reports/plain_language_summary.pdf`. The HTML file is not in this repo, and
neither is the code behind these analyses. Per Pranav's description of the
report, sentiment was scored with a DistilBERT-based classifier and fallacies
with an ELECTRA-based classifier. The exact checkpoints, thresholds, and the
conceptual-core procedure are not documented anywhere in this repo.

| Claim | Number | Status |
|---|---|---|
| Turns with at least one flagged fallacy, full_kg | 38.9% | [X], usable once provenance confirmed |
| Turns with at least one flagged fallacy, no_kg (same metric) | 61.1% | [X], usable once provenance confirmed. Do not use 83.7%, which is fallacy instances per 100 turns, a different metric (plain-language summary, Caveat 2) |
| Sentiment ordering: full_kg most negative, general_only most positive | ordering only; the plain-language PDF gives no numeric values | [X], ordering only |
| Straw-man rate rises under full_kg only | direction only | [X], direction only |
| Shared concepts in the In Favor camp at day 30, full_kg vs tom_only | 339 vs 102 | [X] |
| Same-camp concept overlap across conditions | 14% to 26% | [X] |
| Distinctive-keyword overlap across conditions | 0 in 18 of 18 comparisons | [X] |
| Drift beats shuffled null (1,000 shuffles), general_only and full_kg | > 99.4% of shuffles | [X] |
| Agents with individually non-Markovian trajectories: full_kg, tom_only, general_only, no_kg | 100%, 77%, 3%, 0% | [X], test definition not documented in repo |
| Number of statistical null models in the report | 19 | [X] |

## 6. Spot-check of external claims against [R] numbers

Checked where this repo's CSVs allow it. Caveat 2 in the plain-language
summary found one mismatch. This check found more, so treat every [X] number
as unverified until the report's analysis code is available.

| External claim | [R] result | Verdict |
|---|---|---|
| general_only is the most convergent condition (fewest camps) | lowest final and mean C and H | Reproduced |
| full_kg is the most fragmented condition, with the most individual stance changes | highest final and mean C and H; 47.9% of updates change stance | Reproduced |
| general_only reaches "52% positive" by day 30 | 75/140 = 53.6% on the In Favor side | Approximately reproduced; exact definition unknown |
| full_kg has the strongest net swing toward In Favor (+25%) and the steepest Against collapse (-33%) | In Favor side 42 to 64 (full_kg) vs 42 to 75 (general_only); Against side 42 to 45 (full_kg) | **Not reproduced.** general_only has the larger In Favor gain and the larger mean-score shift; full_kg's Against side grows slightly |
| no_kg ends "close to where it started" | mean score +0.036, but Neutral 56 to 21 and H falls 0.47 bits | Partly: no net directional shift, but a large change in distribution |
| tom_only is the only condition where Neutral agents split evenly between In Favor and Against | no_kg is the most even (0.437 vs 0.438); tom_only is 0.492 vs 0.434 | **Not reproduced** |
| Strongly In Favor agents are talked down more than 90% of the time in every condition | 0.920 to 0.964 | Reproduced |
| "Pro positions are sticky" / Statement 1: "Strongly-favorable positions resist persuasion regardless of memory" | SF is the least stable stance in every condition | **Contradicts** the report's own 90% figure and [R] |
| Strongly Against grows more movable as memory is added | 0.620 (no_kg) to 0.647 to 0.731 across memory conditions | Reproduced vs no_kg; ordering among memory conditions is not monotone in memory size |
| Moderate-distance partners are resisted most, extreme-distance least; full_kg irons this out | d = 2 lowest everywhere; full_kg flattest | Reproduced, but the d >= 3 part is confounded with regression to the centre (Section 3.2) |

### 6.1 Stance polarity: a construct problem, not only a labelling one

`topics/immigration.py` defines "In Favor" as **supporting restrictive
immigration policy** and seeds far-right personas at Strongly In Favor. The
external report and the plain-language summary read In Favor as
**pro-immigration** ("52% positive", "pro-immigration agents", "anti-immigration
positions ... easier to erode"). Under the repo's stated convention, that
reading is inverted.

The prompts do not settle the question either way. `src/prompts.py` passes the
topic to both the agents and the annotator as the bare string "immigration
policy" (the DGX CSV's `topic` column says "immigration"), and the annotator
scale refers to "the proposition" without stating one. So the agents and the
annotator never see what In Favor means. The paper should:

1. describe stances by their scale labels (In Favor / Against the proposition as
   prompted), not as pro- or anti-immigration;
2. report the intended convention from `topics/immigration.py` together with
   the fact that the prompt never states it;
3. list the missing proposition as a threat to validity, and fix it in future
   runs by stating an explicit proposition.

Rossetti's DGX code may have changed the topic string (the CSV's topic value
differs from this repo's). Confirm this with him.

## Appendix A: raw output of `scripts/compute_paper_numbers.py --bootstrap`

### no_kg

- rows (exchanges): 100800; days 1..30; hours 0..23
- exchanges per (day, hour): min 140, max 140
- distinct initiators per (day, hour): min 140, max 140
- n_turns range: 2..5, mean 3.499

| End of day | SA | A | N | F | SF | Against side | In Favor side | H (bits) | C |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 14 | 28 | 56 | 28 | 14 | 42 | 42 | 2.1219 | 3.846 |
| 1 | 6 | 53 | 28 | 53 | 0 | 59 | 53 | 1.7202 | 3.044 |
| 5 | 4 | 51 | 20 | 65 | 0 | 55 | 65 | 1.5922 | 2.706 |
| 10 | 4 | 54 | 22 | 60 | 0 | 58 | 60 | 1.6201 | 2.794 |
| 15 | 5 | 52 | 25 | 58 | 0 | 57 | 58 | 1.6729 | 2.918 |
| 20 | 4 | 58 | 24 | 54 | 0 | 62 | 54 | 1.6395 | 2.852 |
| 25 | 6 | 53 | 21 | 60 | 0 | 59 | 60 | 1.6597 | 2.846 |
| 30 | 6 | 48 | 21 | 65 | 0 | 54 | 65 | 1.6487 | 2.798 |

- entropy, mean over days 1..30: 1.6304; min 1.4055; max 1.7468
- effective clusters, mean over days 1..30: 2.771
- mean stance score, day 0: 0.000; day 30: 0.036
- share of agent-updates with any stance change: 0.3306 (n=201600)
- max |after - before| observed: 1

| abs distance | accepted | total | P(accept) |
|---|---|---|---|
| 1 | 14572 | 57608 | 0.2530 |
| 2 | 6815 | 67118 | 0.1015 |
| 3 | 2587 | 6686 | 0.3869 |
| 4 | 73 | 90 | 0.8111 |
| 0 (any move) | 23444 | 70098 | 0.3344 |

| before | n | P(any move) | P(move toward centre) |
|---|---|---|---|
| SA | 6394 | 0.6198 | 0.6198 |
| A | 75828 | 0.2371 | 0.1849 |
| N | 32083 | 0.8745 | nan |
| F | 85877 | 0.1783 | 0.1630 |
| SF | 1418 | 0.9386 | 0.9386 |

- Neutral outflow: P(N -> In Favor) 0.4370, P(N -> Against) 0.4375

### general_only

- rows (exchanges): 100800; days 1..30; hours 0..23
- exchanges per (day, hour): min 140, max 140
- distinct initiators per (day, hour): min 140, max 140
- n_turns range: 2..5, mean 3.499

| End of day | SA | A | N | F | SF | Against side | In Favor side | H (bits) | C |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 14 | 28 | 56 | 28 | 14 | 42 | 42 | 2.1219 | 3.846 |
| 1 | 3 | 31 | 19 | 87 | 0 | 34 | 87 | 1.4180 | 2.202 |
| 5 | 1 | 36 | 18 | 85 | 0 | 37 | 85 | 1.3723 | 2.216 |
| 10 | 2 | 35 | 20 | 83 | 0 | 37 | 83 | 1.4358 | 2.301 |
| 15 | 4 | 41 | 16 | 76 | 3 | 45 | 79 | 1.6203 | 2.533 |
| 20 | 4 | 45 | 19 | 71 | 1 | 49 | 72 | 1.6116 | 2.633 |
| 25 | 1 | 46 | 22 | 71 | 0 | 47 | 71 | 1.4948 | 2.565 |
| 30 | 3 | 44 | 18 | 75 | 0 | 47 | 75 | 1.5065 | 2.483 |

- entropy, mean over days 1..30: 1.4916; min 1.3346; max 1.6288
- effective clusters, mean over days 1..30: 2.409
- mean stance score, day 0: 0.000; day 30: 0.179
- share of agent-updates with any stance change: 0.2668 (n=201600)
- max |after - before| observed: 1

| abs distance | accepted | total | P(accept) |
|---|---|---|---|
| 1 | 13340 | 49042 | 0.2720 |
| 2 | 6522 | 65598 | 0.0994 |
| 3 | 1903 | 4502 | 0.4227 |
| 4 | 35 | 40 | 0.8750 |
| 0 (any move) | 18696 | 82418 | 0.2268 |

| before | n | P(any move) | P(move toward centre) |
|---|---|---|---|
| SA | 3340 | 0.6952 | 0.6952 |
| A | 58613 | 0.1953 | 0.1559 |
| N | 27324 | 0.8532 | nan |
| F | 110961 | 0.1389 | 0.1274 |
| SF | 1362 | 0.9471 | 0.9471 |

- Neutral outflow: P(N -> In Favor) 0.5186, P(N -> Against) 0.3346

### tom_only

- rows (exchanges): 100800; days 1..30; hours 0..23
- exchanges per (day, hour): min 140, max 140
- distinct initiators per (day, hour): min 140, max 140
- n_turns range: 2..5, mean 3.499

| End of day | SA | A | N | F | SF | Against side | In Favor side | H (bits) | C |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 14 | 28 | 56 | 28 | 14 | 42 | 42 | 2.1219 | 3.846 |
| 1 | 3 | 56 | 17 | 63 | 1 | 59 | 64 | 1.5863 | 2.647 |
| 5 | 3 | 56 | 18 | 63 | 0 | 59 | 63 | 1.5465 | 2.635 |
| 10 | 2 | 58 | 24 | 56 | 0 | 60 | 56 | 1.5792 | 2.768 |
| 15 | 2 | 58 | 19 | 59 | 2 | 60 | 61 | 1.6182 | 2.717 |
| 20 | 3 | 61 | 24 | 50 | 2 | 64 | 52 | 1.6953 | 2.878 |
| 25 | 4 | 59 | 20 | 56 | 1 | 63 | 57 | 1.6527 | 2.786 |
| 30 | 1 | 65 | 19 | 53 | 2 | 66 | 55 | 1.5740 | 2.649 |

- entropy, mean over days 1..30: 1.5833; min 1.4481; max 1.7029
- effective clusters, mean over days 1..30: 2.701
- mean stance score, day 0: 0.000; day 30: -0.071
- share of agent-updates with any stance change: 0.3358 (n=201600)
- max |after - before| observed: 1

| abs distance | accepted | total | P(accept) |
|---|---|---|---|
| 1 | 15807 | 57480 | 0.2750 |
| 2 | 7780 | 67856 | 0.1147 |
| 3 | 1597 | 3894 | 0.4101 |
| 4 | 28 | 34 | 0.8235 |
| 0 (any move) | 24488 | 72336 | 0.3385 |

| before | n | P(any move) | P(move toward centre) |
|---|---|---|---|
| SA | 3649 | 0.6470 | 0.6470 |
| A | 77525 | 0.2146 | 0.1843 |
| N | 33003 | 0.9257 | nan |
| F | 86418 | 0.1988 | 0.1877 |
| SF | 1005 | 0.9642 | 0.9642 |

- Neutral outflow: P(N -> In Favor) 0.4920, P(N -> Against) 0.4337

### full_kg

- rows (exchanges): 100800; days 1..30; hours 0..23
- exchanges per (day, hour): min 140, max 140
- distinct initiators per (day, hour): min 140, max 140
- n_turns range: 2..5, mean 3.499

| End of day | SA | A | N | F | SF | Against side | In Favor side | H (bits) | C |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 14 | 28 | 56 | 28 | 14 | 42 | 42 | 2.1219 | 3.846 |
| 1 | 2 | 55 | 30 | 52 | 1 | 57 | 53 | 1.6750 | 2.954 |
| 5 | 2 | 39 | 39 | 58 | 2 | 41 | 60 | 1.7291 | 3.056 |
| 10 | 2 | 48 | 38 | 49 | 3 | 50 | 52 | 1.7766 | 3.181 |
| 15 | 2 | 60 | 32 | 45 | 1 | 62 | 46 | 1.6754 | 2.946 |
| 20 | 1 | 41 | 36 | 61 | 1 | 42 | 62 | 1.6468 | 2.925 |
| 25 | 0 | 35 | 39 | 65 | 1 | 35 | 66 | 1.5785 | 2.811 |
| 30 | 3 | 42 | 31 | 63 | 1 | 45 | 64 | 1.6908 | 2.924 |

- entropy, mean over days 1..30: 1.6628; min 1.5373; max 1.7954
- effective clusters, mean over days 1..30: 2.933
- mean stance score, day 0: 0.000; day 30: 0.121
- share of agent-updates with any stance change: 0.4794 (n=201600)
- max |after - before| observed: 1

| abs distance | accepted | total | P(accept) |
|---|---|---|---|
| 1 | 26487 | 75062 | 0.3529 |
| 2 | 14933 | 55854 | 0.2674 |
| 3 | 1674 | 3234 | 0.5176 |
| 4 | 42 | 48 | 0.8750 |
| 0 (any move) | 31543 | 67402 | 0.4680 |

| before | n | P(any move) | P(move toward centre) |
|---|---|---|---|
| SA | 2351 | 0.7312 | 0.7312 |
| A | 64230 | 0.3671 | 0.3405 |
| N | 48797 | 0.9186 | nan |
| F | 84266 | 0.2933 | 0.2721 |
| SF | 1956 | 0.9197 | 0.9197 |

- Neutral outflow: P(N -> In Favor) 0.4704, P(N -> Against) 0.4483

### Agent-clustered bootstrap, 95% intervals (1000 resamples of the 140 scored agents)

| condition | P(acc|d=1) | P(acc|d=2) | ratio d2/d1 | P(away|d=1) | P(away|d=2) | P(any move) |
|---|---|---|---|---|---|---|
| no_kg | 0.253 [0.243, 0.263] | 0.102 [0.092, 0.112] | 0.401 [0.373, 0.430] | 0.283 [0.268, 0.297] | 0.042 [0.032, 0.052] | 0.331 [0.308, 0.352] |
| general_only | 0.272 [0.262, 0.282] | 0.099 [0.092, 0.107] | 0.366 [0.346, 0.386] | 0.233 [0.222, 0.244] | 0.028 [0.020, 0.037] | 0.267 [0.250, 0.284] |
| tom_only | 0.275 [0.266, 0.283] | 0.115 [0.107, 0.123] | 0.417 [0.396, 0.438] | 0.283 [0.273, 0.294] | 0.025 [0.018, 0.032] | 0.336 [0.318, 0.352] |
| full_kg | 0.353 [0.346, 0.360] | 0.267 [0.257, 0.277] | 0.758 [0.740, 0.775] | 0.268 [0.262, 0.274] | 0.032 [0.026, 0.039] | 0.479 [0.466, 0.491] |

### Acceptance by signed distance dx = partner - agent (point estimate, n)

| condition | dx=-4 | dx=-3 | dx=-2 | dx=-1 | dx=+1 | dx=+2 | dx=+3 | dx=+4 |
|---|---|---|---|---|---|---|---|---|
| no_kg | 0.956 (45) | 0.222 (3343) | 0.112 (33559) | 0.232 (28804) | 0.274 (28804) | 0.091 (33559) | 0.552 (3343) | 0.667 (45) |
| general_only | 0.950 (20) | 0.250 (2251) | 0.103 (32799) | 0.184 (24521) | 0.360 (24521) | 0.096 (32799) | 0.596 (2251) | 0.800 (20) |
| tom_only | 1.000 (17) | 0.263 (1947) | 0.132 (33928) | 0.249 (28740) | 0.301 (28740) | 0.098 (33928) | 0.557 (1947) | 0.647 (17) |
| full_kg | 0.958 (24) | 0.457 (1617) | 0.236 (27927) | 0.319 (37531) | 0.386 (37531) | 0.299 (27927) | 0.578 (1617) | 0.792 (24) |

### Directional asymmetry, agent-clustered bootstrap 95% intervals

| condition | P(A|+1) - P(A|-1) | P(A|+2) - P(A|-2) |
|---|---|---|
| no_kg | +0.042 [+0.013, +0.073] | -0.022 [-0.040, -0.002] |
| general_only | +0.176 [+0.145, +0.206] | -0.007 [-0.024, +0.009] |
| tom_only | +0.052 [+0.018, +0.084] | -0.034 [-0.053, -0.015] |
| full_kg | +0.067 [+0.040, +0.094] | +0.062 [+0.036, +0.089] |
