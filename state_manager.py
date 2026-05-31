"""
Менеджер состояния мира: сохранение и загрузка в JSON-файл.
"""
import json
import os
from typing import Optional
from models import WorldState

WORLDS_FILE = "worlds.json"

def _load_all() -> dict:
    if not os.path.exists(WORLDS_FILE):
        return {}
    with open(WORLDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_all(data: dict):
    with open(WORLDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_world(room_id: str, world: WorldState):
    """Сохраняет состояние мира для комнаты."""
    data = _load_all()
    data[room_id] = world.dict()
    _save_all(data)

def load_world(room_id: str) -> Optional[WorldState]:
    """Загружает состояние мира для комнаты, если оно есть."""
    data = _load_all()
    if room_id in data:
        return WorldState(**data[room_id])
    return None