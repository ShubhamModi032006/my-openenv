import pytest
from env.email_env import EmailTriageEnv
from env.models import Action

def test_env_initialization():
    env = EmailTriageEnv("easy")
    assert env.task_level == "easy"
    assert env.steps_taken == 0
    
def test_env_observation_schema():
    env = EmailTriageEnv()
    obs = env.reset()
    assert obs.history == []
    assert obs.steps_taken == 0
    assert obs.emails_processed == 0

def test_repeated_action_penalty():
    env = EmailTriageEnv("easy")
    env.reset()
    action = Action(priority="high")
    
    # First step
    obs, reward, done, info = env.step(action)
    assert reward.score >= 0.0
    
    # Force repeat on the same email (since it didn't advance if we used an invalid schema, but let's test the penalty)
    # Actually wait, if the first step advanced, we are on a new email. If it advanced, repeating the *same* action JSON doesn't trigger penalty unless it's on the *same* email_id.
    # To test same email, we send an invalid action so it doesn't advance, then repeat.
    invalid_action = Action(priority="nonexistent")
    obs2, reward2, done2, info2 = env.step(invalid_action)
    assert reward2.score == -0.5  # Invalid penalty
    
    # Repeat the invalid action
    obs3, reward3, done3, info3 = env.step(invalid_action)
    assert reward3.score == -0.2  # Repeated penalty
    assert "Repeated" in reward3.message

def test_infinite_loop_protection():
    env = EmailTriageEnv()
    env.reset()
    
    action = Action(priority="high")
    for _ in range(10):
        obs, reward, done, info = env.step(action)
        
    # The 11th step should trigger the massive -1.0 infinite loop penalty and terminate
    obs, reward, done, info = env.step(action)
    assert reward.score == -1.0
    assert done == True
    assert "Too many steps" in info["error"]
