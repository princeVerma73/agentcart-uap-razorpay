import os
import json
import httpx

from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field
from config import settings

class BuyerIntent(BaseModel):
    query: str
    category: Optional[str] = None
    budget: Optional[float] = None
    quantity: int = Field(default=1, ge=1)
    use_case: Optional[str] = None
    required_features: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)

class GeminiIntentParser:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY

    async def parse_intent(self, goal: str, max_user_budget: Optional[float] = None) -> Tuple[Optional[BuyerIntent], bool, Optional[str]]:
        """
        Parse natural language goal into structured BuyerIntent using Gemini API.
        Returns: (intent: Optional[BuyerIntent], fallback_used: bool, error_reason: Optional[str])
        """
        if not self.api_key or not self.api_key.strip():
            return None, True, "GEMINI_API_KEY is missing or empty"

        model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"

        
        system_prompt = (
            "You are an intent parser for an autonomous e-commerce buyer agent. "
            "Extract structured search intent parameters from the user purchase goal. "
            "Categories available: accessories, cables, peripherals, pantry. "
            "Do NOT invent product IDs, prices, or stock numbers."
        )
        
        user_prompt = f"Goal: '{goal}'. Max budget constraint: ₹{max_user_budget if max_user_budget else 'Unspecified'}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n{user_prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING"},
                        "category": {"type": "STRING"},
                        "budget": {"type": "NUMBER"},
                        "quantity": {"type": "INTEGER"},
                        "use_case": {"type": "STRING"},
                        "required_features": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "exclusions": {"type": "ARRAY", "items": {"type": "STRING"}}
                    },
                    "required": ["query"]
                }
            }
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    return None, True, f"Gemini API returned status code {response.status_code}: {response.text[:100]}"

                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return None, True, "Gemini API returned empty candidate response"

                text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if not text_content:
                    return None, True, "Gemini API text response was empty"

                parsed_json = json.loads(text_content)
                intent = BuyerIntent(**parsed_json)

                if intent.budget is None and max_user_budget is not None:
                    intent.budget = max_user_budget

                return intent, False, None

        except httpx.TimeoutException:
            return None, True, "Gemini API request timed out (5.0s limit)"
        except Exception as e:
            return None, True, f"Gemini intent parsing failed: {str(e)}"

gemini_intent_parser = GeminiIntentParser()
