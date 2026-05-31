"""
Генератор игрового мира (русский язык, фактологический стиль).
"""
import json
from models import WorldSkeleton, WorldState
from llm_dispatcher import call_api

def _extract_json(text: str) -> str:
    text = text.strip()
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text

async def generate_skeleton(concept: str, mood: str = "мрачное фэнтези") -> WorldSkeleton:
    prompt = f"""Создай СКЕЛЕТ мира для настольной ролевой игры. Отвечай **строго** JSON-объектом без лишних слов.
Язык: русский.
Поля:
- name: название мира (1-3 слова)
- setting: тип сеттинга (например, тёмное фэнтези, стимпанк, постапокалипсис)
- feature: главная уникальная особенность мира (одно предложение)
- conflict: центральный конфликт (одно предложение)
- tone: общий тон повествования (одно-два слова)

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
    return WorldSkeleton(name="LLM не ответила")

async def generate_full_world(skeleton: WorldSkeleton) -> WorldState:
    prompt = f"""Создай полное описание мира для ведущего. Отвечай **строго** JSON-объектом без лишнего текста.
Язык: русский.
Стиль: предельно фактологический, без художественных описаний, только суть.
Поля:
- description: краткое описание мира (2-4 предложения, только факты)
- main_quest: главный квест (1-2 предложения)
- starting_location: стартовая локация (название и 1-2 факта о ней)
- hooks: список из 2-3 стартовых сюжетных крючков (конкретные события, с которыми сталкиваются игроки)
- atmosphere: список из 3-5 ключевых деталей окружения (запахи, звуки, визуальные особенности)
- factions: список из 1-2 фракций, каждая — объект {{"name": "...", "description": "..."}}
- locations: список из 2-3 ключевых локаций, каждая — объект {{"name": "...", "description": "..."}}

Скелет мира:
{skeleton.model_dump_json(indent=2, ensure_ascii=False)}"""

    messages = [{"role": "user", "content": prompt}]
    result = await call_api(messages, "gryphe/mythomax-l2-13b", max_tokens=2000)
    if result:
        json_str = _extract_json(result)
        try:
            data = json.loads(json_str)
            # Парсим factions и locations как списки объектов
            factions = [Faction(**f) for f in data.get("factions", [])]
            locations = [Location(**l) for l in data.get("locations", [])]
            return WorldState(
                skeleton=skeleton,
                description=data.get("description", ""),
                main_quest=data.get("main_quest", ""),
                starting_location=data.get("starting_location", ""),
                hooks=data.get("hooks", []),
                atmosphere=data.get("atmosphere", []),
                factions=factions,
                locations=locations
            )
        except Exception as e:
            return WorldState(
                skeleton=skeleton,
                description=f"Ошибка JSON: {e}\n\nОтвет модели:\n{result[:500]}"
            )
    return WorldState(
        skeleton=skeleton,
        description="LLM не ответила."
    )