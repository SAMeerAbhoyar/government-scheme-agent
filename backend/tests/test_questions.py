from app.services.questions import get_missing_info_questions

def test_get_missing_info_questions_known_fields():
    missing = ["annual_income", "social_category"]
    questions = get_missing_info_questions(missing)
    assert len(questions) == 2
    assert questions[0]["field"] == "annual_income"
    assert questions[0]["input_type"] == "number"
    assert questions[1]["field"] == "social_category"
    assert questions[1]["input_type"] == "select"

def test_get_missing_info_questions_unknown_field_fallback():
    missing = ["custom_field_xyz"]
    questions = get_missing_info_questions(missing)
    assert len(questions) == 1
    assert questions[0]["field"] == "custom_field_xyz"
    assert questions[0]["input_type"] == "text"
