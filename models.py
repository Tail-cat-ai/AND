"""
Pydantic-модели для D&D AI DM.
Все внутренние модули обмениваются только этими структурами.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

# ──────────────────────────────────────────────
# Базовые перечисления
# ──────────────────────────────────────────────
class RoomState(str, Enum):
    LOBBY = "lobby"
    EXPLORATION = "exploration"
    COMBAT = "combat"
    DIALOGUE = "dialogue"

class ActionType(str, Enum):
    ROLL = "roll"
    CHECK = "check"
    ATTACK = "attack"
    CAST = "cast"
    USE_ITEM = "use_item"
    MOVE = "move"
    TALK = "talk"
    CHAT = "chat"  # обычное сообщение в чат

# ──────────────────────────────────────────────
# Персонаж игрока
# ──────────────────────────────────────────────
class Character(BaseModel):
    name: str
    race: str = "human"
    char_class: str = "fighter"
    level: int = 1
    hp: int = 10
    max_hp: int = 10
    ac: int = 10  # Armor Class
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    skills: Dict[str, int] = Field(default_factory=dict)  # навык -> бонус
    inventory: List[str] = Field(default_factory=list)
    spell_slots: Dict[int, int] = Field(default_factory=dict)  # уровень -> количество

    def get_modifier(self, stat: str) -> int:
        """Возвращает модификатор характеристики по D&D 5e."""
        value = getattr(self, stat, 10)
        return (value - 10) // 2

# ──────────────────────────────────────────────
# Игрок (обёртка над WebSocket + персонаж)
# ──────────────────────────────────────────────
class Player(BaseModel):
    nickname: str
    character: Optional[Character] = None
    is_ready: bool = False

# ──────────────────────────────────────────────
# Игровая комната
# ──────────────────────────────────────────────
class Room(BaseModel):
    id: str
    state: RoomState = RoomState.LOBBY
    players: Dict[str, Player] = Field(default_factory=dict)  # nickname -> Player
    turn_order: List[str] = Field(default_factory=list)  # очерёдность в бою
    active_player_index: int = 0

# ──────────────────────────────────────────────
# Результат броска
# ──────────────────────────────────────────────
class RollResult(BaseModel):
    dice: str = "d20"
    rolls: List[int] = Field(default_factory=list)
    modifier: int = 0
    total: int = 0
    critical_success: bool = False
    critical_failure: bool = False

# ──────────────────────────────────────────────
# NPC
# ──────────────────────────────────────────────
class NPC(BaseModel):
    id: str
    name: str
    role: str = ""
    goal: str = ""
    fear: str = ""
    limit: str = ""  # предел, за который NPC не пойдёт
    attitude: int = 0  # -10 враждебный, 0 нейтральный, +10 дружелюбный
    location: str = ""

# ──────────────────────────────────────────────
# Сухие факты для LLM (схема Event Composer)
# ──────────────────────────────────────────────
class FactJSON(BaseModel):
    scene_type: str = "exploration"
    location: str = ""
    actors: List[str] = Field(default_factory=list)
    facts: Dict[str, Any] = Field(default_factory=dict)
    atmosphere: List[str] = Field(default_factory=list)
    required_style: str = "мрачное фэнтези, сухой реализм, никакой лишней драматизации"

# ──────────────────────────────────────────────
# Входящее сообщение от игрока
# ──────────────────────────────────────────────
class PlayerMessage(BaseModel):
    action: ActionType = ActionType.CHAT
    payload: Dict[str, Any] = Field(default_factory=dict)

# ──────────────────────────────────────────────
# Ответ сервера всем игрокам
# ──────────────────────────────────────────────
class ServerMessage(BaseModel):
    type: str  # "narrative", "roll_result", "system", "chat"
    author: str = "dm"
    content: str = ""
    data: Optional[Dict[str, Any]] = None