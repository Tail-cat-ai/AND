"""
D&D AI DM — точка входа.
FastAPI + WebSocket + интеграция всех модулей.
"""
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

from config import RENDER_PORT, HOST, DEBUG
from models import Player, Character, ServerMessage, PlayerMessage, RoomState
from session_manager import session_manager
from rule_engine import roll_d20, check_skill, ability_check, attack_roll, damage_roll
from event_composer import compose_exploration_scene, compose_combat_scene, compose_social_scene
from llm_dispatcher import narrate, narrate_system_message, call_api
from world_generator import generate_skeleton, generate_full_world
from models import WorldSkeleton  # на случай, если понадобится явно

app = FastAPI()

# Хранилище активных WebSocket-соединений: nickname -> WebSocket
active_connections: dict[str, WebSocket] = {}


# ──────────────────────────────────────────────
# Health-check
# ──────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "alive", "service": "D&D AI DM Backend"}


# ──────────────────────────────────────────────
# WebSocket — главный игровой канал
# ──────────────────────────────────────────────
@app.websocket("/ws/{room_id}")
async def game_websocket(websocket: WebSocket, room_id: str):
    await websocket.accept()
    nickname = None

    try:
        # Ожидаем первое сообщение — регистрация игрока
        data = await websocket.receive_text()
        try:
            msg = PlayerMessage.parse_raw(data)
        except Exception:
            msg = PlayerMessage(payload={"nickname": data.strip()})

        nickname = msg.payload.get("nickname", f"Player_{id(websocket)}")

        # Создаём персонажа, если передан
        character = None
        if "character" in msg.payload:
            try:
                character = Character(**msg.payload["character"])
            except Exception:
                pass

        # Регистрируем игрока
        session_manager.add_player(room_id, nickname, character)
        active_connections[nickname] = websocket

        # Уведомляем комнату
        await session_manager.broadcast(
            room_id,
            ServerMessage(
                type="system",
                author="dm",
                content=await narrate_system_message(
                    f"{nickname} присоединяется к партии."
                ),
            ),
            active_connections,
        )

        # Основной цикл обработки сообщений
        while True:
            raw = await websocket.receive_text()
            try:
                msg = PlayerMessage.parse_raw(raw)
            except Exception:
                msg = PlayerMessage(payload={"text": raw})

            if msg.action == "chat":
                await session_manager.broadcast(
                    room_id,
                    ServerMessage(
                        type="chat",
                        author=nickname,
                        content=msg.payload.get("text", ""),
                    ),
                    active_connections,
                )

            elif msg.action == "roll":
                modifier = int(msg.payload.get("modifier", 0))
                advantage = msg.payload.get("advantage", False)
                disadvantage = msg.payload.get("disadvantage", False)
                result = roll_d20(modifier, advantage, disadvantage)
                await session_manager.broadcast(
                    room_id,
                    ServerMessage(
                        type="roll_result",
                        author=nickname,
                        content=f"d20 + {modifier} = {result.total}",
                        data=result.dict(),
                    ),
                    active_connections,
                )

            elif msg.action == "check":
                player = session_manager.get_player(room_id, nickname)
                if player and player.character:
                    skill = msg.payload.get("skill", "perception")
                    dc = int(msg.payload.get("dc", 15))
                    advantage = msg.payload.get("advantage", False)
                    disadvantage = msg.payload.get("disadvantage", False)
                    result, success = check_skill(player.character, skill, dc, advantage, disadvantage)

                    fact = compose_exploration_scene(
                        location=msg.payload.get("location", "неизвестно"),
                        atmosphere=msg.payload.get("atmosphere", ["мрачное подземелье"]),
                        actors=[nickname],
                        active_character=player.character,
                        recent_roll=result,
                        extra_facts={"skill": skill, "dc": dc, "success": success},
                    )
                    narrative = await narrate(fact)

                    await session_manager.broadcast(
                        room_id,
                        ServerMessage(
                            type="narrative",
                            author="dm",
                            content=narrative,
                            data={"roll": result.dict(), "success": success},
                        ),
                        active_connections,
                    )
                else:
                    await session_manager.send_to_player(
                        nickname,
                        ServerMessage(type="system", author="dm", content="Сначала создайте персонажа."),
                        active_connections,
                    )

            elif msg.action == "attack":
                player = session_manager.get_player(room_id, nickname)
                if player and player.character:
                    target_name = msg.payload.get("target", "враг")
                    target_ac = int(msg.payload.get("target_ac", 12))
                    advantage = msg.payload.get("advantage", False)
                    disadvantage = msg.payload.get("disadvantage", False)
                    atk_result, hit = attack_roll(player.character, target_ac, advantage, disadvantage)
                    dmg = None
                    if hit:
                        dmg = damage_roll(1, 6, player.character.get_modifier("strength"))

                    fact = compose_combat_scene(
                        location=msg.payload.get("location", "поле боя"),
                        atmosphere=msg.payload.get("atmosphere", ["звон стали"]),
                        actors=[nickname, target_name],
                        attacker=player.character,
                        target_name=target_name,
                        target_ac=target_ac,
                        attack_roll_result=atk_result,
                        hit=hit,
                        damage=dmg,
                    )
                    narrative = await narrate(fact)

                    await session_manager.broadcast(
                        room_id,
                        ServerMessage(
                            type="narrative",
                            author="dm",
                            content=narrative,
                            data={"roll": atk_result.dict(), "hit": hit, "damage": dmg},
                        ),
                        active_connections,
                    )
                else:
                    await session_manager.send_to_player(
                        nickname,
                        ServerMessage(type="system", author="dm", content="Сначала создайте персонажа."),
                        active_connections,
                    )

            # === Генерация мира ===
            elif msg.action == "create_world":
                concept = msg.payload.get("concept", "")
                mood = msg.payload.get("mood", "мрачное фэнтези")
                skeleton = await generate_skeleton(concept, mood)
                room = session_manager.get_room(room_id)
                if room:
                    room.world_skeleton = skeleton
                await session_manager.broadcast(
                    room_id,
                    ServerMessage(
                        type="system",
                        author="dm",
                        content=f"Скелет мира:\n{skeleton.json(indent=2, ensure_ascii=False)}\n\n"
                                f"Отредактируйте (edit_skeleton) или утвердите (approve_skeleton)."
                    ),
                    active_connections,
                )

            elif msg.action == "edit_skeleton":
                edits = msg.payload.get("edits", "")
                room = session_manager.get_room(room_id)
                if room and room.world_skeleton:
                    prompt = f"""Текущий скелет мира:
{room.world_skeleton.json(indent=2, ensure_ascii=False)}

Игрок хочет внести правки: {edits}

Обнови скелет, сохранив остальные поля без изменений. Ответь строго JSON скелета."""
                    messages = [{"role": "user", "content": prompt}]
                    result = await call_api(messages, "qwen/qwen3.5-27b-writer-derestricted")  # можно подставить MODEL_NARRATOR_DEEP
                    if result:
                        try:
                            new_data = json.loads(result)
                            room.world_skeleton = WorldSkeleton(**new_data)
                        except Exception:
                            pass  # оставляем старый
                    await session_manager.broadcast(
                        room_id,
                        ServerMessage(
                            type="system",
                            author="dm",
                            content=f"Обновлённый скелет:\n{room.world_skeleton.json(indent=2, ensure_ascii=False)}"
                        ),
                        active_connections,
                    )

            elif msg.action == "approve_skeleton":
                room = session_manager.get_room(room_id)
                if room and room.world_skeleton:
                    full_world = await generate_full_world(room.world_skeleton)
                    room.world_state = full_world
                    room.world_skeleton = None
                    await session_manager.broadcast(
                        room_id,
                        ServerMessage(
                            type="system",
                            author="dm",
                            content=f"Мир создан!\n{full_world.json(indent=2, ensure_ascii=False)}"
                        ),
                        active_connections,
                    )

            else:
                await session_manager.send_to_player(
                    nickname,
                    ServerMessage(type="system", author="dm", content=f"Неизвестное действие: {msg.action}"),
                    active_connections,
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[ERROR] {nickname}: {e}")
    finally:
        if nickname:
            active_connections.pop(nickname, None)
            empty = session_manager.remove_player(room_id, nickname)
            if not empty:
                await session_manager.broadcast(
                    room_id,
                    ServerMessage(
                        type="system",
                        author="dm",
                        content=f"{nickname} покидает игру."
                    ),
                    active_connections,
                )


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=RENDER_PORT)