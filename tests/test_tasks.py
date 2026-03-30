import pytest
from env.tasks import EasyTask, MediumTask, HardTask

@pytest.fixture
def mock_email():
    return {
        "metadata": {
            "expected_priority": "high",
            "expected_department": "support",
            "expected_final_action": "escalate"
        }
    }

def test_easy_task_perfect(mock_email):
    task = EasyTask()
    score, msg, advance = task.evaluate({"priority": "high"}, mock_email, None)
    assert score == 1.0
    assert advance is True

def test_easy_task_wrong(mock_email):
    task = EasyTask()
    score, msg, advance = task.evaluate({"priority": "low"}, mock_email, None)
    assert score == 0.0
    assert advance is True

def test_easy_task_invalid(mock_email):
    task = EasyTask()
    score, msg, advance = task.evaluate({"priority": "urgent"}, mock_email, None)
    assert score == -0.5
    assert advance is False

def test_easy_task_missing(mock_email):
    task = EasyTask()
    score, msg, advance = task.evaluate({}, mock_email, None)
    assert score == -0.5
    assert advance is False

def test_medium_task_perfect(mock_email):
    task = MediumTask()
    score, msg, advance = task.evaluate({"priority": "high", "department": "support"}, mock_email, None)
    assert score == 1.0
    assert advance is True

def test_medium_task_partial_priority(mock_email):
    task = MediumTask()
    # High -> Medium partial credit is 0.25 (as defined in MediumTask matrix)
    score, msg, advance = task.evaluate({"priority": "medium", "department": "support"}, mock_email, None)
    assert score == 0.75  # 0.5 for dept + 0.25 partial priority
    assert advance is True

def test_medium_task_wrong_priority_low(mock_email):
    task = MediumTask()
    # High -> Low is 0.0 partial credit
    score, msg, advance = task.evaluate({"priority": "low", "department": "support"}, mock_email, None)
    assert score == 0.5  # 0.5 for dept
    assert advance is True

def test_medium_task_wrong_all(mock_email):
    task = MediumTask()
    score, msg, advance = task.evaluate({"priority": "low", "department": "sales"}, mock_email, None)
    assert score == 0.0
    assert advance is True

def test_medium_task_invalid_format(mock_email):
    task = MediumTask()
    score, msg, advance = task.evaluate({"priority": "high", "department": "fake_dept"}, mock_email, None)
    assert score == -0.5
    assert advance is False

def test_hard_task_perfect(mock_email):
    task = HardTask()
    action = {
        "priority": "high",
        "department": "support",
        "final_action": "escalate",
        "reply_draft": "This is a very valid draft that passes the short length requirement."
    }
    score, msg, advance = task.evaluate(action, mock_email, None)
    assert score == 1.0
    assert advance is True

def test_hard_task_partial_priority(mock_email):
    task = HardTask()
    action = {
        "priority": "medium",  # Partial credit (0.15)
        "department": "support", # 0.3
        "final_action": "escalate", # 0.2
        "reply_draft": "This is a very valid draft that passes the short length requirement." # 0.2
    }
    score, msg, advance = task.evaluate(action, mock_email, None)
    expected_score = 0.15 + 0.3 + 0.2 + 0.2
    assert pytest.approx(score) == expected_score

def test_hard_task_wrong_all_except_draft(mock_email):
    task = HardTask()
    action = {
        "priority": "low",  # 0.0
        "department": "hr", # 0.0
        "final_action": "archive", # 0.0
        "reply_draft": "This is a very valid draft that passes the short length requirement." # 0.2
    }
    score, msg, advance = task.evaluate(action, mock_email, None)
    assert pytest.approx(score) == 0.2

def test_hard_task_short_draft_penalty(mock_email):
    task = HardTask()
    action = {
        "priority": "high",
        "department": "support",
        "final_action": "escalate",
        "reply_draft": "too short"
    }
    score, msg, advance = task.evaluate(action, mock_email, None)
    assert score == -0.5
    assert advance is False

def test_hard_task_invalid_action(mock_email):
    task = HardTask()
    action = {
        "priority": "high",
        "department": "support",
        "final_action": "delete", # Invalid logic action
        "reply_draft": "This is a very valid draft that passes the short length requirement."
    }
    score, msg, advance = task.evaluate(action, mock_email, None)
    assert score == -0.5
    assert advance is False

def test_matrix_medium_to_high(mock_email):
    mock_email["metadata"]["expected_priority"] = "medium"
    task = HardTask()
    action = {
        "priority": "high", # Should get 0.15 partial
        "department": "support", # 0.3 for support if expected was support. (wait mock is still support)
        "final_action": "escalate",
        "reply_draft": "This is a very valid draft that passes the short length requirement."
    }
    score, msg, advance = task.evaluate(action, mock_email, None)
    assert pytest.approx(score) == 0.15 + 0.3 + 0.2 + 0.2
