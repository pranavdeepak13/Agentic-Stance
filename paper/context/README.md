# Paper: Structured Memory and Selective Agreement in Populations of LLM Agents

The single guide for writing the paper: what it is about, where things live,
the writing plan, how to get help from the agents, and the facts that must
not be gotten wrong.

## 1. The paper in one paragraph

Cau et al. (2025, EPJ Data Science, LODAS) showed that LLM agents in pairwise
debate accept opinions selectively and directionally, not sycophantically.
Their agents have no memory. We add GhostKG, a per-agent knowledge graph with
FSRS decay, and run four memory conditions (`no_kg`, `general_only`,
`tom_only`, `full_kg`) on 140 agents debating immigration policy for 30
simulated days. Memory content shapes the outcome. Facts-only memory gives
the most convergence and about four times the no-memory directional
acceptance bias (+0.176 vs +0.042). Combined memory gives the most churn
(47.9% of updates change stance) and the least selective acceptance. Partner
(theory-of-mind) memory changes little. We had predicted the opposite on
stability, and the paper reports that reversal openly.

## 2. Where things live

```
paper/
  Paper_v1/                    upload THIS folder to Overleaf or Prism
    main.tex                   the whole paper; a % GUIDE block opens each section
    references.bib             21 verified references (fetched from DOI resolvers)
    compare_*.png              the four figures
  context/                     background for you and the agents; never uploaded
    README.md                  this file
    hypothesis_and_scope.md    research question, hypothesis, Outcome (what was found)
    methodology_facts.md       every mechanism claim you may make, traced to code
    related_work_sources.md    citation worksheet: what each reference may be cited for
    style_guide.md             writing rules and LaTeX conventions
    conditions_and_implementation.md   the four memory conditions explained
    ai_draft_v1.tex            an AI-written full draft, for reference only; delete when not needed
reports/full_ablation_summary.md   the ONLY source of numbers (regenerate: scripts/compute_paper_numbers.py)
```

## 3. Getting the file to Overleaf or Prism, and back

- **Upload:** zip `paper/Paper_v1/` and upload it as a new project (Overleaf:
  New Project > Upload Project). Compile `main.tex` with pdfLaTeX.
- **Back to the repository:** the agents read `paper/Paper_v1/main.tex` in the
  repository, not your Overleaf copy. After a writing session, do one of:
  1. download `main.tex` from Overleaf or Prism and replace the repository
     copy;
  2. connect Overleaf's git remote and pull (see
     `.claude/skills/overleaf-sync/SKILL.md`);
  3. paste the section text into the chat when you ask for a review.

## 4. Writing plan

**Order.** Start with the section you can finish today with no open
dependency. Results is the only one: every number is reproducible in the
repo. Then Experimental Setup, then the settled parts of Method (its loop,
clock, and model details wait on Rossetti), then Related Work, which you can
do any time. Then Discussion, Limitations, Conclusion, Introduction, and
Abstract last. `/paper-session next` applies this readiness rule for you.

**Loop for each section.**

1. *Brief.* Read the section's `% GUIDE` block, then ask for a brief:
   "coach brief: Results". You get the outline, the exact numbers with their
   locations, the citation keys, and the pitfalls.
2. *Outline.* Write the paragraph-by-paragraph outline as `%` comments in
   `main.tex`.
3. *Write* the prose yourself in Overleaf or Prism. Use `\pending{...}` for
   anything you cannot settle yet, rather than guessing.
4. *Review.* Sync the file (Section 3), then ask "coach review: Results". Fix
   what you agree with.
5. *Close.* Delete the `% GUIDE` block. The section is done.

**Citations.** When you need a reference that is not in `references.bib`,
ask "find citations for <claim>". The `lit-scout` agent searches, and the
`citation-verifier` agent resolves the identifier and reads the abstract.
Confirmed entries are added to the worksheet and to `references.bib`. Then
re-upload `references.bib`. Never cite from memory.

