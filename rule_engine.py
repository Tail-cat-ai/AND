"""
Игровая механика D&D: броски кубиков, проверки навыков, бой.
Никакой наррации — только вычисления и флаги.
"""
import random
from typing import Optional, Tuple
from models import Character, RollResult


def roll_d20(modifier: int = 0, advantage: bool = False, disadvantage: bool = False) -> RollResult:
    """
    Бросок d20 с модификатором.
    advantage/disadvantage — бросаем два кубика, берём лучший/худший.
    """
    rolls = [random.randint(1, 20) for _ in range(2 if (advantage or disadvantage) else 1)]

    if advantage:
        chosen = max(rolls)
    elif disadvantage:
        chosen = min(rolls)
    else:
        chosen = rolls[0]

    total = chosen + modifier
    return RollResult(
        dice="d20",
        rolls=rolls,
        modifier=modifier,
        total=total,
        critical_success=(chosen == 20),
        critical_failure=(chosen == 1)
    )


def get_skill_modifier(character: Character, skill: str) -> int:
    """
    Возвращает модификатор персонажа для указанного навыка.
    Сначала ищем в skills, если нет — используем модификатор базовой характеристики.
    """
    skill_lower = skill.lower()

    # Прямой бонус навыка (если задан в листе)
    if skill_lower in character.skills:
        return character.skills[skill_lower]

    # Привязка навыков к характеристикам (D&D 5e)
    skill_to_stat = {
        "athletics": "strength",
        "acrobatics": "dexterity",
        "sleight of hand": "dexterity",
        "stealth": "dexterity",
        "arcana": "intelligence",
        "history": "intelligence",
        "investigation": "intelligence",
        "nature": "intelligence",
        "religion": "intelligence",
        "animal handling": "wisdom",
        "insight": "wisdom",
        "medicine": "wisdom",
        "perception": "wisdom",
        "survival": "wisdom",
        "deception": "charisma",
        "intimidation": "charisma",
        "performance": "charisma",
        "persuasion": "charisma",
    }

    stat = skill_to_stat.get(skill_lower)
    if stat:
        return character.get_modifier(stat)
    return 0


def check_skill(character: Character, skill: str, dc: int,
                advantage: bool = False, disadvantage: bool = False) -> Tuple[RollResult, bool]:
    """
    Проверка навыка против сложности (DC).
    Возвращает (результат_броска, успех/провал).
    """
    modifier = get_skill_modifier(character, skill)
    result = roll_d20(modifier, advantage, disadvantage)
    success = result.total >= dc or result.critical_success
    if result.critical_failure:
        success = False
    return result, success


def ability_check(character: Character, ability: str, dc: int,
                  advantage: bool = False, disadvantage: bool = False) -> Tuple[RollResult, bool]:
    """
    Прямая проверка характеристики (без навыка).
    ability: strength, dexterity, constitution, intelligence, wisdom, charisma
    """
    modifier = character.get_modifier(ability.lower())
    result = roll_d20(modifier, advantage, disadvantage)
    success = result.total >= dc or result.critical_success
    if result.critical_failure:
        success = False
    return result, success


def attack_roll(attacker: Character, target_ac: int,
                advantage: bool = False, disadvantage: bool = False) -> Tuple[RollResult, bool]:
    """
    Бросок атаки против Armor Class цели.
    Возвращает (результат, попал/промазал).
    Пока используем strength для ближнего боя (можно расширить позже).
    """
    modifier = attacker.get_modifier("strength")  # упрощённо, позже добавим выбор характеристики
    result = roll_d20(modifier, advantage, disadvantage)
    hit = result.total >= target_ac or result.critical_success
    if result.critical_failure:
        hit = False
    return result, hit


def damage_roll(dice_count: int, dice_size: int, modifier: int = 0) -> int:
    """
    Бросок урона: например, 2d6+3 → damage_roll(2, 6, 3)
    """
    total = sum(random.randint(1, dice_size) for _ in range(dice_count)) + modifier
    return max(0, total)


def initiative_roll(character: Character) -> RollResult:
    """Бросок инициативы (d20 + модификатор ловкости)."""
    return roll_d20(character.get_modifier("dexterity"))