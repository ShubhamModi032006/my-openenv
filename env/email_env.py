import copy
import random
from typing import Tuple, Dict, Any, Optional

from .models import Observation, Action, Reward, Email
from .data import emails
from .tasks import EasyTask, MediumTask, HardTask

class EmailTriageEnv:
    def __init__(self, task_level: str = "easy"):
        self.task_level = task_level.lower()
        self.all_emails = random.sample(emails, min(10, len(emails)))
        self.current_index = 0
        self.history = []
        self.steps_taken = 0
        
        if self.task_level == "easy":
            self.task = EasyTask()
        elif self.task_level == "medium":
            self.task = MediumTask()
        elif self.task_level == "hard":
            self.task = HardTask()
        else:
            raise ValueError(f"Unknown task level: {task_level}")
            
    def _get_observation(self) -> Observation:
        if self.current_index < len(self.all_emails):
            raw_email = self.all_emails[self.current_index]
            email_obj = Email(
                id=raw_email["id"],
                sender=raw_email["sender"],
                subject=raw_email["subject"],
                body=raw_email["body"],
                timestamp=raw_email["timestamp"]
            )
        else:
            email_obj = None
            
        return Observation(
            current_email=email_obj,
            history=self.history,
            steps_taken=self.steps_taken,
            remaining_emails=len(self.all_emails) - self.current_index,
            emails_processed=self.current_index,
            task_description=self.task.description
        )
        
    def reset(self, task_level: Optional[str] = None) -> Observation:
        if task_level:
            self.task_level = task_level.lower()
            if self.task_level == "easy":
                self.task = EasyTask()
            elif self.task_level == "medium":
                self.task = MediumTask()
            elif self.task_level == "hard":
                self.task = HardTask()
            else:
                raise ValueError(f"Unknown task level: {task_level}")
        
        self.all_emails = random.sample(emails, min(10, len(emails)))
        self.current_index = 0
        self.history = []
        self.steps_taken = 0
        return self._get_observation()
        
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
        # If already done
        if self.current_index >= len(self.all_emails):
            return (
                self._get_observation(),
                Reward(score=0.0, message="No emails left to triage"),
                True,
                {"error": "Environment already done"}
            )
        self.steps_taken += 1
        
        if self.steps_taken > 10:
            return (
                self._get_observation(),
                Reward(score=-1.0, message="Infinite loop detected"),
                True,
                {"error": "Too many steps"}
            )
            
        current_email = self.all_emails[self.current_index]
        action_dict = action.model_dump(exclude_none=True)
        
        repeated = False
        for past in self.history:
            if past.get("email_id") == current_email["id"] and past.get("action") == action_dict:
                repeated = True
                
        if repeated:
            score = -0.2
            message = "Repeated action penalized"
            advance = False
        else:
            score, message, advance = self.task.evaluate(action_dict, current_email, self)
        
        self.history.append({
            "email_id": current_email["id"],
            "action": action_dict,
            "score": score
        })
        
        if advance:
            self.current_index += 1
            
        done = (self.current_index >= len(self.all_emails)) or (self.steps_taken > 10)
        
        reward = Reward(score=score, message=message)
        obs = self._get_observation()
        
        return obs, reward, done, {"task_level": self.task_level, "email_id": current_email["id"]}
        
    def state(self) -> Dict[str, Any]:
        return {
            "current_index": self.current_index,
            "total_emails": len(self.all_emails),
            "task_level": self.task_level,
            "done": self.current_index >= len(self.all_emails)
        }