**Checkpoints.**

- *After Results:* run the full review (numbers and methodology lenses)
  before writing the Discussion on top of it.
- *After all sections:* run the full review on all five lenses, plus a
  compile check. Then resolve every red `\pending`, remove `\nocite{*}`, and
  send the draft to Rossetti.

## 5. Agent help

**Writing sessions.** Start one fresh Claude session per section and type
`/paper-session <mode> <section>`:

- `next`: which section to write next
- `plan Method`: a brief before writing (paragraph plan, numbers, citations,
  traps)
- `review Method`: paste your section text after the command; you get what
  works, what does not, and language fixes
- `polish Method`: grammar and syntax only, as minimal before → after pairs

The skill reads only that section and the lines it needs, so sessions stay
cheap and the fixed prompt prefix stays cached. Move to a new session for
the next section.

**Other agents:**

| Ask | Agent | What you get |
|---|---|---|
| "coach brief: <section>" | `section-coach` | what to write, numbers with locations, citation keys, pitfalls; no prose |
| "coach review: <section>" | `section-coach` | line-level findings on your draft, most important first; never edits |
| "find citations for <claim>" | `lit-scout` then `citation-verifier` | verified references, added to the worksheet and `references.bib` |
| "review the whole paper" | `paper-reviewer` x 5 lenses, plus 2 skeptics per finding | only findings that survive verification |
| "check the numbers are current" | grounding stage | re-runs the analysis script and diffs it against the summary file |

The same steps can run as one saved workflow, `.claude/workflows/paper-pipeline.js`,
with stages `literature`, `grounding`, `coach`, `review`, and `compile`.
No agent writes the manuscript, commits, pushes, or emails.

## 6. Facts that must not be gotten wrong

- **Selective agreement is directional.** Cau et al. define it on signed
  distance: agents accept opinions closer to the framing statement more
  readily. It is not "agents accept nearby partners".
- **The LODAS baseline:** a 7-point scale; the Discussant updates *itself*
  (there is no annotator); the Ship of Theseus with a framing statement;
  Mistral-7B and Llama-3-8B; **140 agents**; 30 iterations; **10 runs**;
  +/-1 updates. So 140 agents is not "larger scale", and the +/-1 rule is
  not new.
- **Our design differs from LODAS:** a separate annotator scores both
  participants; a 5-point scale; a divisive topic; one run per condition.
- **Cadence:** each agent initiated one exchange per simulated *hour* (24
  rounds a day). Never write "once per day" for the delivered runs.
- **Polarity:** prompts never state a proposition. The persona file intends
  In Favor = restrictive policy. Write "In Favor / Against", never pro- or
  anti-immigration.
- **The hypothesis** was stated in advance in an internal document, not
  formally pre-registered. full_kg meets its entropy criterion but is the
  least stable condition by every other measure.
- **The DGX model is unconfirmed.** Do not name it.
- **The 10-day llama3.2 pilot** (34.9%/20.1%, left drift) is superseded.
  Never pool it with the ablation.
- **External report numbers** (fallacy, sentiment, concepts) are not
  reproducible here, and several of its claims failed our checks. Use 38.9%
  vs 61.1%, never 83.7%, and only once provenance is confirmed.
- **Bootstrap intervals** are within-run (one run per condition), not
  across runs.

## 7. Open questions for Rossetti

1. Which venue and document class? `main.tex` uses `article` until he
   answers.
2. Does GhostKG have its own paper? It is cited as software for now.
3. Can he share the DGX loop diff? It decides the cadence, how often the
   GhostKG clock advanced, the topic string, which model vLLM served, and
   the GhostKG version.
4. Is the external HTML report his own analysis, and can he share its code?
5. What proposition did "In Favor" mean in the runs?
6. Can he share the transcripts and knowledge-graph databases (needed for
   the Discussion's mechanism analysis)?
7. The author order and affiliations.
