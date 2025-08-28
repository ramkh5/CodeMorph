
import os, json
from typing import Dict, Any, Optional
from openai import OpenAI

class OpenAIClient:
    """
    Thin wrapper to call Chat Completions with system+user prompts and get text back.
    Expects OPENAI_API_KEY in env.
    """
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.2):
        self.model = model
        self.temperature = temperature
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY env var is required for non --dry-run mode.")
        self.client = OpenAI(api_key=api_key)

    def complete_json(self, system_prompt: str, user_prompt: str, response_format: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Returns dict parsed from model output. Assumes the model returns JSON in the message content.
        """
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        text = resp.choices[0].message.content
        json_str = self._extract_json(text)
        try:
            return json.loads(json_str)
        except Exception:
            cleaned = json_str.strip().strip("`")
            return json.loads(cleaned)

    @staticmethod
    def _extract_json(text: str) -> str:
        import re
        fence = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.S)
        if fence:
            return fence.group(1)
        fence = re.search(r"```\s*(\{.*?\})\s*```", text, flags=re.S)
        if fence:
            return fence.group(1)
        return text
