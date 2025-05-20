from datetime import datetime, timedelta
import calendar

def get_date_range(date_str):
    parts = date_str.split("-")
    if len(parts) == 1:
        year = int(parts[0])
        start = datetime(year, 1, 1)
        end = datetime(year + 1, 1, 1)
    elif len(parts) == 2:
        year, month = int(parts[0]), int(parts[1])
        start = datetime(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end = datetime(year, month, last_day) + timedelta(days=1)
    elif len(parts) == 3:
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        start = datetime(year, month, day)
        end = start + timedelta(days=1)
    else:
        raise ValueError("Formato de data inválido")
    
    return {
        "$gte": start.strftime("%Y-%m-%d"),
        "$lt": end.strftime("%Y-%m-%d")
    }