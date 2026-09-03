# Related work sources

A sourcing worksheet, not a bibliography. Two tiers only. Nothing may be
cited in the paper that is not in the confirmed tier, with a real DOI or
URL a human has checked.

## Confirmed (verified, safe to cite)

**Cau, E., Pansanella, V., Pedreschi, D., and Rossetti, G. (2025).**
Selective agreement, not sycophancy: investigating opinion dynamics in
LLM interactions. *EPJ Data Science*, 14, 59.
https://doi.org/10.1140/epjds/s13688-025-00579-1

This is the direct baseline (LODAS framework) this project extends. Used
throughout the codebase and prior reports. Confirmed real, confirmed
correct DOI, safe to cite without further checking.

## Needs sourcing (do not cite until verified)

The following are topic areas the related work section needs to cover.
None of these have a specific paper attached yet. A writer must run an
actual literature search (paper-search or litreview skill, or a manual
search) and replace each line below with a real, checked citation before
it can appear in the paper. Do not let a model invent a plausible-sounding
title, author list, or DOI for any of these; an invented citation is
worse than a missing one.

- **FSRS (Free Spaced Repetition Scheduler)**: the specific paper or
  technical writeup this project's decay model is based on. GhostKG uses
  it; find the canonical source GhostKG itself cites, if any, rather than
  searching independently.
- **GhostKG**: whether GhostKG has its own paper or technical report to
  cite as the memory architecture this project builds on, separate from
  citing Cau et al. Ask Rossetti directly, since GhostKG is his library.
- **LLM sycophancy / agreement bias, single-agent**: prior work on models
  shifting answers to match a stated user preference or framing, outside
  the multi-agent population setting. Needed to distinguish this paper's
  population-level claim from single-turn sycophancy findings.
- **Classical opinion dynamics models**: DeGroot, bounded-confidence
  (Hegselmann-Krause), or voter models, as the non-LLM precedent for
  using entropy, consensus, and polarization as measurement tools. Needed
  to justify why these specific metrics were chosen.
- **LLM agent memory architectures**: retrieval-augmented generation and
  agent memory systems generally, to place GhostKG's decaying,
  dimension-typed graph against the broader category of "give an LLM
  agent memory" approaches, and state what specifically differs (decay,
  typed dimensions, FSRS scheduling vs. flat retrieval).

## Process note

When this list is worked through, move each finished entry up into
Confirmed with its real citation, and delete the corresponding bullet
from Needs sourcing. The related work section may only be drafted using
entries that are in Confirmed at the time of writing.
