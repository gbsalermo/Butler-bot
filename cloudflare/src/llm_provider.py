import json

from js import Object
from pyodide.ffi import to_js

DEFAULT_MODEL = "@cf/google/gemma-4-26b-a4b-it"


def _to_js(value):
    return to_js(value, dict_converter=Object.fromEntries)


def _to_py(value):
    if value is None:
        return None
    try:
        return value.to_py()
    except Exception:
        return value


class LLMProvider:
    name = "base"

    def available(self):
        return False

    async def generate(self, messages, *, max_tokens=500, temperature=0.55):
        raise RuntimeError("LLM provider unavailable")


class CloudflareWorkersAIProvider(LLMProvider):
    name = "cloudflare-workers-ai"

    def __init__(self, ai_binding, model=DEFAULT_MODEL):
        self.ai = ai_binding
        self.model = model

    def available(self):
        return self.ai is not None

    async def generate(self, messages, *, max_tokens=500, temperature=0.55):
        if not self.available():
            raise RuntimeError("Workers AI binding unavailable")
        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        raw = await self.ai.run(self.model, _to_js(payload))
        data = _to_py(raw)
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            text = data.get("response") or data.get("result") or data.get("text")
            if isinstance(text, str):
                return text
        try:
            serialized = json.dumps(data, ensure_ascii=False)
        except Exception:
            serialized = str(data)
        raise RuntimeError(f"Unexpected Workers AI response: {serialized[:300]}")


def build_provider(env):
    try:
        binding = getattr(env, "AI")
    except Exception:
        binding = None
    return CloudflareWorkersAIProvider(binding)
