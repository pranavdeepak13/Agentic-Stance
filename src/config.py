"""
config.py — All data types, SimulationConfig, config loading, and validation.
Every other module imports its types from here. This is the single source of truth for enums, dataclasses, and constants.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SUPPORTED_PROVIDERS = {"ollama", "anthropic", "openai", "groq", "vllm"}


# ── Enums ─────────────────────────────────────────────────────────────────────

class LikertStance(Enum):
    """
    5-point Likert scale for stance annotation.

    Tuple values: (label, integer score). Both live on the same line so adding
    a new member without a score raises ValueError at import time.
    """
    STRONGLY_AGAINST  = ("Strongly Against",  -2)
    AGAINST           = ("Against",           -1)
    NEUTRAL           = ("Neutral",            0)
    IN_FAVOR          = ("In Favor",           1)
    STRONGLY_IN_FAVOR = ("Strongly In Favor",  2)

    @property
    def label(self) -> str:
        return self.value[0]

    @property
    def score(self) -> int:
        return self.value[1]

    def __str__(self) -> str:
        return self.label


class PoliticalLeaning(str, Enum):
    FAR_LEFT  = "far_left"
    LEFT      = "left"
    CENTER    = "center"
    RIGHT     = "right"
    FAR_RIGHT = "far_right"


class MemoryCondition(str, Enum):
    NO_KG        = "no_kg"
    GENERAL_ONLY = "general_only"
    TOM_ONLY     = "tom_only"
    FULL_KG      = "full_kg"


# ── Custom exceptions ─────────────────────────────────────────────────────────

class AnnotationError(Exception):
    """Raised when the annotator LLM returns an unparseable stance label."""


class LLMError(Exception):
    """Raised when an LLM call fails after all retries."""


# ── SimulationConfig ──────────────────────────────────────────────────────────

@dataclass
class SimulationConfig:
    topic: str                              = "immigration policy"
    n_agents: int                           = 12
    n_iterations: int                       = 50
    min_turns: int                          = 2
    max_turns: int                          = 5
    random_seed: int                        = 42
    memory_condition: MemoryCondition       = MemoryCondition.NO_KG
    clock_advance_hours: int                = 24   
    llm_provider: str                       = "ollama"
    llm_model: str                          = "llama3.2"
    llm_base_url: str                       = "http://localhost:8000/v1"
    llm_max_tokens: int                     = 512
    llm_temperature: float                  = 0.7
    llm_top_p: float                        = 0.95
    llm_max_concurrency: int                = 8
    parallel_exchange_jobs: int             = 1
    output_dir: str                         = "data/run_01"
    db_path: str                            = "data/run_01/simulation.db"


# ── Config loading ────────────────────────────────────────────────────────────

def load_config() -> SimulationConfig:
    """
    Build SimulationConfig from environment variables (loaded from .env).
    Validates all fields and smoke-tests all prompts before returning.
    Fails immediately with a full list of errors — never mid-simulation.
    """
    config = SimulationConfig(
        topic                = os.getenv("TOPIC", "immigration policy"),
        n_agents             = int(os.getenv("N_AGENTS", "12")),
        n_iterations         = int(os.getenv("N_ITERATIONS", "50")),
        min_turns            = int(os.getenv("MIN_TURNS", "2")),
        max_turns            = int(os.getenv("MAX_TURNS", "5")),
        random_seed          = int(os.getenv("RANDOM_SEED", "42")),
        memory_condition     = MemoryCondition(os.getenv("MEMORY_CONDITION", "no_kg")),
        clock_advance_hours  = int(os.getenv("CLOCK_ADVANCE_HOURS", "24")),
        llm_provider         = os.getenv("LLM_PROVIDER", "ollama"),
        llm_model            = os.getenv("LLM_MODEL", "llama3.2"),
        llm_base_url         = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1"),
        llm_max_tokens       = int(os.getenv("LLM_MAX_TOKENS", "512")),
        llm_temperature      = float(os.getenv("LLM_TEMPERATURE", "0.7")),
        llm_top_p            = float(os.getenv("LLM_TOP_P", "0.95")),
        llm_max_concurrency  = int(os.getenv("LLM_MAX_CONCURRENCY", "8")),
        parallel_exchange_jobs = int(os.getenv("PARALLEL_EXCHANGE_JOBS", "1")),
        output_dir           = os.getenv("OUTPUT_DIR", "data/run_01"),
        db_path              = os.getenv("DB_PATH", "data/run_01/simulation.db"),
    )

    _validate_config(config)
    _smoke_test_prompts()
    return config


def _validate_config(config: SimulationConfig) -> None:
    """Collect every config error and raise them all at once."""
    errors: list[str] = []

    if config.min_turns > config.max_turns:
        errors.append(
            f"min_turns ({config.min_turns}) > max_turns ({config.max_turns})"
        )

    if config.n_iterations <= 0:
        errors.append(f"n_iterations must be > 0, got {config.n_iterations}")

    if config.n_agents < 2:
        errors.append(f"n_agents must be >= 2, got {config.n_agents}")

    if config.clock_advance_hours <= 0:
        errors.append(
            f"clock_advance_hours must be > 0, got {config.clock_advance_hours}"
        )

    if config.llm_max_tokens <= 0:
        errors.append(f"llm_max_tokens must be > 0, got {config.llm_max_tokens}")

    if not 0.0 < config.llm_temperature <= 2.0:
        errors.append(f"llm_temperature must be in (0, 2], got {config.llm_temperature}")

    if not 0.0 < config.llm_top_p <= 1.0:
        errors.append(f"llm_top_p must be in (0, 1], got {config.llm_top_p}")

    if config.llm_max_concurrency <= 0:
        errors.append(
            f"llm_max_concurrency must be > 0, got {config.llm_max_concurrency}"
        )

    if config.parallel_exchange_jobs <= 0:
        errors.append(
            f"parallel_exchange_jobs must be > 0, got {config.parallel_exchange_jobs}"
        )

    if config.llm_provider not in SUPPORTED_PROVIDERS:
        errors.append(
            f"llm_provider {config.llm_provider!r} not in {sorted(SUPPORTED_PROVIDERS)}"
        )

    # Create output directory; fail if we can't
    try:
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)
    except PermissionError:
        errors.append(
            f"output_dir {config.output_dir!r} cannot be created (permission denied)"
        )

    db_parent = Path(config.db_path).parent
    if not db_parent.exists():
        errors.append(
            f"db_path parent directory {str(db_parent)!r} does not exist"
        )

    if errors:
        raise ValueError(
            "SimulationConfig validation failed:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    # Ollama connectivity check is last — it requires a network call
    if config.llm_provider == "ollama":
        _check_ollama(config)
    elif config.llm_provider == "vllm":
        _check_vllm_config(config)


def _check_ollama(config: SimulationConfig) -> None:
    """Verify that Ollama is running and the requested model is available."""
    try:
        import ollama
        available = [m.model for m in ollama.list().models]
        model_base = config.llm_model.split(":")[0]
        if not any(m.startswith(model_base) for m in available):
            raise LLMError(
                f"Model {config.llm_model!r} not found in Ollama. "
                f"Available: {available}. "
                f"Run: ollama pull {config.llm_model}"
            )
    except ImportError:
        raise LLMError("ollama package not installed. Run: pip install ollama")
    except Exception as exc:
        if isinstance(exc, LLMError):
            raise
        raise LLMError(
            f"Cannot connect to Ollama. Make sure it is running. Error: {exc}"
        ) from exc


def _check_vllm_config(config: SimulationConfig) -> None:
    """Basic validation for a vLLM OpenAI-compatible endpoint."""
    if not config.llm_base_url.startswith(("http://", "https://")):
        raise LLMError(f"LLM_BASE_URL must be an http(s) URL, got {config.llm_base_url!r}")


def _smoke_test_prompts() -> None:
    """
    Render every prompt with dummy values.
    If any template has a broken placeholder, the simulation exits before the
    first LLM call — not 2 hours into a run.
    """
    from prompts import ALL_PROMPTS  # imported here to avoid circular imports

    dummy = {
        "name": "TestAgent",
        "leaning": "left",
        "age": "30",
        "occupation": "engineer",
        "persona_description": "A thoughtful person.",
        "topic": "test topic",
        "current_stance": "Neutral",
        "kg_context": "",
        "exchange_history": "",
        "utterances": "I think this is important.",
        "scale_definition": "test scale",
        "text": "subject predicate object",
        "dimension": "general",
    }

    for prompt_cls in ALL_PROMPTS:
        prompt = prompt_cls()
        try:
            prompt.render(**{k: dummy[k] for k in prompt.required_keys})
        except (KeyError, TypeError) as exc:
            raise ValueError(
                f"Prompt {prompt_cls.__name__} has a broken template: {exc}"
            ) from exc


# ── Stance parsing ────────────────────────────────────────────────────────────

def parse_likert(text: str) -> LikertStance:
    """
    Parse a Likert label from annotator LLM output into a LikertStance.

    Strategy (most-to-least strict):
      1. Exact match on the full stripped response (ideal: model output just the label)
      2. Substring match — look for any label appearing inside the response text
         (handles models that add "The stance is: X" or similar wrappers)

    Longest label is checked first within substring matching to prevent "Against"
    matching before "Strongly Against".

    Raises AnnotationError if no label is found anywhere in the text.
    """
    cleaned = text.strip()

    # 1. Exact match (case-insensitive)
    for member in LikertStance:
        if member.label.lower() == cleaned.lower():
            return member

    # 2. Substring match — sort longest label first so "Strongly Against"
    #    is found before "Against" in the same string.
    lower_text = cleaned.lower()
    for member in sorted(LikertStance, key=lambda m: len(m.label), reverse=True):
        if member.label.lower() in lower_text:
            return member

    valid = [m.label for m in LikertStance]
    raise AnnotationError(
        f"Could not parse Likert label from: {text!r}. Valid labels: {valid}"
    )
