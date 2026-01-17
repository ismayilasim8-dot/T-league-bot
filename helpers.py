"""
T-League Bot - Вспомогательные функции
"""
from datetime import datetime
from typing import Tuple, Optional

def format_datetime(dt: datetime, format: str = "%d.%m.%Y %H:%M") -> str:
    """
    Форматирование даты и времени
    
    Args:
        dt: Объект datetime
        format: Формат строки (по умолчанию "%d.%m.%Y %H:%M")
    
    Returns:
        Отформатированная строка
    """
    return dt.strftime(format)

def validate_score(score_text: str) -> Optional[Tuple[int, int]]:
    """
    Валидация и парсинг счёта матча
    
    Args:
        score_text: Строка со счётом в формате "X:Y"
    
    Returns:
        Кортеж (score1, score2) или None если формат неверный
    """
    try:
        parts = score_text.strip().split(":")
        if len(parts) != 2:
            return None
        
        score1 = int(parts[0])
        score2 = int(parts[1])
        
        if score1 < 0 or score2 < 0:
            return None
        
        return (score1, score2)
    except (ValueError, IndexError):
        return None

def get_match_result_emoji(my_score: int, opponent_score: int) -> str:
    """
    Получение эмодзи результата матча
    
    Args:
        my_score: Мой счёт
        opponent_score: Счёт соперника
    
    Returns:
        Эмодзи результата
    """
    if my_score > opponent_score:
        return "✅"
    elif my_score < opponent_score:
        return "❌"
    else:
        return "➖"

def format_winrate(wins: int, total_matches: int) -> str:
    """
    Форматирование winrate
    
    Args:
        wins: Количество побед
        total_matches: Всего матчей
    
    Returns:
        Отформатированный winrate в процентах
    """
    if total_matches == 0:
        return "0.0%"
    
    winrate = (wins / total_matches) * 100
    return f"{winrate:.1f}%"

def format_streak(streak: int) -> str:
    """
    Форматирование серии побед/поражений
    
    Args:
        streak: Текущая серия (положительная - победы, отрицательная - поражения)
    
    Returns:
        Отформатированная строка с серией
    """
    if streak > 0:
        return f"🔥 {streak}W"
    elif streak < 0:
        return f"❄️ {abs(streak)}L"
    else:
        return "➖"

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Обрезание текста до указанной длины
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина
    
    Returns:
        Обрезанный текст с многоточием если необходимо
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def parse_deadline(deadline_text: str) -> Optional[datetime]:
    """
    Парсинг дедлайна из текста
    
    Args:
        deadline_text: Строка с датой в формате "ДД.ММ.ГГГГ ЧЧ:ММ"
    
    Returns:
        Объект datetime или None если формат неверный
    """
    try:
        return datetime.strptime(deadline_text.strip(), "%d.%m.%Y %H:%M")
    except ValueError:
        return None

def get_status_emoji(status: str) -> str:
    """
    Получение эмодзи для статуса
    
    Args:
        status: Статус (tournament/match)
    
    Returns:
        Соответствующий эмодзи
    """
    status_emojis = {
        # Турниры
        "registration": "🟡",
        "active": "🟢",
        "finished": "🔴",
        # Матчи
        "scheduled": "⏳",
        "pending": "⌛",
        "confirmed": "✅",
        "disputed": "⚠️",
        "technical": "🚫"
    }
    
    return status_emojis.get(status, "❓")

def calculate_goal_difference(goals_for: int, goals_against: int) -> str:
    """
    Расчёт и форматирование разницы мячей
    
    Args:
        goals_for: Забитые голы
        goals_against: Пропущенные голы
    
    Returns:
        Отформатированная разница (+X или -X)
    """
    diff = goals_for - goals_against
    if diff > 0:
        return f"+{diff}"
    return str(diff)

def is_valid_telegram_id(user_id: int) -> bool:
    """
    Проверка валидности Telegram ID
    
    Args:
        user_id: ID пользователя
    
    Returns:
        True если ID валидный
    """
    return isinstance(user_id, int) and user_id > 0

def format_tournament_format(format_type: str) -> str:
    """
    Форматирование типа турнира
    
    Args:
        format_type: Тип турнира
    
    Returns:
        Читаемое название формата
    """
    formats = {
        "round_robin": "⚽ Круговой турнир",
        "playoff": "🏆 Плей-офф",
        "swiss": "🎲 Швейцарская система"
    }
    
    return formats.get(format_type, "❓ Неизвестный формат")