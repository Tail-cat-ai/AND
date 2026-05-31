"""
D&D AI DM — точка входа.
FastAPI + WebSocket + интеграция всех модулей.
"""
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

from config import RENDER_PORT, HOST, DEBUG
from models import Player, Character, ServerMessage, PlayerMessage, RoomState
from session_manager import session_manager
from rule_engine import roll_d20, check_skill, attack_roll, damage_roll
from event_composer import compose_exploration_scene, compose_combat_scene, compose_social_scene
from llm_dispatcher import narrate, narrate_system_message, call_api
from world_generator import generate_skeleton, generate_full_world
from models import WorldSkeleton

app = FastAPI()

active_connections: dict[str, WebSocket] = {}

@app.get("/")
async def root():
    return {"status": "alive", "service": "D&D AI DM Backend"}

@app.websocket("/ws/{room_id}")
async def game_websocket(websocket: WebSocket, room_id: str):
    await websocket.accept()
    nickname = None

    try:
        data = await websocket.receive_text()
        try:
            msg = PlayerMessage.model_validate_json(data)
        except Exception:
            msg = PlayerMessage(payload={"nickname": data.strip()})

        nickname = msg.payload.get("nickname", f"Player_{id(websocket)}")

        character = None
        if "character" in msg.payload:
            try:
                character = Character(**msg.payload["character"])
            except Exception:
                pass

        session_manager.add_player(room_id, nickname, character)
        active_connections[nickname] = websocket

        await session_manager.broadcast(
            room_id,
            ServerMessage(
                type="system",
                author="dm",
                content=await narrate_system_message(f"{nickname} присоединяется к партии.")
            ),
            active_connections,
        )

        while True:
            raw = await websocket.receive_text()
            try:
                msg = PlayerMessage.model_validate_json(raw)
            except Exception:
                msg = PlayerMessage(payload={"text": raw})

            action = msg.action
            payload = msg.payload

            if action == "chat":
                await session_manager.broadcast(
                    room_id,
                    ServerMessage(type="chat", author=nickname, content=payload.get("text", "")),
                    active_connections,
                )
            elif action == "roll":
                modifier = int(payload.get("modifier", 0))
                advantage = payload.get("advantage", False)
                disadvantage = payload.get("disadvantage", False)
                result = roll_d20(modifier, advantage, disadvantage)
                await session_manager.broadcast(
                    room_id,
                    ServerMessage(
                        type="roll_result",
                        author=nickname,
                        content=f"d20 + {modifier} = {result.total}",
                        data=result.model_dump(mode='python')
                    ),
                    active_connections,
                )
            elif action == "check":
                player = session_manager.get_player(room_id, nickname)
                if player and player.character:
                    skill = payload.get("skill", "perception")
                    dc = int(payload.get("dc", 15))
                    advantage = payload.get("advantage", False)
                    disadvantage = payload.get("disadvantage", False)
                    result, success = check_skill(player.character, skill, dc, advantage, disadvantage)
                    fact = compose_exploration_scene(
                        location=payload.get("location", "неизвестно"),
                        atmosphere=payload.get("atmosphere", ["мрачное подземелье"]),
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
                            data={"roll": result.model_dump(mode='python'), "success": success},
                        ),
                        active_connections,
                    )
                else:
                    await session_manager.send_to_player(
                        nickname,
                        ServerMessage(type="system", author="dm", content="Сначала создайте персонажа."),
                        active_connections,
                    )
            elif action == "attack":
                player = session_manager.get_player(room_id, nickname)
                if player and player.character:
                    target_name = payload.get("target", "враг")
                    target_ac = int(payload.get("target_ac", 12))
                    advantage = payload.get("advantage", False)
                    disadvantage = payload.get("disadvantage", False)
                    atk_result, hit = attack_roll(player.character, target_ac, advantage, disadvantage)
                    dmg = None
                    if hit:
                        dmg = damage_roll(1, 6, player.character.get_modifier("strength"))
                    fact = compose_combat_scene(
                        location=payload.get("location", "поле боя"),
                        atmosphere=payload.get("atmosphere", ["звон стали"]),
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
                            data={"roll": atk_result.model_dump(mode='python'), "hit": hit, "damage": dmg},
                        ),
                        active_connections,
                    )
                else:
                    await session_manager.send_to_player(
                        nickname,
                        ServerMessage(type="system", author="dm", content="Сначала создайте персонажа."),
                        active_connections,
                    )
            elif action == "create_world":
                concept = payload.get("concept", "")
                mood = payload.get("mood", "мрачное фэнтези")
                skeleton = await generate_skeleton(concept, mood)
                room = session_manager.get_room(room_id)
                if room:
                    room.world_skeleton = skeleton
                await session_manager.broadcast(
                    room_id,
                    ServerMessage(
                        type="system",
                        author="dm",
                        content=f"Скелет мира:\n{skeleton.model_dump_json(indent=2)}\n\nОтредактируйте (edit_skeleton) или утвердите (approve_skeleton)."
                    ),
                    active_connections,
                )
            elif action == "edit_skeleton":
                edits = payload.get("edits", "")
                room = session_manager.get_room(room_id)
                if room and room.world_skeleton:
                    prompt = f"""Текущий скелет мира:
{room.world_skeleton.model_dump_json(indent=2)}

Игрок хочет внести правки: {edits}

Обнови скелет, сохранив остальные поля без изменений. Ответь строго JSON скелета."""
                    messages = [{"role": "user", "content": prompt}]
                    result = await call_api(messages, "gryphe/mythomax-l2-13b")
                    if result:
                        try:
                            new_data = json.loads(result)
                            room.world_skeleton = WorldSkeleton(**new_data)
                        except Exception:
                            pass
                    await session_manager.broadcast(
                        room_id,
                        ServerMessage(
                            type="system",
                            author="dm",
                            content=f"Обновлённый скелет:\n{room.world_skeleton.model_dump_json(indent=2)}"
                        ),
                        active_connections,
                    )
            elif action == "approve_skeleton":
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
                            content=f"Мир создан!\n{full_world.model_dump_json(indent=2)}"
                        ),
                        active_connections,
                    )
            else:
                await session_manager.send_to_player(
                    nickname,
                    ServerMessage(type="system", author="dm", content=f"Неизвестное действие: {action}"),
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