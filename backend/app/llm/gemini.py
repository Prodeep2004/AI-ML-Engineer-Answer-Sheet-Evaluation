"""Thin async Gemini wrapper: model fallback chain, retries, JSON schema output, embeddings."""
import asyncio
import logging
import math

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.config import get_settings

log = logging.getLogger(__name__)

RETRYABLE = {429, 500, 502, 503, 504}
SKIP_MODEL = {404}


class LLMUnavailable(RuntimeError):
    pass


class Gemini:
    def __init__(self) -> None:
        s = get_settings()
        self.client = genai.Client(
            api_key=s.gemini_api_key,
            http_options=types.HttpOptions(timeout=s.request_timeout_s * 1000),
        )
        self.sem = asyncio.Semaphore(s.max_concurrency)
        self.embed_model = s.embed_model
        self._no_thinking_cfg: set[str] = set()  # models that reject thinking_level
        self._dead: set[str] = set()  # models that returned 404 this process

    def _config(self, model: str, schema: type[BaseModel], temperature: float) -> types.GenerateContentConfig:
        kw = dict(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=temperature,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        if model not in self._no_thinking_cfg:
            kw["thinking_config"] = types.ThinkingConfig(thinking_level="low")
        return types.GenerateContentConfig(**kw)

    async def generate_json(
        self,
        chain: list[str],
        contents: list,
        schema: type[BaseModel],
        temperature: float = 0.0,
        attempts_per_model: int = 2,
    ) -> tuple[BaseModel, str]:
        """Try each model in the chain; retry transient errors with backoff. Returns (parsed, model)."""
        last_err: Exception | None = None
        for model in [m for m in chain if m not in self._dead]:
            for attempt in range(attempts_per_model):
                try:
                    async with self.sem:
                        resp = await self.client.aio.models.generate_content(
                            model=model, contents=contents, config=self._config(model, schema, temperature)
                        )
                    parsed = resp.parsed if isinstance(resp.parsed, schema) else schema.model_validate_json(resp.text)
                    return parsed, model
                except errors.APIError as e:
                    last_err = e
                    if e.code == 400 and "think" in str(e).lower() and model not in self._no_thinking_cfg:
                        self._no_thinking_cfg.add(model)
                        continue
                    if e.code in SKIP_MODEL:
                        self._dead.add(model)
                        break
                    if e.code in RETRYABLE:
                        log.warning("%s -> %s (attempt %d)", model, e.code, attempt + 1)
                        if e.code in (429, 503):
                            break  # quota hit / overloaded: another model has its own quota, move on now
                        await asyncio.sleep(1.5 * (attempt + 1))
                        continue
                    raise
                except Exception as e:  # timeouts, bad JSON
                    last_err = e
                    log.warning("%s -> %s (attempt %d)", model, type(e).__name__, attempt + 1)
                    await asyncio.sleep(1.0)
        # Every model busy: one last patient pass over the chain.
        for model in [m for m in chain if m not in self._dead]:
            try:
                await asyncio.sleep(3)
                async with self.sem:
                    resp = await self.client.aio.models.generate_content(
                        model=model, contents=contents, config=self._config(model, schema, temperature)
                    )
                return schema.model_validate_json(resp.text), model
            except Exception as e:
                last_err = e
        raise LLMUnavailable(f"All models failed: {last_err}")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        texts = [t if t.strip() else "(empty)" for t in texts]
        for attempt in range(4):
            try:
                async with self.sem:
                    resp = await self.client.aio.models.embed_content(
                        model=self.embed_model,
                        # one Content per text: gemini-embedding-2 merges a bare list of strings into ONE vector
                        contents=[types.Content(parts=[types.Part(text=t)]) for t in texts],
                        config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
                    )
                if len(resp.embeddings) != len(texts):
                    raise LLMUnavailable(f"expected {len(texts)} embeddings, got {len(resp.embeddings)}")
                return [e.values for e in resp.embeddings]
            except errors.APIError as e:
                if e.code not in RETRYABLE or attempt == 3:
                    raise
                await asyncio.sleep(1.5 * (attempt + 1))
        raise LLMUnavailable("embedding failed")


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
