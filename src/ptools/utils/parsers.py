def parse_human_time(time_str: str) -> float:
    """Parse a human-readable time string into seconds."""
    import re
    time_units = {
        'ms': 0.001,
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800,
        'mo': 2592000,  # Approximate month as 30 days
        'y': 31536000,  # Approximate year as 365 days
    }

    pattern = r'(\d+(\.\d+)?)(ms|mo|[smhdwy])'
    needle  = time_str.lower().strip()
    matches = re.findall(pattern, needle)

    if not matches:
        raise ValueError(f"Invalid time format: {time_str}")

    if not re.fullmatch(r'(\d+(\.\d+)?(ms|mo|[smhdwy]))+', needle):
        raise ValueError(f"Invalid time format: {time_str}")

    total_seconds = sum(float(value) * time_units[unit] for value, _, unit in matches)
    return total_seconds