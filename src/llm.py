"""
llm.py — Unified async access to LLM providers, with batch-aware helpers.

Single-request callers still use `llm_call()`. Batch-capable call sites should
use `llm_call_many()` so providers like vLLM can benefit from concurrent
requests that the backend batches internally.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import SimulationConfig

from config import LLMError


@dataclass(frozen=True)
class LLMRequest:
    system: str
    user: str


async def llm_call(system: str, user: str, config: "SimulationConfig") -> str:
    responses = await llm_call_many([LLMRequest(system=system, user=user)], config)
    return responses[0]


async def llm_call_many(
    requests: list[LLMRequest],
    config: "SimulationConfig",
) -> list[str]:
    if not requests:
        return []

    provider = config.llm_provider
    if provider == "ollama":
        return await _call_many_ollama(requests, config)
    if provider == "anthropic":
        return await _call_many_anthropic(requests, config)
    if provider == "openai":
        return await _call_many_openai(requests, config)
    if provider == "groq":
        return await _call_many_groq(requests, config)
    if provider == "vllm":
        return await _call_many_vllm(requests, config)
    raise LLMError(f"Unknown provider: {provider!r}")


async def _bounded_gather(requests: list[LLMRequest], config: "SimulationConfig", call_fn) -> list[str]:
    semaphore = asyncio.Semaphore(config.llm_max_concurrency)

    async def _run(request: LLMRequest) -> str:
        async with semaphore:
            return await call_fn(request, config)

    results = await asyncio.gather(*[_run(request) for request in requests])
    return list(results)


async def _call_one_ollama(request: LLMRequest, config: "SimulationConfig") -> str:
    try:
        import ollama
        client = ollama.AsyncClient()
        response = await client.chat(
            model=config.llm_model,
            messages=[
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
        )
        return response.message.content.strip()
    except ImportError:
        raise LLMError("ollama package not installed. Run: pip install ollama")
    except Exception as exc:
        raise LLMError(f"Ollama call failed: {exc}") from exc


async def _call_one_anthropic(request: LLMRequest, config: "SimulationConfig") -> str:
    try:
        import anthropic
        import os
        client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        message = await client.messages.create(
            model=config.llm_model,
            max_tokens=config.llm_max_tokens,
            system=request.system,
            messages=[{"role": "user", "content": request.user}],
        )
        return message.content[0].text.strip()
    except ImportError:
        raise LLMError("anthropic package not installed. Run: pip install anthropic")
    except KeyError:
        raise LLMError("ANTHROPIC_API_KEY not set in environment")
    except Exception as exc:
        raise LLMError(f"Anthropic call failed: {exc}") from exc


async def _call_one_openai(request: LLMRequest, config: "SimulationConfig") -> str:
    try:
        import openai
        import os
        client = openai.AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = await client.chat.completions.create(
            model=config.llm_model,
            messages=[
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            max_tokens=config.llm_max_tokens,
            temperature=config.llm_temperature,
            top_p=config.llm_top_p,
        )
        return response.choices[0].message.content.strip()
    except ImportError:
        raise LLMError("openai package not installed. Run: pip install openai")
    except KeyError:
        raise LLMError("OPENAI_API_KEY not set in environment")
    except Exception as exc:
        raise LLMError(f"OpenAI call failed: {exc}") from exc


async def _call_one_groq(request: LLMRequest, config: "SimulationConfig") -> str:
    try:
        import groq
        import os
        client = groq.AsyncGroq(api_key=os.environ["GROQ_API_KEY"])
        response = await client.chat.completions.create(
            model=config.llm_model,
            messages=[
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            max_tokens=config.llm_max_tokens,
            temperature=config.llm_temperature,
            top_p=config.llm_top_p,
        )
        return response.choices[0].message.content.strip()
    except ImportError:
        raise LLMError("groq package not installed. Run: pip install groq")
    except KeyError:
        raise LLMError("GROQ_API_KEY not set in environment")
    except Exception as exc:
        raise LLMError(f"Groq call failed: {exc}") from exc


async def _call_one_vllm(request: LLMRequest, config: "SimulationConfig") -> str:
    try:
        import openai
        client = openai.AsyncOpenAI(
            api_key="EMPTY",
            base_url=config.llm_base_url,
        )
        response = await client.chat.completions.create(
            model=config.llm_model,
            messages=[
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            max_tokens=config.llm_max_tokens,
            temperature=config.llm_temperature,
            top_p=config.llm_top_p,
        )
        return response.choices[0].message.content.strip()
    except ImportError:
        raise LLMError("openai package not installed. Run: pip install openai")
    except Exception as exc:
        raise LLMError(f"vLLM call failed: {exc}") from exc


async def _call_many_ollama(requests: list[LLMRequest], config: "SimulationConfig") -> list[str]:
    return await _bounded_gather(requests, config, _call_one_ollama)


async def _call_many_anthropic(requests: list[LLMRequest], config: "SimulationConfig") -> list[str]:
    return await _bounded_gather(requests, config, _call_one_anthropic)


async def _call_many_openai(requests: list[LLMRequest], config: "SimulationConfig") -> list[str]:
    return await _bounded_gather(requests, config, _call_one_openai)


async def _call_many_groq(requests: list[LLMRequest], config: "SimulationConfig") -> list[str]:
    return await _bounded_gather(requests, config, _call_one_groq)


async def _call_many_vllm(requests: list[LLMRequest], config: "SimulationConfig") -> list[str]:
    # vLLM continuously batches concurrent requests on the server side, so a
    # bounded gather is enough to realize the throughput gains without changing
    # the application-level contract.
    return await _bounded_gather(requests, config, _call_one_vllm)
