from __future__ import annotations

import time

from google import genai

from debugagent.llm.base import LLMBackend
from debugagent.llm.rate_limiter import RateLimiter


class GeminiClient(LLMBackend):
    def __init__(self, api_key: str, verbose: bool = False):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing. Set it in .env")
        self.client = genai.Client(api_key=api_key)
        self.rate_limiter = RateLimiter(requests_per_minute=14)
        self.verbose = verbose

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> tuple[str, int]:
        retries = 3
        for attempt in range(retries):
            try:
                self.rate_limiter.acquire(verbose=self.verbose)
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=user_prompt,
                    config={
                        "system_instruction": system_prompt,
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                    },
                )
                text = getattr(response, "text", "") or ""
                usage = getattr(response, "usage_metadata", None)
                tokens = int(getattr(usage, "total_token_count", 0) or 0)
                return text, tokens
            except Exception as exc:
                msg = str(exc).lower()
                retryable = "429" in msg or "rate" in msg or "timeout" in msg
                if attempt < retries - 1 and retryable:
                    backoff = 2 ** attempt
                    if self.verbose:
                        print(f"Gemini retry in {backoff}s ({attempt + 1}/{retries})...")
                    time.sleep(backoff)
                    continue
                raise

        return "", 0
