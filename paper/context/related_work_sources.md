# Related work sources

A sourcing worksheet, not a bibliography. Two tiers only. Nothing may be
cited in the paper that is not in the confirmed tier, with a real DOI or
URL a human has checked.

Sourcing pass of 2026-09-30: each entry below was found by a real search
(OpenAlex or Crossref search API, arXiv API, or the cited project's own
README), then its identifier was resolved with a live request (Crossref
`/works/{doi}` metadata, arXiv `id_list` query, or an HTTP fetch of the URL
whose page title was checked). The title, authors, venue, and year below come
from that resolved metadata, not from memory. "Supports" states what the
abstract (read in this pass) licenses a citing sentence to say. Do not cite
an entry for a claim beyond its "Supports" line without reading more of the
paper first.

Suggested BibTeX keys are given in brackets.

## Confirmed (verified, safe to cite)

### Direct baseline

**[cau2025selective] Cau, E., Pansanella, V., Pedreschi, D., and Rossetti, G. (2025).**
Selective agreement, not sycophancy: investigating opinion dynamics in
LLM interactions. *EPJ Data Science*, 14, 59.
https://doi.org/10.1140/epjds/s13688-025-00579-1
Supports: the LODAS framework, the selective-agreement finding, and the
metric definitions (`analysis/metrics.py` states it follows this paper). Re-resolved on
Crossref 2026-09-30.

Design details verified against the open-access full text on 2026-09-30.
Cite these exactly; the original DRAFT.md (now retired) had several of them
wrong:
- LODAS agents hold one of **seven** opinions (a 7-point Likert scale) and
  update by +/-1 per interaction. The +/-1 constraint therefore comes from
  LODAS. It is not a contribution of this paper.
