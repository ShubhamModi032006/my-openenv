import os
import sys
import json
import time
import logging
import traceback
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Configure comprehensive logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Required variables per OpenEnv template
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

API_URL = "http://localhost:7860"

def run_task_level(client, task_level):
    try:
        logging.info(f"========== STARTING TASK LEVEL: {task_level.upper()} ==========")
        # Mandated exact stdout logs from OpenEnv validator requirements
        print("START")

        logging.debug(f"[HTTP REQ] POST {API_URL}/reset | Payload: {{'task_level': '{task_level}'}}")
        # Reset env
        res = requests.post(f"{API_URL}/reset", json={"task_level": task_level})
        
        logging.debug(f"[HTTP RES] POST {API_URL}/reset | Status: {res.status_code}")
        logging.debug(f"[HTTP RES BODY] raw text: {res.text}")

        if res.status_code != 200:
            logging.error(f"Failed to reset environment. HTTP {res.status_code}: {res.text}")
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
                logging.debug("No 'current_email' in observation. Breaking loop.")
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
            # Mandated exact stdout logs from OpenEnv validator requirements
            print("STEP")
            
            logging.debug(f"[OpenAI REQ] Sending chat completion to model: {MODEL_NAME}")
            logging.debug(f"[OpenAI PROMPT]\n{prompt}")

            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )

                raw_response = response.choices[0].message.content
                logging.debug(f"[OpenAI RES SUCCESS] Received response.")
                logging.debug(f"[OpenAI RAW RESPONSE]\n{raw_response}")

                action_json = raw_response
                action_dict = json.loads(action_json)
            except Exception as e:
                logging.error(f"[OpenAI ERR] Exception during OpenAI API call: {e}")
                logging.error(f"Traceback:\n{traceback.format_exc()}")
                action_dict = {}

            logging.info(f"Action parsed for email '{email.get('subject', 'N/A')}': {action_dict}")

            payload = {
                "session_id": session_id,
                "action": action_dict
            }
            
            logging.debug(f"[HTTP REQ] POST {API_URL}/step | Payload: {payload}")
            try:
                step_res = requests.post(f"{API_URL}/step", json=payload)
                logging.debug(f"[HTTP RES] POST {API_URL}/step | Status: {step_res.status_code}")
                logging.debug(f"[HTTP RES BODY] raw text: {step_res.text}")
                
                step_res.raise_for_status()
                step_data = step_res.json()
            except Exception as e:
                logging.error(f"[HTTP ERR] local API /step request failed: {e}")
                logging.error(f"Traceback:\n{traceback.format_exc()}")
                break

            obs = step_data.get("observation", {})
            reward = step_data.get("reward", {})
            done = step_data.get("done", True)

            score = reward.get("score", 0.0)
            msg = reward.get("message", "")
            
            logging.debug(f"[STEP COMPLETION] Reward={score}/1.0 | done={done} | message: {msg}")
            
            total_score += score
            steps += 1

        logging.info(f"✅ [{task_level.upper()} COMPLETE] Total Score: {total_score} out of {steps} possible")
        # Mandated exact stdout logs from OpenEnv validator requirements
        print("END")
        
    except Exception as e:
        logging.error(f"run_task_level({task_level!r}) failed with unhandled exception: {e}")
        logging.error(f"Traceback:\n{traceback.format_exc()}")

if __name__ == "__main__":
    try:
        logging.info(f"--- Script Startup ---")
        logging.info(f"Python Version: {sys.version.split()[0]}")
        
        api_key_present = "OPENAI_API_KEY" in os.environ
        hf_token_present = "HF_TOKEN" in os.environ
        
        logging.info("Checking Environment Variables:")
        logging.info(f"  - OPENAI_API_KEY present: {api_key_present}")
        logging.info(f"  - HF_TOKEN present:       {hf_token_present}")
        logging.info(f"  - API_BASE_URL:           {API_BASE_URL}")
        logging.info(f"  - MODEL_NAME:             {MODEL_NAME}")
        logging.info(f"  - LOCAL API SERVER:       {API_URL}")
        
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

    except Exception as e:
        logging.critical(f"FATAL ERROR in __main__ block: {e}")
        logging.critical(f"Traceback:\n{traceback.format_exc()}")
        raise
    finally:
        print("DONE")
