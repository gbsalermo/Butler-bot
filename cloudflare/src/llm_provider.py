import json

from js import Object
from pyodide.ffi import to_js

PRIMARY_MODEL = "@cf/zai-org/glm-4.7-flash"
FALLBACK_MODEL = "@cf/google/gemma-4-26b-a4b-it"


def _to_js(value):
    return to_js(value, dict_converter=Object.fromEntries)


def _to_py(value):
    if value is None:
        return None
    try:
        return value.to_py()
    except Exception:
        return value


def _extract_text(data):
    if isinstance(data, str):
        return data
    if not isinstance(data, dict):
        return None

    direct = data.get("response") or data.get("text")
    if isinstance(direct, str):
        return direct

    result = data.get("result")
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        nested = _extract_text(result)
        if nested:
            return nested

    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
            text = first.get("text")
            if isinstance(text, str):
                return text

    return None


class LLMProvider:
    name = "base"

    def available(self):
        return False

    async def generate(self, messages, *, max_tokens=500, temperature=0.55):
        raise RuntimeError("LLM provider unavailable")


class CloudflareWorkersAIProvider(LLMProvider):
    name = "cloudflare-workers-ai"

    def __init__(self, ai_binding, models=None):
        self.ai = ai_binding
        self.models = models or [PRIMARY_MODEL, FALLBACK_MODEL]
        self.last_model = None

    def available(self):
        return self.ai is not None

    async def _run_model(self, model, messages, max_tokens, temperature):
        payload = {
            "messages": messages,
            "max_completion_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        raw = await self.ai.run(model, _to_js(payload))
        data = _to_py(raw)
        text = _extract_text(data)
        if text:
            self.last_model = model
            return text
        try:
            serialized = json.dumps(data, ensure_ascii=False)
        except Exception:
            serialized = str(data)
        raise RuntimeError(f"Unexpected Workers AI response from {model}: {serialized[:300]}")

    async def generate(self, messages, *, max_tokens=500, temperature=0.55):
        if not self.available():
            raise RuntimeError("Workers AI binding unavailable")

        errors = []
        for model in self.models:
            try:
                return await self._run_model(model, messages, max_tokens, temperature)
            except Exception as exc:
                errors.append(f"{model}: {exc}")
        raise RuntimeError("All Workers AI models failed: " + " | ".join(errors)[:900])


def build_provider(env):
    try:
        binding = getattr(env, "AI")
    except Exception:
        binding = None
    return CloudflareWorkersAIProvider(binding)
