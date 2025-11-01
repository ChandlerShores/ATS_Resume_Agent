import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from ..config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_TIMEOUT_SECONDS
from ..prompt_templates import REPAIR_INSTRUCTION
from ..schemas import response_json_schema


def _client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=OPENAI_API_KEY)


def _with_backoff(callable_fn, *, max_attempts: int = 3) -> Any:
    delay = 2
    attempt = 0
    while True:
        attempt += 1
        try:
            return callable_fn()
        except Exception as e:
            if attempt >= max_attempts:
                raise
            time.sleep(delay)
            delay *= 2


def _create_chat(messages: List[Dict[str, str]], schema: dict):
    client = _client()
    def do_call():
        return client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=OPENAI_TEMPERATURE,
            response_format={
                "type": "json_schema",
                "json_schema": schema,
            },
            timeout=OPENAI_TIMEOUT_SECONDS,
        )

    return _with_backoff(do_call)


def call_model(messages: List[Dict[str, str]]) -> Tuple[bool, Dict, int]:
    schema = response_json_schema()
    start = time.time()
    resp = _create_chat(messages, schema)
    latency_ms = int((time.time() - start) * 1000)

    content = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
        return True, data, latency_ms
    except Exception:
        return False, {"raw": content}, latency_ms


def call_model_with_repair(messages: List[Dict[str, str]]) -> Tuple[bool, Dict, int, int]:
    valid, data, latency_ms = call_model(messages)
    if valid:
        return True, data, latency_ms, 0
    # One repair attempt
    repaired_messages = list(messages) + [{"role": "user", "content": REPAIR_INSTRUCTION}]
    valid2, data2, latency_ms2 = call_model(repaired_messages)
    total_latency = latency_ms + latency_ms2
    return valid2, data2 if valid2 else data, total_latency, 1


