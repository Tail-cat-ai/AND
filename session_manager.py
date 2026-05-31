"""
Менеджер игровых комнат и подключений.
Хранит состояние комнат в памяти, управляет игроками, рассылает сообщения.
"""
from typing import Dict, Optional
from fastapi import WebSocket
from models import Room, Player, Character, ServerMessage, RoomState
import json


class SessionManager:
    def __init__(self):
        # room_id -> Room
        self.rooms: Dict[str, Room] = {}

    def create_room(self, room_id: str) -> Room:
        """Создать новую комнату или вернуть существующую."""
        if room_id not in self.rooms:
            self.rooms[room_id] = Room(id=room_id)
        return self.rooms[room_id]

    def add_player(self, room_id: str, nickname: str, character: Optional[Character] = None) -> Player:
        """Добавить игрока в комнату. Если комната не существует, создаёт её."""
        room = self.create_room(room_id)
        if nickname in room.players:
            # Игрок с таким ником уже есть — возвращаем существующего (переподключение)
            return room.players[nickname]

        player = Player(nickname=nickname, character=character, is_ready=character is not None)
        room.players[nickname] = player
        return player

    def remove_player(self, room_id: str, nickname: str) -> bool:
        """Удалить игрока из комнаты. Возвращает True, если комната опустела и была удалена."""
        if room_id not in self.rooms:
            return False
        room = self.rooms[room_id]
        if nickname in room.players:
            del room.players[nickname]
        if not room.players:
            del self.rooms[room_id]
            return True
        return False

    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id)

    def get_player(self, room_id: str, nickname: str) -> Optional[Player]:
        room = self.get_room(room_id)
        if room:
            return room.players.get(nickname)
        return None

    async def broadcast(self, room_id: str, message: ServerMessage, websockets: Dict[str, WebSocket]):
        """Разослать сообщение всем игрокам в комнате, у которых есть активный WebSocket."""
        room = self.get_room(room_id)
        if not room:
            return
        msg_json = message.json()
        for nickname in room.players:
            ws = websockets.get(nickname)
            if ws:
                try:
                    await ws.send_text(msg_json)
                except Exception:
                    pass  # соединение могло уже закрыться

    async def send_to_player(self, nickname: str, message: ServerMessage, websockets: Dict[str, WebSocket]):
        """Отправить сообщение конкретному игроку."""
        ws = websockets.get(nickname)
        if ws:
            try:
                await ws.send_text(message.json())
            except Exception:
                pass

    def set_room_state(self, room_id: str, state: RoomState):
        room = self.get_room(room_id)
        if room:
            room.state = state

    def next_turn(self, room_id: str) -> Optional[str]:
        """Передать ход следующему игроку в порядке очереди (для боя)."""
        room = self.get_room(room_id)
        if not room or not room.turn_order:
            return None
        room.active_player_index = (room.active_player_index + 1) % len(room.turn_order)
        return room.turn_order[room.active_player_index]


# Глобальный экземпляр
session_manager = SessionManager()