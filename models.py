"""
Pydantic-модели для D&D AI DM.
Совместимость с Pydantic v2.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from enum import Enum

class RoomState(str, Enum):
    LOBBY = "lobby"
    EXPLORATION = "exploration"
    COMBAT = "combat"
    DIALOGUE = "dialogue"

class Character(BaseModel):
    name: str
    race: str = "human"
    char_class: str = "fighter"
    level: int = 1
    hp: int = 10
    max_hp: int = 10
    ac: int = 10
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    skills: Dict[str, int] = Field(default_factory=dict)
    inventory: List[str] = Field(default_factory=list)
    spell_slots: Dict[int, int] = Field(default_factory=dict)

    def get_modifier(self, stat: str) -> int:
        value = getattr(self, stat, 10)
        return (value - 10) // 2

class Player(BaseModel):
    nickname: str
    character: Optional[Character] = None
    is_ready: bool = False

class WorldSkeleton(BaseModel):
    name: str = "Новый мир"
    setting: str = "фэнтези"
    feature: str = ""
    conflict: str = ""
    tone: str = "мрачное"

class WorldState(BaseModel):
    skeleton: WorldSkeleton
    description: str = ""
    main_quest: str = ""
    starting_location: str = ""
    hooks: List[str] = Field(default_factory=list)
    atmosphere: List[str] = Field(default_factory=list)

class Room(BaseModel):
    id: str
    state: RoomState = RoomState.LOBBY
    players: Dict[str, Player] = Field(default_factory=dict)
    turn_order: List[str] = Field(default_factory=list)
    active_player_index: int = 0
    world_skeleton: Optional[WorldSkeleton] = None
    world_state: Optional[WorldState] = None

class RollResult(BaseModel):
    dice: str = "d20"
    rolls: List[int] = Field(default_factory=list)
    modifier: int = 0
    total: int = 0
    critical_success: bool = False
    critical_failure: bool = False

class NPC(BaseModel):
    id: str
    name: str
    role: str = ""
    goal: str = ""
    fear: str = ""
    limit: str = ""
    attitude: int = 0
    location: str = ""

class FactJSON(BaseModel):
    scene_type: str = "exploration"
    location: str = ""
    actors: List[str] = Field(default_factory=list)
    facts: Dict[str, Any] = Field(default_factory=dict)
    atmosphere: List[str] = Field(default_factory=list)
    required_style: str = "мрачное фэнтези, сухой реализм, никакой лишней драматизации"

class PlayerMessage(BaseModel):
    action: str = "chat"
    payload: Dict[str, Any] = Field(default_factory=dict)

class ServerMessage(BaseModel):
    type: str
    author: str = "dm"
    content: str = ""
    data: Optional[Dict[str, Any]] = None

    def model_dump_json(self, **kwargs):
        # для обратной совместимости, но не обязательно
        return super().model_dump_json(**kwargs)