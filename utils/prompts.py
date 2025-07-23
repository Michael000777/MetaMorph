import json 
from pathlib import Path

PROMPT_PATH = Path(__file__).parent.parent/ "prompts" / "prompts.json"

def load_prompts() -> dict:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
    

def get_prompt(key: str) -> str:
    prompts = load_prompts()
    return prompts.get(key, "")
