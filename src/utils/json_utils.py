from typing import Optional, Any
import os
import json
import json_repair


def parse_json(text):
    try:
        return json_repair.loads(text)
    except json.JSONDecodeError:
        return None


def save_json(data, save_path: Optional[str] = None, indent=2):
    if save_path is None:
        save_path = os.path.join("output")
    os.makedirs(save_path, exist_ok=True)

    file_path = os.path.join(save_path, "work_pause_activity_logs.json")
    with open(file_path, mode="w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=indent))


def load_json(file_path: str, default: Optional[Any] = None, use_repair: bool = True):
    if not os.path.exists(file_path):
        return default

    try:
        with open(file_path, mode="r", encoding="utf-8") as f:
            text = f.read()

        if not text.strip():
            return default

        if use_repair:
            try:
                return json_repair.loads(text)
            except (ValueError, json.JSONDecodeError):
                # Fallback to strict JSON if repair fails
                return json.loads(text)
        else:
            return json.loads(text)
    except (OSError, ValueError, json.JSONDecodeError):
        return default


def main():
    """Entry Point for the Program."""
    print(
        f"Welcome from `{os.path.basename(__file__).split('.')[0]}` Module. Nothing to do ^_____^!"
    )

    print(load_json("logs.json"))


if __name__ == "__main__":
    main()
