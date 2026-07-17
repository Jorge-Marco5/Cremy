def format_duration(nanoseconds):
    if nanoseconds is None:
        return "N/A"

    seconds = nanoseconds / 1_000_000_000

    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.0f}s"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        remaining_seconds = (seconds % 3600) % 60
        return f"{hours}h {remaining_minutes}m {remaining_seconds:.0f}s"
    else:
        days = int(seconds // 86400)
        remaining_hours = int((seconds % 86400) // 3600)
        remaining_minutes = int(((seconds % 86400) % 3600) // 60)
        remaining_seconds = ((seconds % 86400) % 3600) % 60
        return f"{days}d {remaining_hours}h {remaining_minutes}m {remaining_seconds:.0f}s"