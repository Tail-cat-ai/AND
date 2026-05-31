"""
Централизованная конфигурация D&D AI DM.
Все секреты (ключи API) должны задаваться через переменные окружения.
Не коммитьте реальные ключи в репозиторий.
"""
import os

# ──────────────────────────────────────────────
# Сервер
# ──────────────────────────────────────────────
RENDER_PORT: int = int(os.getenv("PORT", "10000"))
HOST: str = os.getenv("HOST", "0.0.0.0")
DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")

# ──────────────────────────────────────────────
# База данных
# ──────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./game.db")

# ──────────────────────────────────────────────
# LLM API (nano-gpt.com)
# ──────────────────────────────────────────────
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_API_URL: str = os.getenv("LLM_API_URL", "https://nano-gpt.com/api/v1/chat/completions")

# Имена моделей — точные названия из nano-gpt
MODEL_NARRATOR_FAST: str = os.getenv("MODEL_NARRATOR_FAST", "Qwen3.5-27B-BlueStar-v3-Derestricted")
MODEL_NARRATOR_DEEP: str = os.getenv("MODEL_NARRATOR_DEEP", "Qwen3.5-27B-BlueStar-v3-Derestricted")
MODEL_NARRATOR_THINKING: str = os.getenv("MODEL_NARRATOR_THINKING", "Qwen3.5-27B-BlueStar-v3-Derestricted")
MODEL_FALLBACK: str = os.getenv("MODEL_FALLBACK", "gryphe/mythomax-l2-13b")
# Параметры генерации
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1000"))
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# ──────────────────────────────────────────────
# Игровые константы
# ──────────────────────────────────────────────
DEFAULT_DIFFICULTY_CLASS: int = 15
MAX_PLAYERS_PER_ROOM: int = 6
NPC_PULSE_INTERVAL_SCENES: int = 3