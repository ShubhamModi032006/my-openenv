---
title: Email Triage OpenEnv
emoji: 📧
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# Email Triage OpenEnv

## Overview
Email Triage OpenEnv is a realistic simulation environment designed for AI agents to process and triage incoming emails. It fully complies with the OpenEnv specification and provides multiple levels of difficulty.

## Problem Motivation
Customer support and administrative teams receive thousands of emails daily that must be classified by priority, routed to the correct department, and properly handled (archived or escalated). Automating this workflow requires an AI agent capable of multi-step reasoning. This environment evaluates such agents.

## Architecture
The project follows standard OpenEnv principles, offering deterministic state mutations through a FastAPI frontend.
- `env/`: Contains the core environment logic (models, tasks, state management).
- `api/`: Exposes the OpenEnv-compatible HTTP layer.
- `baseline/`: Contains a reference agent using the OpenAI API.

## Action Space
The agent can perform the following actions, determined by the `Action` schema:
```json
{
  "priority": "high|medium|low",
  "department": "support|sales|hr",
  "reply_draft": "string",
  "final_action": "archive|escalate"
}
```

## Observation Space
The environment returns an `Observation` at each step:
```json
{
  "current_email": {
    "id": "...",
    "sender": "...",
    "subject": "...",
    "body": "...",
    "timestamp": "..."
  },
  "history": [{"email_id": "...", "action": {}, "score": 1.0}],
  "steps_taken": 2,
  "remaining_emails": 1,
  "emails_processed": 1,
  "task_description": "..."
}
```

## Tasks
* **Easy**: Classify priority.
* **Medium**: Classify priority and assign to a department.
* **Hard**: Full workflow - priority, department, draft a reply, decide to archive or escalate.

## Setup Instructions
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

## Run Instructions
```bash
python main.py
# Server runs on http://localhost:7860
```

## Docker Instructions
```bash
docker build -t openenv .
docker run -p 7860:7860 openenv
```
Compatible with Hugging Face Spaces!

## Baseline Results
Set your OpenAI key and run the baseline:
```bash
export OPENAI_API_KEY="sk-..."
python baseline/run_baseline.py
```

### Groq `llama-3.3-70b-versatile` Performance (`temperature=0.0`)
- **EASY Task:** 1.0 / 3.0
- **MEDIUM Task:** 2.5 / 3.0
- **HARD Task:** 2.75 / 3.0

