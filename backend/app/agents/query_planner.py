import logging
import json
import time
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

class QueryPlanOutput(BaseModel):
    intent: str = Field("scheme_search", description="Search intent classification")
    category: Optional[str] = Field(None, description="Inferred category e.g. Education, Agriculture")
    target_group: Optional[str] = Field(None, description="Target group e.g. Students, Farmers, Women")
    state: Optional[str] = Field(None, description="Central or Maharashtra")
    keywords: List[str] = Field(default_factory=list, description="Extracted search keywords")

SYSTEM_PLANNER_PROMPT = """
You are a government scheme query planning assistant.
Analyze the user's natural language search prompt and extract structured search parameters into JSON matching:
{
  "intent": "scheme_search",
  "category": "Education" | "Agriculture" | "Housing" | "Social Welfare" | null,
  "target_group": "Students" | "Farmers" | "Women" | "Senior Citizens" | null,
  "state": "Maharashtra" | "Central" | null,
  "keywords": ["keyword1", "keyword2"]
}
"""

class QueryPlannerAgent:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.LLM_API_KEY

    async def plan_query(self, user_prompt: str, user_profile: Dict[str, Any] = None) -> QueryPlanOutput:
        user_profile = user_profile or {}
        prompt_lower = user_prompt.lower()

        # Fallback keyword-based planner if placeholder or offline mode
        if not self.api_key or self.api_key == "placeholder":
            return self._fallback_plan(user_prompt, user_profile)

        try:
            import google.generativeai as genai
            from app.services.llm_logger import log_llm_call
            t0 = time.time()
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            full_prompt = f"{SYSTEM_PLANNER_PROMPT}\n\nUSER SEARCH PROMPT: {user_prompt}"
            response = await model.generate_content_async(
                full_prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            lat = int((time.time() - t0) * 1000)
            await log_llm_call(purpose="query_planning", model="gemini-1.5-flash", latency_ms=lat, success=True)
            data = json.loads(response.text)
            return QueryPlanOutput(**data)
        except Exception as e:
            logger.warning(f"Query planner LLM failed: {str(e)}, using fallback planner")
            from app.services.llm_logger import log_llm_call
            await log_llm_call(purpose="query_planning", model="gemini-1.5-flash", success=False)
            return self._fallback_plan(user_prompt, user_profile)

    def _fallback_plan(self, user_prompt: str, user_profile: Dict[str, Any]) -> QueryPlanOutput:
        p_lower = user_prompt.lower()

        state = None
        if "maharashtra" in p_lower or "mahadbt" in p_lower:
            state = "Maharashtra"
        elif "central" in p_lower or "india" in p_lower or "pm" in p_lower:
            state = "Central"

        category = None
        if any(k in p_lower for k in ["scholarship", "student", "education", "school", "engineering"]):
            category = "Education"
        elif any(k in p_lower for k in ["farmer", "kisan", "agriculture", "pond", "irrigation"]):
            category = "Agriculture"
        elif any(k in p_lower for k in ["house", "housing", "awas"]):
            category = "Housing"
        elif any(k in p_lower for k in ["women", "ladki", "bahin", "widow"]):
            category = "Social Welfare"

        target_group = None
        if "student" in p_lower:
            target_group = "Students"
        elif "farmer" in p_lower or "kisan" in p_lower:
            target_group = "Farmers"
        elif "women" in p_lower or "lady" in p_lower:
            target_group = "Women"

        # Tokenize keywords
        stop_words = {"for", "in", "and", "the", "of", "to", "a", "an", "is", "scheme", "schemes"}
        words = [w.strip() for w in p_lower.split() if len(w.strip()) > 2 and w.strip() not in stop_words]

        return QueryPlanOutput(
            intent="scheme_search",
            category=category,
            target_group=target_group,
            state=state,
            keywords=words
        )
