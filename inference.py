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

# ─────────────────────────────────────────────
#  Logging Setup — clean, minimal, human-friendly
# ─────────────────────────────────────────────
class _PrettyFormatter(logging.Formatter):
    """Color-coded, compact log formatter."""
    COLORS = {
        logging.DEBUG:    "\033[90m",   # grey
        logging.INFO:     "\033[0m",    # default
        logging.WARNING:  "\033[33m",   # yellow
        logging.ERROR:    "\033[31m",   # red
        logging.CRITICAL: "\033[1;31m", # bold red
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        ts = self.formatTime(record, "%H:%M:%S")
        level = f"{record.levelname:<8}"
        return f"{color}{ts} {level} {record.getMessage()}{self.RESET}"


def _setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(_PrettyFormatter())
    root.addHandler(handler)

    # Silence noisy libraries — we only care about our own logs
    for noisy in ("httpx", "httpcore", "openai._base_client", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


_setup_logging()
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────
API_BASE_URL     = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME       = os.getenv("MODEL_NAME",   "gpt-4o-mini")
HF_TOKEN         = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
API_URL          = "http://localhost:7860"


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
def _banner(text: str, char="═"):
    width = 58
    log.info(char * width)
    log.info(f"  {text}")
    log.info(char * width)


def _section(text: str):
    log.info(f"  ▶ {text}")


def _ok(text: str):
    log.info(f"  ✅ {text}")


def _fail(text: str):
    log.error(f"  ❌ {text}")


def _warn(text: str):
    log.warning(f"  ⚠️  {text}")


# ─────────────────────────────────────────────
#  Core task runner
# ─────────────────────────────────────────────
def run_task_level(client, task_level: str):
    _banner(f"TASK LEVEL: {task_level.upper()}")
    print("START")

    # ── Reset environment ──────────────────────
    _section(f"Resetting environment  [{task_level}]")
    try:
        res = requests.post(f"{API_URL}/reset", json={"task_level": task_level})
        res.raise_for_status()
    except Exception as e:
        _fail(f"Could not reach local server at {API_URL}/reset — is it running?  ({e})")
        return

    data       = res.json()
    session_id = data.get("session_id")
    obs        = data.get("observation", {})
    log.debug(f"    session_id = {session_id}")

    done        = False
    total_score = 0.0
    step_num    = 0

    # ── Step loop ─────────────────────────────
    while not done:
        email = obs.get("current_email")
        if not email:
            _warn("No current_email in observation — stopping loop.")
            break

        step_num += 1
        subject = email.get("subject", "N/A")
        sender  = email.get("sender",  "N/A")

        log.info("")
        log.info(f"  ── Step {step_num}  │  \"{subject}\"  ({sender})")

        task_desc = obs.get("task_description", "")

        prompt = (
            f"You are an AI Email Assistant.\n"
            f"Task: {task_desc}\n\n"
            f"Email Subject: {subject}\n"
            f"Email Sender:  {sender}\n"
            f"Email Body:    {email['body']}\n\n"
            f"Respond ONLY in JSON matching this schema:\n"
            f"{{\n"
            f'  "priority":     "high|medium|low",\n'
            f'  "department":   "support|sales|hr",\n'
            f'  "reply_draft":  "your drafted text",\n'
            f'  "final_action": "archive|escalate"\n'
            f"}}\n"
        )

        # ── Call LLM ──────────────────────────
        print("STEP")
        log.debug(f"    → Calling model: {MODEL_NAME}")

        action_dict = {}
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            raw = response.choices[0].message.content
            action_dict = json.loads(raw)
            log.debug(f"    ← Model replied OK  │  {list(action_dict.keys())}")

        except Exception as exc:
            err_str = str(exc)

            # ── Auth error — fail fast, don't loop ──
            if "401" in err_str or "invalid_api_key" in err_str or "AuthenticationError" in type(exc).__name__:
                _fail(
                    "Groq/OpenAI returned 401 Unauthorized — your API key is invalid or expired.\n"
                    "      Fix: update GROQ_API_KEY in your .env file and restart."
                )
                # Stop the whole run — there's no point continuing
                return

            _warn(f"LLM call failed: {exc}  →  sending empty action")
            log.debug(f"    {traceback.format_exc().strip()}")

        # ── Send action to env ─────────────────
        payload = {"session_id": session_id, "action": action_dict}
        try:
            step_res = requests.post(f"{API_URL}/step", json=payload)
            step_res.raise_for_status()
            step_data = step_res.json()
        except Exception as e:
            _fail(f"POST /step failed: {e}")
            break

        obs    = step_data.get("observation", {})
        reward = step_data.get("reward", {})
        done   = step_data.get("done", True)
        info   = step_data.get("info",   {})

        score = reward.get("score",   0.0)
        msg   = reward.get("message", "")
        total_score += score

        # Colour-code the score
        score_symbol = "✅" if score >= 0.5 else ("⚠️ " if score >= 0 else "❌")
        log.info(f"    {score_symbol}  Reward: {score:+.1f}   │  {msg}")

        if info.get("error"):
            _fail(f"Server error info: {info['error']}")

    # ── Summary ───────────────────────────────
    log.info("")
    _banner(f"{task_level.upper()} COMPLETE  │  Score: {total_score:+.2f} over {step_num} steps", char="─")
    print("END")


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    try:
        _banner("EMAIL TRIAGE AGENT  —  STARTUP")
        log.info(f"  Python     : {sys.version.split()[0]}")
        log.info(f"  Model      : {MODEL_NAME}")
        log.info(f"  API base   : {API_BASE_URL}")
        log.info(f"  Local env  : {API_URL}")

        api_key   = os.getenv("OPENAI_API_KEY", "")
        hf_present = bool(HF_TOKEN)
        log.info(f"  OPENAI_KEY : {'✅ set' if api_key else '❌ missing — LLM calls will fail'}")
        log.info(f"  HF_TOKEN   : {'✅ set' if hf_present else '❌ missing'}")

        if not api_key:
            log.critical("  OPENAI_API_KEY is not set — cannot make LLM calls. Exiting.")
            raise SystemExit(1)

        # NOTE: Use OPENAI_API_KEY for LLM (Groq) calls.
        # HF_TOKEN is for Hugging Face authentication only — do NOT use it as the LLM key.
        client = OpenAI(base_url=API_BASE_URL, api_key=api_key)

        for level in ["easy", "medium", "hard"]:
            run_task_level(client, level)
            time.sleep(1)

    except Exception as e:
        log.critical(f"FATAL: {e}")
        log.debug(traceback.format_exc())
        raise
    finally:
        print("DONE")
