from typing import Dict, Any, Tuple

class Task:
    def evaluate(self, action: Dict[str, Any], email: Dict[str, Any], env: Any) -> Tuple[float, str, bool]:
        raise NotImplementedError

class EasyTask(Task):
    description = "Classify the priority of the email ('high', 'medium', 'low')."
    
    def evaluate(self, action: Dict[str, Any], email: Dict[str, Any], env: Any) -> Tuple[float, str, bool]:
        expected = email["metadata"]["expected_priority"]
        predicted = action.get("priority", "")
        if predicted is None:
            predicted = ""
        predicted = predicted.lower()
        if not predicted or predicted not in ['high', 'medium', 'low']:
            return -0.5, "Invalid action format", False
        if predicted == expected:
            return 1.0, "Correct priority classification", True
        return 0.0, f"Incorrect priority. Expected {expected}, got {predicted}", True

class MediumTask(Task):
    description = "Classify priority ('high', 'medium', 'low') and assign department ('support', 'sales', 'hr')."
    
    def evaluate(self, action: Dict[str, Any], email: Dict[str, Any], env: Any) -> Tuple[float, str, bool]:
        exp_priority = email["metadata"]["expected_priority"]
        exp_dept = email["metadata"]["expected_department"]
        
        pred_priority = (action.get("priority") or "").lower()
        pred_dept = (action.get("department") or "").lower()
        
        if pred_priority not in ['high', 'medium', 'low'] or pred_dept not in ['support', 'sales', 'hr']:
            return -0.5, "Invalid action format", False
            
        score = 0.0
        msgs = []
        
        if pred_priority == exp_priority:
            score += 0.5
            msgs.append("Correct priority")
        else:
            matrix = {"high": {"medium": 0.25, "low": 0.0}, "medium": {"high": 0.25, "low": 0.25}, "low": {"medium": 0.25, "high": 0.0}}
            if exp_priority in matrix and pred_priority in matrix[exp_priority]:
                score += matrix[exp_priority][pred_priority]
                msgs.append(f"Partial priority credit ({matrix[exp_priority][pred_priority]})")
            else:
                msgs.append(f"Incorrect priority (got {pred_priority})")
            
        if pred_dept == exp_dept:
            score += 0.5
            msgs.append("Correct department")
        else:
            msgs.append(f"Incorrect department (got {pred_dept})")
            
        return score, "; ".join(msgs), True

class HardTask(Task):
    description = "Classify priority, assign department, write a reply_draft, and decide final_action ('archive' or 'escalate')."
    
    def evaluate(self, action: Dict[str, Any], email: Dict[str, Any], env: Any) -> Tuple[float, str, bool]:
        exp_priority = email["metadata"]["expected_priority"]
        exp_dept = email["metadata"]["expected_department"]
        exp_action = email["metadata"]["expected_final_action"]
        
        pred_priority = (action.get("priority") or "").lower()
        pred_dept = (action.get("department") or "").lower()
        pred_draft = action.get("reply_draft") or ""
        pred_action = (action.get("final_action") or "").lower()
        
        valid_priorities = ['high', 'medium', 'low']
        valid_depts = ['support', 'sales', 'hr']
        valid_actions = ['archive', 'escalate']
        
        if pred_priority not in valid_priorities or pred_dept not in valid_depts or pred_action not in valid_actions:
            return -0.5, "Invalid action format", False
        
        # New Strict Draft Penalty constraint    
        if not pred_draft or len(pred_draft.strip()) <= 10:
            return -0.5, "Draft too short or invalid", False
            
        score = 0.0
        msgs = []
        
        if pred_priority == exp_priority:
            score += 0.3
            msgs.append("Correct priority")
        else:
            matrix = {"high": {"medium": 0.15, "low": 0.0}, "medium": {"high": 0.15, "low": 0.15}, "low": {"medium": 0.15, "high": 0.0}}
            if exp_priority in matrix and pred_priority in matrix[exp_priority]:
                score += matrix[exp_priority][pred_priority]
                msgs.append(f"Partial priority credit ({matrix[exp_priority][pred_priority]})")
            else:
                msgs.append("Incorrect priority")
            
        if pred_dept == exp_dept:
            score += 0.3
            msgs.append("Correct department")
        else:
            msgs.append("Incorrect department")
            
        if pred_action == exp_action:
            score += 0.2
            msgs.append("Correct final action")
        else:
            msgs.append("Incorrect action")
            
        expected_keywords = email["metadata"].get("expected_reply_keywords", [])
        
        if expected_keywords:
            matched_words = [kw for kw in expected_keywords if kw.lower() in pred_draft.lower()]
            keyword_score = len(matched_words) / len(expected_keywords)
            score += round(keyword_score * 0.2, 2)
            msgs.append(f"Reply quality: {len(matched_words)}/{len(expected_keywords)} keywords")
        else:
            score += 0.2
            msgs.append("Adequate reply length")
        
        score = round(score, 2)
        if score == 1.0:
            return 1.0, "Perfect full workflow evaluation", True
        return score, "Partial success: " + ", ".join(msgs), True
