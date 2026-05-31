"""
Диспетчер LLM-нарраторов.
Выбирает модель, формирует промпт, вызывает API (nano-gpt / OpenAI-совместимый),
возвращает готовый художественный текст.
"""
import json
import httpx
from typing import Optional, List, Dict, Any
from config import (
    LLM_API_KEY,
    LLM_API_URL,
    MODEL_NARRATOR_FAST,
    MODEL_NARRATOR_DEEP,
    MODEL_NARRATOR_THINKING,
    MODEL_FALLBACK,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
)
from models import FactJSON


# Системный промпт, задающий тон нарратору
SYSTEM_PROMPT = (
    "Ты — бесстрастный ведущий настольной ролевой игры в мрачном фэнтези-мире. "
    "Твоя задача: на основе сухих фактов, предоставленных игровым движком, создать "
    "живое, атмосферное описание сцены. Не добавляй факты, которых нет в полученном JSON. "
    "Не делай выбор за игроков. Не заканчивай сообщение списком вариантов действий. "
    "Описывай ощущения, звуки, запахи, тишину. Будь точен и лаконичен."
)


def _select_model(scene_type: str, force_model: Optional[str] = None) -> str:
    """Выбирает модель в зависимости от типа сцены."""
    if force_model:
        return force_model

    if scene_type in ("combat",):
        return MODEL_NARRATOR_FAST
    elif scene_type in ("dialogue", "social"):
        return MODEL_NARRATOR_DEEP
    elif scene_type in ("revelation", "watcher"):
        return MODEL_NARRATOR_THINKING
    else:
        return MODEL_NARRATOR_FAST


def _build_messages(fact: FactJSON) -> List[Dict[str, str]]:
    """Формирует список сообщений для API."""
    user_content = json.dumps(fact.dict(), ensure_ascii=False, indent=2)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


async def _call_api(messages: List[Dict[str, str]], model: str) -> Optional[str]:
    """Вызывает API и возвращает текст ответа или None при ошибке."""
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY не задан. Добавьте ключ в переменные окружения.")

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": LLM_MAX_TOKENS,
        "temperature": LLM_TEMPERATURE,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(LLM_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            # Извлекаем ответ в формате OpenAI Chat Completions
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            return content.strip() if content else None
        except httpx.HTTPStatusError as e:
            print(f"[LLM] HTTP ошибка {e.response.status_code}: {e.response.text[:200]}")
            return None
        except Exception as e:
            print(f"[LLM] Ошибка соединения: {e}")
            return None


async def narrate(fact: FactJSON, force_model: Optional[str] = None) -> str:
    """
    Основная функция: принимает фактаж, возвращает нарративный текст.
    При ошибке пробует fallback-модель.
    """
    model = _select_model(fact.scene_type, force_model)
    messages = _build_messages(fact)

    # Попытка с основной моделью
    result = await _call_api(messages, model)
    if result:
        return result

    # Fallback
    if model != MODEL_FALLBACK:
        print(f"[LLM] Основная модель '{model}' недоступна, пробую fallback '{MODEL_FALLBACK}'...")
        result = await _call_api(messages, MODEL_FALLBACK)
        if result:
            return result

    # Если ничего не сработало — возвращаем сухой текст
    return "(Нарратор временно недоступен. Продолжайте действия.)"


async def narrate_system_message(message: str) -> str:
    """
    Для простых системных сообщений (игрок зашёл, комната создана) —
    не дёргаем LLM, просто возвращаем текст как есть.
    """
    return message