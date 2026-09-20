from typing import List, Dict, Any, Optional

QUESTION_TEMPLATES = {
    "annual_income": {
        "field": "annual_income",
        "category": "Financial",
        "question_text": "What is your total annual family income in INR (₹)?",
        "input_type": "number",
        "placeholder": "e.g. 250000",
        "options": None
    },
    "social_category": {
        "field": "social_category",
        "category": "Social & Category",
        "question_text": "Which social category do you belong to?",
        "input_type": "select",
        "options": [
            {"label": "General", "value": "General"},
            {"label": "OBC", "value": "OBC"},
            {"label": "SC", "value": "SC"},
            {"label": "ST", "value": "ST"},
            {"label": "EWS", "value": "EWS"},
            {"label": "Prefer not to say", "value": "prefer_not_to_say"}
        ]
    },
    "bpl_card": {
        "field": "bpl_card",
        "category": "Social & Category",
        "question_text": "Do you hold a Below Poverty Line (BPL) Ration Card?",
        "input_type": "select",
        "options": [
            {"label": "Yes", "value": True},
            {"label": "No", "value": False}
        ]
    },
    "age": {
        "field": "age",
        "category": "Personal",
        "question_text": "What is your current age in years?",
        "input_type": "number",
        "placeholder": "e.g. 21",
        "options": None
    },
    "education_level": {
        "field": "education_level",
        "category": "Education",
        "question_text": "What is your highest education level achieved?",
        "input_type": "select",
        "options": [
            {"label": "10th Pass", "value": "10th Pass"},
            {"label": "12th Pass", "value": "12th Pass"},
            {"label": "Diploma", "value": "Diploma"},
            {"label": "Undergraduate", "value": "Undergraduate"},
            {"label": "Postgraduate", "value": "Postgraduate"},
            {"label": "Doctorate", "value": "Doctorate"}
        ]
    },
    "disability": {
        "field": "disability",
        "category": "Social & Category",
        "question_text": "Are you a person with benchmark disability (PwD)?",
        "input_type": "select",
        "options": [
            {"label": "Yes", "value": True},
            {"label": "No", "value": False}
        ]
    },
    "minority": {
        "field": "minority",
        "category": "Social & Category",
        "question_text": "Do you belong to a recognized minority community?",
        "input_type": "select",
        "options": [
            {"label": "Yes", "value": True},
            {"label": "No", "value": False}
        ]
    },
    "state": {
        "field": "state",
        "category": "Personal",
        "question_text": "Which state are you a resident of?",
        "input_type": "select",
        "options": [
            {"label": "Maharashtra", "value": "Maharashtra"},
            {"label": "Central Jurisdiction", "value": "Central"},
            {"label": "Other State", "value": "Other"}
        ]
    },
    "land_holding_acres": {
        "field": "land_holding_acres",
        "category": "Financial",
        "question_text": "What is your agricultural land holding in acres?",
        "input_type": "number",
        "placeholder": "e.g. 2.5",
        "options": None
    }
}

def get_missing_info_questions(missing_fields: List[str]) -> List[Dict[str, Any]]:
    questions = []
    for field in missing_fields:
        if field in QUESTION_TEMPLATES:
            questions.append(QUESTION_TEMPLATES[field])
        else:
            # Fallback generic question for unknown fields
            questions.append({
                "field": field,
                "category": "General",
                "question_text": f"Please provide your profile detail for '{field.replace('_', ' ').title()}':",
                "input_type": "text",
                "placeholder": "Enter value",
                "options": None
            })
    return questions
