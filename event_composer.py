"""
Компоновщик фактажа для LLM-нарратора.
Собирает сухие результаты игровых механик и состояния мира в структуру FactJSON,
которую llm_dispatcher превратит в художественное описание.
"""
from typing import Optional, List, Dict, Any
from models import FactJSON, Character, RollResult, NPC, Room


def compose_exploration_scene(
    location: str,
    atmosphere: List[str],
    actors: List[str],
    active_character: Optional[Character] = None,
    nearby_npcs: Optional[List[NPC]] = None,
    recent_roll: Optional[RollResult] = None,
    extra_facts: Optional[Dict[str, Any]] = None,
) -> FactJSON:
    """
    Собирает фактаж для сцены исследования/перемещения.
    """
    facts: Dict[str, Any] = {}

    if active_character:
        facts["active_character"] = {
            "name": active_character.name,
            "race": active_character.race,
            "class": active_character.char_class,
            "hp": f"{active_character.hp}/{active_character.max_hp}",
        }

    if nearby_npcs:
        facts["nearby_npcs"] = [
            {"name": npc.name, "role": npc.role, "attitude": npc.attitude}
            for npc in nearby_npcs
        ]

    if recent_roll:
        facts["recent_roll"] = {
            "dice": recent_roll.dice,
            "rolls": recent_roll.rolls,
            "modifier": recent_roll.modifier,
            "total": recent_roll.total,
            "critical_success": recent_roll.critical_success,
            "critical_failure": recent_roll.critical_failure,
        }

    if extra_facts:
        facts.update(extra_facts)

    return FactJSON(
        scene_type="exploration",
        location=location,
        actors=actors,
        facts=facts,
        atmosphere=atmosphere,
        required_style="мрачное фэнтези, сухой реализм, минимум драматизации",
    )


def compose_combat_scene(
    location: str,
    atmosphere: List[str],
    actors: List[str],
    attacker: Character,
    target_name: str,
    target_ac: int,
    attack_roll_result: RollResult,
    hit: bool,
    damage: Optional[int] = None,
    extra_facts: Optional[Dict[str, Any]] = None,
) -> FactJSON:
    """
    Собирает фактаж для боевой сцены.
    """
    facts: Dict[str, Any] = {
        "attacker": {
            "name": attacker.name,
            "hp": f"{attacker.hp}/{attacker.max_hp}",
        },
        "target": {
            "name": target_name,
            "ac": target_ac,
        },
        "attack_roll": {
            "rolls": attack_roll_result.rolls,
            "modifier": attack_roll_result.modifier,
            "total": attack_roll_result.total,
            "hit": hit,
            "critical_success": attack_roll_result.critical_success,
            "critical_failure": attack_roll_result.critical_failure,
        },
    }

    if damage is not None:
        facts["damage"] = damage

    if extra_facts:
        facts.update(extra_facts)

    return FactJSON(
        scene_type="combat",
        location=location,
        actors=actors,
        facts=facts,
        atmosphere=atmosphere,
        required_style="мрачное фэнтези, динамичный бой, сухой реализм, акцент на последствия",
    )


def compose_social_scene(
    location: str,
    atmosphere: List[str],
    actors: List[str],
    speaker_npc: NPC,
    active_character: Optional[Character] = None,
    recent_check: Optional[tuple] = None,  # (RollResult, success: bool)
    extra_facts: Optional[Dict[str, Any]] = None,
) -> FactJSON:
    """
    Собирает фактаж для сцены диалога/социального взаимодействия.
    """
    facts: Dict[str, Any] = {
        "npc": {
            "name": speaker_npc.name,
            "role": speaker_npc.role,
            "goal": speaker_npc.goal,
            "fear": speaker_npc.fear,
            "attitude": speaker_npc.attitude,
        }
    }

    if active_character:
        facts["active_character"] = {
            "name": active_character.name,
            "race": active_character.race,
            "class": active_character.char_class,
        }

    if recent_check:
        roll_result, success = recent_check
        facts["social_check"] = {
            "rolls": roll_result.rolls,
            "modifier": roll_result.modifier,
            "total": roll_result.total,
            "success": success,
            "critical_success": roll_result.critical_success,
            "critical_failure": roll_result.critical_failure,
        }

    if extra_facts:
        facts.update(extra_facts)

    return FactJSON(
        scene_type="dialogue",
        location=location,
        actors=actors,
        facts=facts,
        atmosphere=atmosphere,
        required_style="мрачное фэнтези, естественный диалог, NPC действует исходя из своих целей и страхов",
    )


def compose_system_message(
    message: str,
    extra_data: Optional[Dict[str, Any]] = None,
) -> FactJSON:
    """
    Служебное сообщение (игрок присоединился, комната создана и т.п.).
    Не требует LLM, но может быть оформлено как фактаж для единообразия.
    """
    return FactJSON(
        scene_type="system",
        location="",
        actors=[],
        facts={"message": message, **(extra_data or {})},
        atmosphere=[],
        required_style="",
    )