def create_user_key(user_id: str, flag: str = None):
    if flag:
        from hashlib import sha256

        return sha256(user_id.encode("utf-8")).hexdigest()
    return user_id if user_id.startswith("user") else f"user:{user_id}"


from database.models import (
    Sales,
    Catalog,
    Inventory,
    Creditors,
    Credited,
    OperationExpenses,
)

MODELS = [
    Sales,
    Catalog,
    Inventory,
    Creditors,
    Credited,
    OperationExpenses,
]

from re import compile

# Regex pattern to match datetime.datetime(year, month, day, hour, minute, second, microsecond)
DATETIME_REGEX = compile(
    r"datetime\.datetime\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*(\d+))?(?:\s*,\s*(\d+))?(?:\s*,\s*(\d+))?(?:\s*,\s*(\d+))?\s*\)"
)


def _replacer(match):
    """Converts a matched datetime.datetime tuple string into a standard ISO-8601 string."""
    groups = match.groups()
    # Extract structural arguments, defaulting missing time components to 0
    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
    hour = int(groups[3]) if groups[3] is not None else 0
    minute = int(groups[4]) if groups[4] is not None else 0
    second = int(groups[5]) if groups[5] is not None else 0
    microsecond = int(groups[6]) if groups[6] is not None else 0

    from datetime import datetime

    dt = datetime(year, month, day, hour, minute, second, microsecond)
    # Return as a valid JSON string literal
    return f'"{dt.isoformat()}"'


def decode_json_objects(data: str):
    """
    Safely parses incoming data strings that may accidentally contain raw
    Python datetime string representations.
    """
    if not isinstance(data, str):
        return data

    from json import loads, JSONDecodeError
    from ast import literal_eval

    # 1. Clean the string by replacing datetime.datetime(...) with standard string stamps
    cleaned_data = DATETIME_REGEX.sub(_replacer, data)

    # 2. Standardize single quotes to double quotes if it looks like a Python dict string
    # (ast.literal_eval can handle single quotes, but JSON requires double quotes)
    try:
        return loads(cleaned_data)
    except JSONDecodeError:
        # Fallback to ast.literal_eval if it contains other python-specific structures
        try:
            return literal_eval(cleaned_data)
        except Exception:
            # If everything fails, return the cleaned raw string or raise
            return cleaned_data
            # raise ValueError(f"Failed to parse cleaned data payload: {cleaned_data}")


def clean_str(data: str):
    return data.lower().strip()


def clean_data(data: dict):
    for k, v in data.copy().items():
        data = {}
        if isinstance(v, str):
            data[clean_str(k)] = clean_str(v)
        else:
            data[clean_str(k)] = v
    print("Cleaned data with values: \n", data)
    return data
