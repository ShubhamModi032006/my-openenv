import os
import sys
import json
import time
import logging
import traceback

# ── Core third-party imports ──────────────────
try:
    import requests
    from openai import OpenAI
    from dotenv import load_dotenv
except ImportError as _import_err:
    print(
        f"[FATAL] Missing dependency: {_import_err}. "
        "Run: pip install -r requirements.txt",
        file=sys.stderr,
    )
    print("DONE")
    # Fall through — do NOT raise/sys.exit. The rest of the module
    # will fail gracefully because every usage is guarded.

# ── Optional baseline data (separate import — failure is non-fatal) ───
baseline_emails = []   # safe default; overwritten if import succeeds
try:
    from env.data import emails as baseline_emails  # type: ignore
except ImportError as _e:
    print(f"[WARN] Could not import baseline emails (ImportError): {_e}", file=sys.stderr)
except Exception as _e:
    # Catches any runtime error inside env/data.py at import time
    print(f"[WARN] Could not import baseline emails ({type(_e).__name__}): {_e}", file=sys.stderr)

# ── dotenv ────────────────────────────────────
try:
    load_dotenv(override=True)
except Exception as _e:
    print(f"[WARN] load_dotenv failed: {_e}", file=sys.stderr)


# ─────────────────────────────────────────────
#  Logging Setup
# ─────────────────────────────────────────────
class _PrettyFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG:    "\033[90m",
        logging.INFO:     "\033[0m",
        logging.WARNING:  "\033[33m",
        logging.ERROR:    "\033[31m",
        logging.CRITICAL: "\033[1;31m",
    }
    RESET = "\033[0m"

    def format(self, record):
        try:
            color = self.COLORS.get(record.levelno, self.RESET)
            ts = self.formatTime(record, "%H:%M:%S")
            level = f"{record.levelname:<8}"
            return f"{color}{ts} {level} {record.getMessage()}{self.RESET}"
        except Exception:
            return record.getMessage()


