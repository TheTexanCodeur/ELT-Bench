import os


def call_llm(prompt: str, model: str = "gpt-5", temperature: float = 0.0) -> str:
    """
    Minimal abstraction for OpenAI / Anthropic chat models.
    Automatically removes unsupported args like temperature=0.0
    for models that only accept the default.
    """
    # Determine provider
    provider = "openai" if model.startswith(("gpt", "o", "text-")) else "anthropic" if model.startswith(("claude",)) else "openai"

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI()
        kwargs = dict(model=model, messages=[{"role": "user", "content": prompt}])

        # temperature is optional; skip it for models that forbid overrides
        try:
            if temperature not in (None, 1):
                kwargs["temperature"] = temperature
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            # Retry once without temperature if API rejects the arg
            if "temperature" in str(e).lower():
                resp = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
                return resp.choices[0].message.content.strip()
            raise RuntimeError(f"OpenAI call failed: {e}")

    else:
        import anthropic

        client = anthropic.Anthropic()
        kwargs = dict(model=model, max_tokens=2048, messages=[{"role": "user", "content": prompt}])
        if temperature not in (None, 1):
            kwargs["temperature"] = temperature
        try:
            msg = client.messages.create(**kwargs)
        except Exception as e:
            if "temperature" in str(e).lower():
                msg = client.messages.create(model=model, max_tokens=2048, messages=[{"role": "user", "content": prompt}])
            else:
                raise RuntimeError(f"Anthropic call failed: {e}")
        # Extract text parts
        parts = []
        for p in msg.content:
            if hasattr(p, "text"):
                parts.append(p.text)
            elif isinstance(p, dict) and p.get("type") == "text":
                parts.append(p.get("text", ""))
        return "".join(parts).strip()