- Each interaction pairs a randomly chosen Opponent and Discussant. **Only
  the Discussant updates**, and it does so itself (it is prompted to accept,
  reject, or ignore the Opponent's opinion and update by +/-1). LODAS has no
  separate annotator model. This project's separate annotator is a design
  difference, not a shared limitation.
- Topic: the Ship of Theseus paradox, chosen to minimise controversy, opened
  with a positive ("The ship remains the same") or negative ("The ship
  becomes different") framing statement.
- Models: Mistral-7B-Instruct and Llama-3-8B. Scenarios: balanced (uniform),
  polarized, and unbalanced initial distributions.
- Their null model uses **N = 140 agents, T = 30 iterations**, each iteration
  N pairwise interactions. Results are averaged over **10 runs**. So this
  project's 140 agents is not a larger scale than LODAS.
- Metrics include the effective number of clusters, C(t) = N^2 / sum_i
  n_i(t)^2, and acceptance P(A | dx) with **signed** dx = x_O - x_D.
- Findings: populations converge toward agreement with the framing
  statement. Acceptance rises with signed dx, meaning agents favour more
  agreeable opinions relative to the framing: strongly for Mistral, more
  symmetrically for Llama. Llama agents show "a form of bounded confidence"
  (greater susceptibility to nearby opinions), and the authors conclude that
  agents show neither sycophancy nor bounded confidence in general. About
  20% of Opponent statements contain logical fallacies, and fallacies
  measurably drive opinion change.

### Memory decay: FSRS and GhostKG

**[fsrs_algorithm] Open Spaced Repetition. The Algorithm (FSRS).** Wiki page, awesome-fsrs.
https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm
Supports: the FSRS algorithm as implemented. GhostKG's own FSRS module
(`ghost_kg/memory/fsrs.py`, v0.2.0) states that it implements FSRS v6 and
cites the fsrs4anki "The Algorithm" wiki page. That page now redirects to the
awesome-fsrs wiki above, which returned HTTP 200 with the matching page title. Cite it as
software documentation, with an access date.

**[ye2022ssp] Ye, J., Su, J., and Cao, Y. (2022).** A Stochastic Shortest
Path Algorithm for Optimizing Spaced Repetition Scheduling. In *Proceedings
of the 28th ACM SIGKDD Conference on Knowledge Discovery and Data Mining*,
pp. 4381–4390. https://doi.org/10.1145/3534678.3539081
Supports: the research line FSRS builds on, a memory model with the Markov
property fitted to large-scale review logs and used to schedule reviews. The
fsrs4anki README names this paper as its foundation.

**[su2023dynamics] Su, J., Ye, J., Nie, L., Cao, Y., and Chen, Y. (2023).**
Optimizing Spaced Repetition Schedule by Capturing the Dynamics of Memory.
*IEEE Transactions on Knowledge and Data Engineering*, 35(10), 10085–10097.
https://doi.org/10.1109/TKDE.2023.3251721
Supports: the same research line, the second paper the fsrs4anki README
names.

**[ghostkg] Rossetti, G. GhostKG: Dynamic Knowledge Graphs with Memory Decay for LLM Agents.**
Software, version 0.2.0. https://github.com/GiulioRossetti/GhostKG
Supports: the memory library used, per-agent knowledge graphs with FSRS-6
decay (package metadata: "Dynamic Knowledge Graph with FSRS-6 Forgetting for
LLM Agents"). The repository page resolves and its title matches. This is a
software citation only. Whether a GhostKG paper exists is still open (see
Needs sourcing).

### LLM sycophancy, single-agent

**[perez2023discovering] Perez, E., Ringer, S., Lukošiūtė, K., Nguyen, K., et al. (2023).**
Discovering Language Model Behaviors with Model-Written Evaluations. In
*Findings of the Association for Computational Linguistics: ACL 2023*,
pp. 13387–13434. https://doi.org/10.18653/v1/2023.findings-acl.847
Supports: larger LMs repeat back a dialogue user's preferred answer
("sycophancy"). Also: RLHF can make LMs express stronger political views,
with immigration named as one example topic.

**[sharma2023sycophancy] Sharma, M., Tong, M., Korbak, T., Duvenaud, D., Askell, A., Bowman, S. R., et al. (2023).**
Towards Understanding Sycophancy in Language Models. arXiv:2310.13548.
https://arxiv.org/abs/2310.13548
Supports: five AI assistants consistently exhibit sycophancy across four
free-form tasks. Human preference data favours responses that match a user's
views, and this likely contributes to sycophancy. Cite the arXiv version. A
conference version may exist, but OpenReview blocked automated access, so
the venue is unverified.

**[wei2023synthetic] Wei, J., Huang, D., Lu, Y., Zhou, D., and Le, Q. V. (2023).**
Simple synthetic data reduces sycophancy in large language models.
arXiv:2308.03958. https://doi.org/10.48550/arXiv.2308.03958
Supports: sycophancy is defined as tailoring responses to a user's view even
when that view is not objectively correct. Model scaling and instruction
tuning increase it (PaLM, up to 540B), including on opinion questions such
as politics.

### Classical opinion dynamics

**[degroot1974consensus] DeGroot, M. H. (1974).** Reaching a Consensus.
*Journal of the American Statistical Association*, 69(345), 118–121.
https://doi.org/10.1080/01621459.1974.10480137
Supports: the canonical weighted-averaging consensus model. Volume 69, issue 345, pages 118–121, per Crossref's BibTeX
record (fetched 2026-10-02).

**[hegselmann2002opinion] Hegselmann, R., and Krause, U. (2002).** Opinion
dynamics and bounded confidence models, analysis and simulation. *Journal of
Artificial Societies and Social Simulation*, 5(3), 2.
https://jasss.soc.surrey.ac.uk/5/3/2.html
Supports: the bounded-confidence model family. The URL resolves and the page
title matches. JASSS does not issue DOIs for this volume.

**[deffuant2000mixing] Deffuant, G., Neau, D., Amblard, F., and Weisbuch, G. (2000).**
Mixing beliefs among interacting agents. *Advances in Complex Systems*,
3(01n04), 87–98. https://doi.org/10.1142/S0219525900000078
Supports: pairwise bounded-confidence interaction, in which agents influence
each other only when their opinions are close enough. This is the classical
analogue of distance-dependent acceptance.

**[holley1975ergodic] Holley, R. A., and Liggett, T. M. (1975).** Ergodic
Theorems for Weakly Interacting Infinite Systems and the Voter Model. *The
Annals of Probability*, 3(4). https://doi.org/10.1214/aop/1176996306
Supports: the voter model. Crossref has no page range; the bibliography can
omit it.

**[castellano2009statistical] Castellano, C., Fortunato, S., and Loreto, V. (2009).**
Statistical physics of social dynamics. *Reviews of Modern Physics*, 81(2),
591–646. https://doi.org/10.1103/RevModPhys.81.591
Supports: a review of opinion dynamics models, and of consensus, fragmentation, and
polarization as order parameters. Use it as the umbrella citation for the
metrics framing.

**[sirbu2017opinion] Sîrbu, A., Loreto, V., Servedio, V. D. P., and Tria, F. (2016).**
Opinion Dynamics: Models, Extensions and External Effects. In
*Participatory Sensing, Opinions and Collective Awareness*, Understanding
Complex Systems, pp. 363–401. Springer.
https://doi.org/10.1007/978-3-319-25658-0_17
Supports: a review of opinion dynamics models and their extensions.
`analysis/metrics.py` attributes the effective-clusters formula to this chapter.
The chapter was not read in this pass, so that attribution is unverified. Do
not cite this chapter for the formula; attribute the metric to Cau et al.
(2025), which the code says it follows. Crossref dates the chapter 2016
(online), while the code comment says 2017.

### LLM agents and opinion dynamics

**[chuang2024simulating] Chuang, Y.-S., Goyal, A., Harlalka, N., Suresh, S., Hawkins, R., et al. (2024).**
Simulating Opinion Dynamics with Networks of LLM-based Agents. In *Findings
of the Association for Computational Linguistics: NAACL 2024*,
pp. 3326–3346. https://doi.org/10.18653/v1/2024.findings-naacl.211
Supports: LLM agent populations show a strong bias toward accurate
information and converge toward scientific consensus. Opinion fragmentation
appears after confirmation bias is induced through prompting.

### LLM agent memory architectures

**[lewis2020rag] Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., et al. (2020).**
Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. In
*Advances in Neural Information Processing Systems 33* (NeurIPS 2020).
https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html
(arXiv:2005.11401). Supports: retrieval-augmented generation as the general
pattern of conditioning generation on retrieved external memory. Page numbers
were not verified, so omit them.

**[park2023generative] Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., and Bernstein, M. S. (2023).**
Generative Agents: Interactive Simulacra of Human Behavior. In *Proceedings
of the 36th Annual ACM Symposium on User Interface Software and Technology
(UIST '23)*, pp. 1–22. https://doi.org/10.1145/3586183.3606763
Supports: an agent architecture that stores a complete natural-language
record of experiences, synthesises reflections, and retrieves memories
dynamically. Its agents form opinions and initiate conversations. The
six-author list is checked against the Crossref record.

**[packer2023memgpt] Packer, C., Wooders, S., Lin, K., Fang, V., Patil, S. G., et al. (2023).**
MemGPT: Towards LLMs as Operating Systems. arXiv:2310.08560.
https://doi.org/10.48550/arXiv.2310.08560
Supports: hierarchical memory tiers with data movement between fast and slow
memory, to extend effective context.

**[zhong2024memorybank] Zhong, W., Guo, L., Gao, Q., Ye, H., and Wang, Y. (2024).**
MemoryBank: Enhancing Large Language Models with Long-Term Memory.
*Proceedings of the AAAI Conference on Artificial Intelligence*, 38(17),
19724–19731. https://doi.org/10.1609/aaai.v38i17.29946
Supports: an LLM long-term memory whose updating mechanism is inspired by the
Ebbinghaus forgetting curve. It forgets and reinforces memories based on
elapsed time and relative significance. This is the closest prior use of a
forgetting curve in LLM memory, and the most direct contrast with GhostKG's
FSRS scheduling.

**[zhang2025memorysurvey] Zhang, Z., Dai, Q., Bo, X., Ma, C., Li, R., et al. (2025).**
A Survey on the Memory Mechanism of Large Language Model-based Agents. *ACM
Transactions on Information Systems*, 43(6), 1–47.
https://doi.org/10.1145/3748302
Supports: memory as a key component of LLM-based agents, and a survey
of memory mechanisms. Use it as the umbrella citation for agent memory.

**[edge2024graphrag] Edge, D., Trinh, H., Cheng, N., Bradley, J., Chao, A., Mody, A., et al. (2024).**
From Local to Global: A Graph RAG Approach to Query-Focused Summarization.
arXiv:2404.16130. https://arxiv.org/abs/2404.16130
Supports: graph-structured retrieval augmentation, which pairs a knowledge
graph with RAG. The abstract was not read in this pass, so cite it only for
the existence of the graph-RAG approach, or read it first.

## Needs sourcing (do not cite until verified)

- **GhostKG paper or technical report.** The software citation above is
  confirmed. Whether GhostKG has its own paper is unknown: GhostKG's README
  has no citation section, and a search turned up nothing. Ask Rossetti
  directly.
- **Classifiers used in the external report** (sentiment, fallacy
  detection). Only needed if the paper reports the [X] numbers from
  `reports/full_ablation_summary.md`, Section 5. The model checkpoints are
  unknown until Rossetti shares the analysis code.
- **Sharma et al. conference venue.** Optional. The arXiv citation is fine
  as is.

## Process note

When this list is worked through, move each finished entry up into
Confirmed with its real citation, and delete the corresponding bullet
from Needs sourcing. The related work section may only be drafted using
entries that are in Confirmed at the time of writing.
