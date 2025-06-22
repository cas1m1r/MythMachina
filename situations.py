import json
from pathlib import Path
from typing import List, Dict, Any


class Situation:
    def __init__(
        self,
        id: str,
        title: str,
        setting: str,
        initial_prompt: str,
        theme: List[str],
        participants: List[str],
        rules: Dict[str, Any]
    ):
        self.id = id
        self.title = title
        self.setting = setting
        self.initial_prompt = initial_prompt
        self.theme = theme
        self.participants = participants
        self.rules = rules

    def to_narrator_prompt(self):
        return f"📜 {self.title}\nSetting: {self.setting}\nConflict: {self.initial_prompt}\nThemes: {', '.join(self.theme)}"


def load_situations(file_path: str):
    """
    Load all situation JSON files from a directory and return a list of Situation objects.
    """
    with open(file_path, "r", encoding="utf-8") as f:
       situations = json.loads(f.read())
    f.close()
    return situations