import os
import json
import time
from openai import OpenAI
import requests

# Required variables per OpenEnv template
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

API_URL = "http://localhost:7860"

def run_task_level(client, task_level):
    try:
        print(f"\n{'='*50}")
        print(f" 🚀 STARTING TASK LEVEL: {task_level.upper()}")
        print(f"{'='*50}")

        # Reset env
        res = requests.post(f"{API_URL}/reset", json={"task_level": task_level})
        if res.status_code != 200:
            print("Failed to reset environment:", res.text)
            return

        data = res.json()
        session_id = data.get("session_id")
        obs = data.get("observation")
        done = False
        total_score = 0.0
        steps = 0

        while not done:
            email = obs.get("current_email")
            if not email:
                break

            task_desc = obs.get("task_description")

            prompt = f"""You are an AI Email Assistant.
Task: {task_desc}

Email Subject: {email['subject']}
Email Sender: {email['sender']}
Email Body: {email['body']}

Respond ONLY in JSON matching this schema, providing the required fields for the task:
{{
  "priority": "high|medium|low",
  "department": "support|sales|hr",
  "reply_draft": "your drafted text",
  "final_action": "archive|escalate"
}}
"""

            print("STEP")
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )

                action_json = response.choices[0].message.content
                action_dict = json.loads(action_json)
            except Exception as e:
                print(f"  [X] Error calling OpenAI API: {e}")
                action_dict = {}

            print(f"  [Email]: {email['subject']}")
            print(f"  [Action Taken]:")
            if "priority" in action_dict: print(f"    - Priority: {action_dict['priority']}")
            if "department" in action_dict: print(f"    - Dept:     {action_dict['department']}")
            if "final_action" in action_dict: print(f"    - Decision: {action_dict['final_action']}")
            if "reply_draft" in action_dict:
                draft_sample = action_dict['reply_draft']
                if len(draft_sample) > 50:
                    draft_sample = draft_sample[:47] + "..."
                print(f"    - Draft:    \"{draft_sample}\"")

            try:
                payload = {
                    "session_id": session_id,
                    "action": action_dict
                }
                step_res = requests.post(f"{API_URL}/step", json=payload)
                step_data = step_res.json()
            except requests.exceptions.RequestException as e:
                print(f"  [X] Error calling local API: {e}")
                break

            obs = step_data.get("observation")
            reward = step_data.get("reward", {})
            done = step_data.get("done", True)

            score = reward.get("score", 0.0)
            msg = reward.get("message", "")
            print(f"  [Result]: Reward = {score} / 1.0")
            print(f"  [Feedback]: {msg}\n")

            total_score += score
            steps += 1

        print(f"✅ [{task_level.upper()} COMPLETE] Total Score: {total_score} out of {steps} possible\n")
        print("END")
        
    except Exception as e:
        print(f"  [X] run_task_level({task_level!r}) failed with unhandled error: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    # The validator requires that the client is instantiated via these exact variables.
    # If the environment passed HF_TOKEN, use it, otherwise fall back to OPENAI_API_KEY
    api_key = HF_TOKEN or os.getenv("OPENAI_API_KEY", "dummy-key")

    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=api_key
    )

    for level in ["easy", "medium", "hard"]:
        run_task_level(client, level)
        time.sleep(1)