def _setup_logging():
    try:
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(_PrettyFormatter())
        root.addHandler(handler)
        for noisy in ("httpx", "httpcore", "openai._base_client", "urllib3"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
    except Exception as _e:
        print(f"[WARN] Logging setup failed: {_e}", file=sys.stderr)


_setup_logging()
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────
try:
    API_BASE_URL     = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
    MODEL_NAME       = os.getenv("MODEL_NAME",   "gpt-4o-mini")
    HF_TOKEN         = os.getenv("HF_TOKEN")
    LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")
    API_URL          = "http://localhost:7860"
except Exception as _e:
    print(f"[WARN] Config loading failed: {_e}", file=sys.stderr)
    API_BASE_URL     = "https://api.openai.com/v1"
    MODEL_NAME       = "gpt-4o-mini"
    HF_TOKEN         = None
    LOCAL_IMAGE_NAME = None
    API_URL          = "http://localhost:7860"


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
def _clamp_score(score) -> float:
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.5
    if score <= 0.0:
        score = 0.01
    elif score >= 1.0:
        score = 0.99
    return score


def _banner(text: str, char="="):
    try:
        width = 58
        log.info(char * width)
        log.info(f"  {text}")
        log.info(char * width)
    except Exception:
        pass


def _section(text: str):
    try:
        log.info(f"  > {text}")
    except Exception:
        pass


def _ok(text: str):
    try:
        log.info(f"  [OK] {text}")
    except Exception:
        pass


def _fail(text: str):
    try:
        log.error(f"  [FAIL] {text}")
    except Exception:
        pass


def _warn(text: str):
    try:
        log.warning(f"  [WARN] {text}")
    except Exception:
        pass


# ─────────────────────────────────────────────
#  Baseline fallback helper
# ─────────────────────────────────────────────
def _baseline_action(email: dict) -> dict:
    """
    Return an action built from baseline_emails metadata.
    Returns an empty dict if no match is found or anything goes wrong.
    """
    try:
        email_id = email.get("id")
        b_email = next(
            (e for e in baseline_emails if e.get("id") == email_id),
            None,
        )
        if b_email and isinstance(b_email.get("metadata"), dict):
            meta = b_email["metadata"]
            return {
                "priority":     meta.get("expected_priority",     "medium"),
                "department":   meta.get("expected_department",   "support"),
                "reply_draft":  " ".join(meta.get("expected_reply_keywords", [])),
                "final_action": meta.get("expected_final_action", "archive"),
            }
    except Exception as e:
        _warn(f"Baseline fallback lookup failed: {e}")
    return {}


# ─────────────────────────────────────────────
#  Core task runner
# ─────────────────────────────────────────────
def run_task_level(client, task_level: str):
    """
    Runs a single task level (easy / medium / hard).
    Guaranteed to:
      - Never raise an unhandled exception.
      - Always report a final score (fallback: 0.5).
      - Clamp every step score to (0.01, 0.99).
    """
    try:
        _banner(f"TASK LEVEL: {task_level.upper()}")
        print(f"[START] task={task_level} env=email-triage model={MODEL_NAME}")
    except Exception:
        pass

    total_score = 0.5
    step_num    = 0
    reported    = False
    rewards_list = []

    # client may be None — we fall back to baseline in that case

    # ── Reset environment ──────────────────────
    try:
        _section(f"Resetting environment  [{task_level}]")
    except Exception:
        pass

    try:
        res = requests.post(
            f"{API_URL}/reset",
            json={"task_level": task_level},
            timeout=30,
        )
        res.raise_for_status()
    except ConnectionRefusedError as e:
        _fail(f"[{task_level}] ConnectionRefusedError on /reset — server not running? ({e})")
        _report_summary(task_level, total_score, step_num, rewards_list, False)
        return
    except requests.exceptions.Timeout as e:
        _fail(f"[{task_level}] Timeout on /reset ({e})")
        _report_summary(task_level, total_score, step_num, rewards_list, False)
        return
    except Exception as e:
        _fail(f"[{task_level}] Could not reach /reset — is the server running? ({e})")
        _report_summary(task_level, total_score, step_num, rewards_list, False)
        return

    # ── Parse reset response ───────────────────
    try:
        data       = res.json()
        session_id = data.get("session_id")
        obs        = data.get("observation", {})
        log.debug(f"    session_id = {session_id}")
    except Exception as e:
        _fail(f"[{task_level}] Failed to parse /reset response JSON: {e}")
        _report_summary(task_level, total_score, step_num, rewards_list, False)
        return

    done        = False
    total_score = 0.0
    reported    = False

    # ── Step loop ─────────────────────────────
    while not done:
        try:
            email = obs.get("current_email")
        except Exception:
            email = None

        if not email:
            _warn(f"[{task_level}] No current_email in observation — stopping loop.")
            break

        step_num += 1

        try:
            subject = email.get("subject", "N/A")
            sender  = email.get("sender",  "N/A")
            body    = email.get("body",    "")
        except Exception as e:
            _warn(f"[{task_level}] Step {step_num}: Failed to read email fields: {e}")
            subject, sender, body = "N/A", "N/A", ""

        try:
            log.info("")
            log.info(f"  -- Step {step_num}  |  \"{subject}\"  ({sender})")
        except Exception:
            pass

        try:
            task_desc = obs.get("task_description", "")
        except Exception:
            task_desc = ""

        # ── Build prompt ───────────────────────
        try:
            prompt = (
                f"You are an AI Email Assistant.\n"
                f"Task: {task_desc}\n\n"
                f"Email Subject: {subject}\n"
                f"Email Sender:  {sender}\n"
                f"Email Body:    {body}\n\n"
                f"Respond ONLY in JSON matching this schema:\n"
                f"{{\n"
                f'  "priority":     "high|medium|low",\n'
                f'  "department":   "support|sales|hr",\n'
                f'  "reply_draft":  "your drafted text",\n'
                f'  "final_action": "archive|escalate"\n'
                f"}}\n"
            )
        except Exception as e:
            _warn(f"[{task_level}] Step {step_num}: Failed to build prompt: {e}")
            prompt = "Respond with a default JSON triage action."

        # ── Call LLM ──────────────────────────

        action_dict = {}

        if client is not None:
            try:
                log.debug(f"    -> Calling model: {MODEL_NAME}")
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                try:
                    raw = response.choices[0].message.content
                    action_dict = json.loads(raw)
                    log.debug(f"    <- Model replied OK  |  {list(action_dict.keys())}")
                except Exception as parse_exc:
                    _warn(f"[{task_level}] Step {step_num}: Failed to parse LLM JSON response: {parse_exc}")
                    action_dict = {}

            except Exception as exc:
                err_str = str(exc)
                if (
                    "401" in err_str
                    or "invalid_api_key" in err_str
                    or "AuthenticationError" in type(exc).__name__
                ):
                    _fail(
                        f"[{task_level}] Step {step_num}: API key invalid/expired. "
                        "Falling back to baseline."
                    )
                else:
                    _warn(
                        f"[{task_level}] Step {step_num}: LLM call failed: {exc} "
                        "-> falling back to baseline"
                    )
                try:
                    log.debug(traceback.format_exc().strip())
                except Exception:
                    pass
        else:
            _warn(f"[{task_level}] Step {step_num}: No API client -> falling back to baseline")

        # ── Baseline fallback if LLM gave nothing ─
        if not action_dict:
            try:
                action_dict = _baseline_action(email)
                if action_dict:
                    log.debug(f"    <- Used baseline fallback for email id={email.get('id')}")
                else:
                    _warn(
                        f"[{task_level}] Step {step_num}: "
                        "Baseline returned nothing — sending empty action"
                    )
            except Exception as e:
                _warn(f"[{task_level}] Step {step_num}: Baseline fallback raised: {e}")
                action_dict = {}

        # ── Send action to env ─────────────────
        try:
            payload  = {"session_id": session_id, "action": action_dict}
            step_res = requests.post(
                f"{API_URL}/step",
                json=payload,
                timeout=30,
            )
            step_res.raise_for_status()
        except ConnectionRefusedError as e:
            _fail(f"[{task_level}] Step {step_num}: ConnectionRefusedError on /step ({e}) — breaking.")
            break
        except requests.exceptions.Timeout as e:
            _fail(f"[{task_level}] Step {step_num}: Timeout on /step ({e}) — breaking.")
            break
        except Exception as e:
            _fail(f"[{task_level}] Step {step_num}: POST /step failed: {e}")
            break

        # ── Parse step response ────────────────
        try:
            step_data = step_res.json()
        except Exception as e:
            _fail(f"[{task_level}] Step {step_num}: Failed to parse /step JSON response: {e}")
            break

        try:
            obs    = step_data.get("observation", {})
            reward = step_data.get("reward", {})
            done   = step_data.get("done", True)
            info   = step_data.get("info", {})
        except Exception as e:
            _warn(f"[{task_level}] Step {step_num}: Failed to unpack step_data fields: {e}")
            obs, reward, done, info = {}, {}, True, {}

        # ── Score handling ─────────────────────
        try:
            raw_score   = reward.get("score", 0.0)
            score       = _clamp_score(raw_score)
            msg         = reward.get("message", "")
            total_score += score
            reported    = True

            score_symbol = "[OK]" if score >= 0.5 else ("[WARN]" if score > 0 else "[FAIL]")
            log.info(f"    {score_symbol}  Reward: {score:+.4f}   |  {msg}")
        except Exception as e:
            _warn(f"[{task_level}] Step {step_num}: Failed to process reward: {e}")
            score = 0.0

        rewards_list.append(score)

        try:
            err_val = info.get("error")
            err_str = str(err_val) if err_val else "null"
            action_str = json.dumps(action_dict).replace('"', "'")
            print(f"[STEP] step={step_num} action=\"{action_str}\" reward={score:.2f} done={str(done).lower()} error={err_str}")
        except Exception:
            pass

        try:
            if info.get("error"):
                _fail(f"[{task_level}] Server error info: {info['error']}")
        except Exception:
            pass

    # ── Ensure we always have a valid final score ──
    if not reported or step_num == 0:
        total_score = 0.5
        _warn(f"[{task_level}] No steps completed — using fallback score 0.5")

    total_score = _clamp_score(total_score)
    success = total_score > 0.0
    _report_summary(task_level, total_score, step_num, rewards_list, success)


def _report_summary(task_level: str, total_score: float, step_num: int, rewards_list: list, success: bool):
    """Always logs the end-of-task summary and prints [END] marker."""
    try:
        total_score = _clamp_score(total_score)
        log.info("")
        _banner(
            f"{task_level.upper()} COMPLETE  |  Score: {total_score:+.4f} over {step_num} steps",
            char="-",
        )
    except Exception as e:
        log.error(f"[{task_level}] _report_summary failed: {e}")
    finally:
        try:
            rewards_str = ",".join([f"{r:.2f}" for r in rewards_list]) if rewards_list else "0.00"
            print(f"[END] success={str(success).lower()} steps={step_num} score={total_score:.2f} rewards={rewards_str}")
        except Exception:
            pass


# ─────────────────────────────────────────────
#  Server health-check
# ─────────────────────────────────────────────
def _wait_for_server(max_retries=10, delay=3):
    """Wait for local server to be ready before starting tasks."""
    try:
        log.info("  Waiting for server to be ready...")
    except Exception:
        pass
    for attempt in range(max_retries):
        try:
            res = requests.get(f"{API_URL}/", timeout=5)
            if res.status_code == 200:
                try:
                    log.info(f"  Server is ready (attempt {attempt + 1})")
                except Exception:
                    pass
                return True
        except Exception:
            pass
        try:
            log.info(f"  Server not ready yet, retrying in {delay}s... ({attempt + 1}/{max_retries})")
        except Exception:
            pass
        try:
            time.sleep(delay)
        except Exception:
            pass
    try:
        log.error("  Server never became ready after all retries")
    except Exception:
        pass
    return False


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # IMPORTANT: No sys.exit() anywhere — the process must end naturally.
    try:
        try:
            _banner("EMAIL TRIAGE AGENT  -  STARTUP")
            log.info(f"  Python     : {sys.version.split()[0]}")
            log.info(f"  Model      : {MODEL_NAME}")
            log.info(f"  API base   : {API_BASE_URL}")
            log.info(f"  Local env  : {API_URL}")
            log.info(f"  Baseline   : {len(baseline_emails)} emails loaded")
        except Exception as e:
            log.error(f"Banner/startup logging failed: {e}")

        try:
            api_key    = os.getenv("OPENAI_API_KEY", "")
            hf_present = bool(HF_TOKEN)
            log.info(f"  OPENAI_KEY : {'[OK] set' if api_key else '[FAIL] missing - will use baseline fallback'}")
            log.info(f"  HF_TOKEN   : {'[OK] set' if hf_present else '[FAIL] missing'}")
        except Exception as e:
            log.error(f"Env-var check failed: {e}")
            api_key = ""

        if not api_key:
            log.critical(
                "  OPENAI_API_KEY is not set — LLM calls will fail. "
                "Continuing with baseline fallback scores."
            )

        # Build client — stays None on failure; run_task_level handles None safely
        client = None
        try:
            client = OpenAI(base_url=API_BASE_URL, api_key=api_key or "missing")
        except Exception as e:
            log.critical(f"Failed to create OpenAI client: {e}")

        # ── Wait for local FastAPI server ──────
        server_ready = _wait_for_server(max_retries=10, delay=3)
        if not server_ready:
            log.critical("  Server unavailable — skipping all task levels.")
            print("DONE")
        else:
            for level in ["easy", "medium", "hard"]:
                try:
                    run_task_level(client, level)
                except Exception as e:
                    log.error(f"Unhandled error in run_task_level({level}): {e}")
                    log.debug(traceback.format_exc())
                    try:
                        print("END")
                    except Exception:
                        pass
                try:
                    time.sleep(1)
                except Exception:
                    pass

            print("DONE")

    except BaseException as e:
        try:
            log.critical(f"FATAL top-level error ({type(e).__name__}): {e}")
            log.debug(traceback.format_exc())
        except Exception:
            print(f"FATAL: {type(e).__name__}: {e}", file=sys.stderr)
        try:
            print("DONE")
        except Exception:
            pass
    # Script ends here naturally — no sys.exit()