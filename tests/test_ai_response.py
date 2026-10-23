from ai_response import extract_ai_insight


def test_extracts_response_from_dict():
    assert extract_ai_insight({"response": "Check the hydraulic seal."}) == "Check the hydraulic seal."


def test_extracts_response_from_json_string():
    assert extract_ai_insight('{"response":"Inspect the pump."}') == "Inspect the pump."


def test_accepts_plain_text_response():
    assert extract_ai_insight("Possible seal failure.") == "Possible seal failure."


def test_trims_whitespace():
    assert extract_ai_insight({"response": "  Inspect the valve.  "}) == "Inspect the valve."


def test_empty_response_is_not_treated_as_a_prediction():
    assert extract_ai_insight({"response": "  "}) is None
    assert extract_ai_insight('{"response":""}') is None


def test_missing_or_null_response_is_unavailable():
    assert extract_ai_insight(None) is None
    assert extract_ai_insight({"response": None}) is None
    assert extract_ai_insight('{"done":true}') is None
    assert extract_ai_insight("null") is None
    assert extract_ai_insight("") is None


def test_non_string_response_is_normalized():
    assert extract_ai_insight({"response": 123}) == "123"
