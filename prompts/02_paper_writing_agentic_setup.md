# Prompt 2: Drafting the paper, starting with methodology and related work

Rossetti explicitly asked us to focus on methodology and related work
first. This prompt is scoped to exactly that, not the whole paper. Do
not let it expand to results or discussion, those wait for prompt 1's
output.

The scaffolding this prompt depends on is already in the repo:

- `paper/context/hypothesis_and_scope.md`, `methodology_facts.md`,
  `related_work_sources.md`, `style_guide.md`, all grounded in the
  actual codebase, not written from general knowledge
- `.claude/agents/paper-writer.md`, a subagent that refuses to cite an
  unverified source or state a mechanism detail not present in the
  context docs

Final target format is LaTeX for Overleaf. The venue and document class
are not confirmed yet (EPJ Data Science's `sn-jnl` class is the likely
target given this extends Cau et al. 2025, but ask Rossetti before
assuming). Draft in plain prose, convert to LaTeX only after the content
is settled.

---

## Prompt

```
We are drafting the methodology and related work sections of the paper,
per Rossetti's explicit request. Nothing else yet.

Read .claude/agents/paper-writer.md so you understand the constraints
that agent operates under before dispatching it: it only cites from the
Confirmed tier of paper/context/related_work_sources.md, only states
mechanism details present in paper/context/methodology_facts.md, and
refuses to invent anything it cannot source.

Step 1. Related work sourcing (do this first, before any writing).
Read paper/context/related_work_sources.md. Everything under "Needs
sourcing" has no real citation attached yet. For each of the five items
listed there, run an actual search (use the paper-search skill, or
WebSearch, whichever finds a real, checkable source) and either:
  - find a real paper with a verifiable DOI or URL and move it into the
    Confirmed tier of related_work_sources.md with that citation, or
  - if nothing suitable is found after a genuine search, leave it under
    Needs sourcing and note in your final summary that this gap is still
    open and the related work section will have a hole there.
Do not fabricate a citation to fill a gap. A missing citation is a known
problem; an invented one is a worse, hidden problem.
One exception: GhostKG's own citation should come directly from
Rossetti, not from a web search, since it is his library. Flag this as
a question for him rather than guessing.

Step 2. Draft the methodology section.
Dispatch the paper-writer agent with: "Draft the methodology section, in
plain prose markdown, from paper/context/methodology_facts.md only.
Cover the simulation loop, one exchange, the annotation and clamp
mechanism, the four memory conditions, triplet extraction, FSRS decay,
the population and topic, and the metrics used. Do not draft results."

Step 3. Draft the related work section.
Only after step 1 is as complete as it can genuinely be. Dispatch the
paper-writer agent with: "Draft the related work section, in plain prose
markdown, using only the Confirmed tier of
paper/context/related_work_sources.md. Situate this project against
Cau et al. (2025) directly, and against each other confirmed source by
topic area. If a topic area from the original 'Needs sourcing' list is
still unfilled, state plainly in your Sources used note that this area
has a gap rather than writing around it with vague claims."

Step 4. Style pass.
Run both drafts through the avoid-ai-writing skill, or a manual pass
against paper/context/style_guide.md if that skill is unavailable in
this session. Fix every em dash, every AI-writing tell, every sentence
that chains two claims that should be split.

Step 5. Human checkpoint.
Do not proceed to LaTeX conversion automatically. Present both drafts
plus the updated related_work_sources.md and stop. The next step
(confirming venue/class with Rossetti, then converting to LaTeX for
Overleaf) needs a human decision on the target venue first.
```

---

## Why this shape

Grounding first, generation second: the context docs exist so the
writing agent cannot hallucinate a citation or a mechanism detail, it
can only draw from files a human has already checked. This is the same
discipline used earlier in this project when writing the technical
documentation, verify against the actual source file before writing
about it, applied here to citations as well as code.

Scoped to exactly what was asked: Rossetti asked for methodology and
related work, not a full draft. Writing more than that risks producing
sections that will need to be rewritten once the actual results are in,
which is wasted work and a worse starting point than an honest gap.

The sourcing step is separated from the drafting step on purpose. A
writing agent under time pressure to produce prose is the wrong agent to
also be evaluating whether a citation is real. Splitting them means the
citation check happens with nothing depending on it being fast.
