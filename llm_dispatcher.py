import json
import httpx
from typing import Optional, List, Dict, Any
from config import (
    LLM_API_KEY, LLM_API_URL,
    MODEL_NARRATOR_FAST, MODEL_NARRATOR_DEEP, MODEL_NARRATOR_THINKING,
    MODEL_FALLBACK, LLM_MAX_TOKENS, LLM_TEMPERATURE,
)
from models import FactJSON

SYSTEM_PROMPT = (
    "Ты — бесстрастный ведущий настольной ролевой игры в мрачном фэнтези-мире. "
    "Твоя задача: на основе сухих фактов, предоставленных игровым движком, создать "
    "живое, атмосферное описание сцены. Не добавляй факты, которых нет в полученном JSON. "
    "Не делай выбор за игроков. Не заканчивай сообщение списком вариантов действий. "
    "Описывай ощущения, звуки, запахи, тишину. Будь предельно лаконичен: используй короткие "
    "предложения, избегай длинных описаний и повторов. "
    "Твой ответ будет принудительно обрезан после 1000 токенов, поэтому строго уложись "
    "в 800-900 токенов, чтобы гарантированно завершить мысль. "
    "Никогда не обрывай предложение на середине — лучше закончи раньше, но цельно."
)

def _select_model(scene_type: str, force_model: Optional[str] = None) -> str:
    if force_model:
        return force_model
    if scene_type in ("combat",):
        return MODEL_NARRATOR_FAST
    elif scene_type in ("dialogue", "social"):
        return MODEL_NARRATOR_DEEP
    elif scene_type in ("revelation", "watcher"):
        return MODEL_NARRATOR_THINKING
    return MODEL_NARRATOR_FAST

def _build_messages(fact: FactJSON) -> List[Dict[str, str]]:
    user_content = json.dumps(fact.dict(), ensure_ascii=False, indent=2)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

async def call_api(messages: List[Dict[str, str]], model: str,
                   max_tokens: Optional[int] = None) -> Optional[str]:
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY не задан.")

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens if max_tokens is not None else LLM_MAX_TOKENS,
        "temperature": LLM_TEMPERATURE,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(LLM_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            print(f"[LLM DEBUG] Full response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            if not content:
                print("[LLM ERROR] Empty content in response")
                return None
            return content.strip()
        except httpx.HTTPStatusError as e:
            print(f"[LLM] HTTP ошибка {e.response.status_code}: {e.response.text[:300]}")
            return None
        except Exception as e:
            print(f"[LLM] Ошибка: {e}")
            return None

async def narrate(fact: FactJSON, force_model: Optional[str] = None) -> str:
    model = _select_model(fact.scene_type, force_model)
    messages = _build_messages(fact)
    result = await call_api(messages, model)
    if result:
        return result
    if model != MODEL_FALLBACK:
        print(f"[LLM] Fallback на {MODEL_FALLBACK}")
        result = await call_api(messages, MODEL_FALLBACK)
        if result:
            return result
    return "(Нарратор временно недоступен.)"

async def narrate_system_message(message: str) -> str:
    return message