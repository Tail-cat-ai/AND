"""
Генератор игрового мира.
"""
import json
from models import WorldSkeleton, WorldState
from llm_dispatcher import call_api

async def generate_skeleton(concept: str, mood: str = "мрачное фэнтези") -> WorldSkeleton:
    prompt = f"""Ты — генератор миров для НРИ. Придумай скелет мира (строго JSON):
{{
  "name": "...",
  "setting": "...",
  "feature": "...",
  "conflict": "...",
  "tone": "..."
}}
Концепция: {concept}
Настроение: {mood}"""
    messages = [{"role": "user", "content": prompt}]
    result = await call_api(messages, "gryphe/mythomax-l2-13b")
    if result:
        try:
            data = json.loads(result)
            return WorldSkeleton(**data)
        except:
            pass
    return WorldSkeleton()

async def generate_full_world(skeleton: WorldSkeleton) -> WorldState:
    prompt = f"""Создай полный мир на основе скелета (строго JSON):
{{
  "description": "...",
  "main_quest": "...",
  "starting_location": "...",
  "hooks": ["...", "..."],
  "atmosphere": ["..."]
}}
Скелет:
{skeleton.model_dump_json(indent=2)}"""
    messages = [{"role": "user", "content": prompt}]
    result = await call_api(messages, "gryphe/mythomax-l2-13b", max_tokens=1500)
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
        except:
            pass
    return WorldState(skeleton=skeleton)