"""
Генератор игрового мира с улучшенным парсингом JSON.
"""
import json
from models import WorldSkeleton, WorldState
from llm_dispatcher import call_api


def _extract_json(text: str) -> str:
    """Пытается извлечь JSON-подстроку из текста, если модель добавила обрамление."""
    text = text.strip()
    # Ищем первый '{' и последний '}'
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text  # возвращаем как есть, если скобок не нашли


async def generate_skeleton(concept: str, mood: str = "мрачное фэнтези") -> WorldSkeleton:
    prompt = f"""Ты — генератор миров для НРИ. Создай скелет мира **строго** в формате JSON.
Не добавляй никакого текста до или после JSON. Ответ должен начинаться с '{{' и заканчиваться '}}'.

{{
  "name": "Название",
  "setting": "Сеттинг",
  "feature": "Уникальная особенность",
  "conflict": "Центральный конфликт",
  "tone": "Тон"
}}

Концепция: {concept}
Настроение: {mood}"""

    messages = [{"role": "user", "content": prompt}]
    result = await call_api(messages, "gryphe/mythomax-l2-13b", max_tokens=512)

    if result:
        json_str = _extract_json(result)
        try:
            data = json.loads(json_str)
            return WorldSkeleton(**data)
        except (json.JSONDecodeError, TypeError) as e:
            return WorldSkeleton(
                name="Ошибка JSON",
                setting=str(e),
                feature=result[:300]
            )
    return WorldSkeleton(
        name="LLM не ответила",
        setting="",
        feature=""
    )


async def generate_full_world(skeleton: WorldSkeleton) -> WorldState:
    prompt = f"""Создай полное описание мира на основе скелета. Ответь **строго** в JSON, без текста вне скобок.

{{
  "description": "2-3 абзаца описания",
  "main_quest": "Главный квест",
  "starting_location": "Стартовая локация",
  "hooks": ["Крючок 1", "Крючок 2", "Крючок 3"],
  "atmosphere": ["Деталь 1", "Деталь 2"]
}}

Скелет:
{skeleton.model_dump_json(indent=2)}"""

    messages = [{"role": "user", "content": prompt}]
    result = await call_api(messages, "gryphe/mythomax-l2-13b", max_tokens=1200)

    if result:
        json_str = _extract_json(result)
        try:
            data = json.loads(json_str)
            return WorldState(
                skeleton=skeleton,
                description=data["description"],
                main_quest=data["main_quest"],
                starting_location=data["starting_location"],
                hooks=data["hooks"],
                atmosphere=data["atmosphere"]
            )
        except Exception as e:
            return WorldState(
                skeleton=skeleton,
                description=f"Ошибка JSON: {e}\nОтвет модели:\n{result[:500]}",
                main_quest="",
                starting_location="",
                hooks=[],
                atmosphere=[]
            )
    return WorldState(
        skeleton=skeleton,
        description="LLM не ответила.",
        main_quest="",
        starting_location="",
        hooks=[],
        atmosphere=[]
    )