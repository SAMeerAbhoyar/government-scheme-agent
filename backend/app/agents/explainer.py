import re
import json
import logging
import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.services.matching import MatchResult, RuleResultDetail
from app.core.config import settings

logger = logging.getLogger(__name__)

MANDATORY_DISCLAIMER = "\n\n*Note: Your profile appears to match the currently retrieved eligibility information. Final eligibility is determined by the relevant authority.*"

# In-memory explanation cache: (scheme_id + content_hash + profile_hash) -> explanation_text
_EXPLANATION_CACHE: Dict[str, str] = {}

def compute_profile_hash(profile_data: Dict[str, Any]) -> str:
    s = json.dumps(profile_data, sort_keys=True, default=str)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def extract_numbers_from_text(text: str) -> List[float]:
    """Extracts numeric values from text (integers & floats)."""
    # Remove commas in numbers like 2,50,000 -> 250000
    cleaned_text = re.sub(r'(\d+),(\d+)', r'\1\2', text)
    matches = re.findall(r'\b\d+(?:\.\d+)?\b', cleaned_text)
    results = []
    for m in matches:
        try:
            results.append(float(m))
        except ValueError:
            pass
    return results

def get_allowed_numbers_from_match_result(match_result: MatchResult) -> List[float]:
    """Collects all valid numbers present in the input match result and rule evaluation details."""
    allowed = []

    def add_num(val: Any):
        if isinstance(val, (int, float)):
            allowed.append(float(val))
        elif isinstance(val, str):
            extracted = extract_numbers_from_text(val)
            allowed.extend(extracted)
        elif isinstance(val, (list, tuple)):
            for item in val:
                add_num(item)

    add_num(match_result.scheme_name)
    for rule in match_result.rule_results:
        add_num(rule.required_value)
        add_num(rule.user_value)
        if rule.source_quote:
            add_num(rule.source_quote)

    if match_result.extraction_confidence:
        allowed.append(float(match_result.extraction_confidence))

    return allowed

def verify_explanation_facts(explanation_text: str, match_result: MatchResult) -> bool:
    """
    Guardrail Inspector:
    Verifies that every number mentioned in the generated explanation text
    exists in the input MatchResult.
    """
    text_numbers = extract_numbers_from_text(explanation_text)
    allowed_numbers = get_allowed_numbers_from_match_result(match_result)

    # Convert to set of rounded floats for comparison
    allowed_set = {round(n, 2) for n in allowed_numbers}

    for num in text_numbers:
        rounded_num = round(num, 2)
        # Allow common formatting numbers (e.g. 1, 2, 3 bullet numbers or 100 percentage)
        if rounded_num in (1.0, 2.0, 3.0, 4.0, 5.0, 100.0):
            continue
        if rounded_num not in allowed_set:
            logger.warning(
                f"Explainer Guardrail Rejection: Fabricated/unverified number '{num}' "
                f"found in generated explanation. Allowed numbers: {allowed_set}"
            )
            return False

    return True

def generate_template_explanation(match_result: MatchResult) -> str:
    lines = []
    if match_result.status == "potentially_relevant":
        lines.append(f"### Why am I seeing this?")
        lines.append(f"You meet all verified eligibility rules for **{match_result.scheme_name}**.")
        for r in match_result.rule_results:
            if r.result == "match":
                lines.append(f"- **{r.field.replace('_', ' ').title()}**: Matches required condition `{r.op} {r.required_value}` (Your value: `{r.user_value}`).")
    
    elif match_result.status == "cannot_determine":
        lines.append(f"### Additional Profile Data Required")
        lines.append(f"You may be eligible for **{match_result.scheme_name}**, but additional profile details are needed.")
        if match_result.missing_fields:
            lines.append(f"- Missing fields: {', '.join([f.replace('_', ' ').title() for f in match_result.missing_fields])}.")

    else: # not_matching
        lines.append(f"### Why don't I match?")
        lines.append(f"Your profile does not satisfy one or more required criteria for **{match_result.scheme_name}**:")
        for r in match_result.rule_results:
            if r.result == "no_match":
                lines.append(f"- **{r.field.replace('_', ' ').title()}**: Required `{r.op} {r.required_value}` vs Your value `{r.user_value}`.")

    if match_result.unverified:
        lines.append("\n*Warning: This scheme information is unverified and pending administrator review.*")

    lines.append(MANDATORY_DISCLAIMER)
    return "\n".join(lines)


class RecommendationExplainerAgent:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.LLM_API_KEY

    async def explain(self, profile_data: Dict[str, Any], match_result: MatchResult) -> str:
        return await self.explain_match(match_result=match_result, profile_data=profile_data)

    async def explain_match(
        self,
        match_result: MatchResult,
        profile_data: Dict[str, Any],
        scheme_version_hash: str = "v1"
    ) -> str:
        # Check explanation cache
        p_hash = compute_profile_hash(profile_data)
        cache_key = f"{match_result.scheme_id}_{scheme_version_hash}_{p_hash}"

        if cache_key in _EXPLANATION_CACHE:
            return _EXPLANATION_CACHE[cache_key]

        # Use deterministic template if offline or placeholder key
        if not self.api_key or self.api_key == "placeholder":
            tmpl = generate_template_explanation(match_result)
            _EXPLANATION_CACHE[cache_key] = tmpl
            return tmpl

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = f"""
            You are a helpful government scheme recommendation explainer.
            Generate a concise, clear explanation based ONLY on the structured match result below.

            MATCH RESULT STRUCTURED DATA:
            {match_result.model_dump_json(indent=2)}

            INSTRUCTIONS:
            1. If status is 'potentially_relevant', write section 'Why am I seeing this?'.
            2. If status is 'not_matching' or 'cannot_determine', write section 'Why don't I match?' detailing required vs user value.
            3. Do NOT invent numbers, dates, or facts not present in the input.
            """

            response = await model.generate_content_async(prompt)
            explanation_text = response.text.strip()

            # Execute Guardrail Fact Inspection
            if not verify_explanation_facts(explanation_text, match_result):
                logger.warning("Explainer guardrail failed. Discarding LLM output and using template.")
                explanation_text = generate_template_explanation(match_result)
            else:
                if MANDATORY_DISCLAIMER not in explanation_text:
                    explanation_text += MANDATORY_DISCLAIMER

            _EXPLANATION_CACHE[cache_key] = explanation_text
            return explanation_text

        except Exception as e:
            logger.error(f"Explainer LLM error: {str(e)}. Using fallback template.")
            tmpl = generate_template_explanation(match_result)
            _EXPLANATION_CACHE[cache_key] = tmpl
            return tmpl
