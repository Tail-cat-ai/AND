"""
Генератор игрового мира.
Поэтапный процесс: скелет → правки → утверждение → полный мир.
Использует call_api из llm_dispatcher.
"""
import json
from models import WorldSkeleton, WorldState
from llm_dispatcher import call_api
from config import MODEL_NARRATOR_DEEP


async def generate_skeleton(concept: str, mood: str = "мрачное фэнтези") -> WorldSkeleton:
    """Генерирует скелет мира по краткой концепции."""
    prompt = f"""Ты — генератор миров для настольной ролевой игры.
Придумай СКЕЛЕТ мира (3-5 предложений) на основе концепции.
Формат ответа — строго JSON:
{{
  "name": "Название мира",
  "setting": "Тип сеттинга (тёмное фэнтези, стимпанк, постапокалипсис...)",
  "feature": "Главная уникальная особенность мира",
  "conflict": "Центральный конфликт",
  "tone": "Общий тон повествования"
}}

Концепция: {concept}
Желаемое настроение: {mood}"""

    messages = [{"role": "user", "content": prompt}]
    result = await call_api(messages, MODEL_NARRATOR_DEEP)
    if result:
        try:
            data = json.loads(result)
            return WorldSkeleton(**data)
        except Exception:
            pass
    # fallback
    return WorldSkeleton(
        name="Новый мир",
        setting="фэнтези",
        feature="неизведанные земли",
        conflict="надвигающаяся тьма",
        tone="мрачное"
    )


async def generate_full_world(skeleton: WorldSkeleton) -> WorldState:
    """На основе утверждённого скелета создаёт полный мир, главный квест и стартовые рельсы."""
    prompt = f"""Ты — генератор миров для НРИ.
На основе скелета мира создай полноценное описание мира и стартовую ситуацию.
Ответ строго в JSON:
{{
  "description": "Детальное описание мира (2-3 абзаца)",
  "main_quest": "Основной квест, который будет предложен партии",
  "starting_location": "Где начинается игра (локация)",
  "hooks": ["Стартовый крючок 1", "Стартовый крючок 2", "Стартовый крючок 3"],
  "atmosphere": ["ключевая", "атмосферная", "деталь"]
}}

Скелет мира:
{json.dumps(skeleton.dict(), ensure_ascii=False)}"""

    messages = [{"role": "user", "content": prompt}]
    # Для полного мира даём больше токенов — 1500
    result = await call_api(messages, MODEL_NARRATOR_DEEP, max_tokens=1500)
    if result:
        try:
            data = json.loads(result)
            return WorldState(
                skeleton=skeleton,
                description=data["description"],
                main_quest=data["main_quest"],
                starting_location=data["starting_location"],
                hooks=data["hooks"],
                atmosphere=data["atmosphere"]
            )
        except Exception:
            pass
    # fallback
    return WorldState(
        skeleton=skeleton,
        description="Мир, полный загадок.",
        main_quest="Выжить.",
        starting_location="Таверна",
        hooks=["Загадочный незнакомец", "Пропавший караван"],
        atmosphere=["туман", "сырость"]
    )