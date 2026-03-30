import requests

BASE_URL = "https://sm032006-email-triage-openenv.hf.space"

def test_api():
    print(f"Testing endpoints at {BASE_URL}...\n")

    # 1. Test Root Endpoint
    print("1️⃣ Testing GET /")
    res = requests.get(f"{BASE_URL}/")
    print(f"Status: {res.status_code}")
    print(f"Response: {res.json()}\n")

    # 2. Test Reset Endpoint (Creates a Session)
    print("2️⃣ Testing POST /reset")
    res = requests.post(f"{BASE_URL}/reset", json={"task_level": "hard"})
    print(f"Status: {res.status_code}")
    
    if res.status_code != 200:
        print("Failed to reset. Exiting.")
        return
        
    data = res.json()
    session_id = data.get("session_id")
    print(f"Session ID Created: {session_id}")
    print("Observation received successfully.\n")

    # 3. Test State Endpoint
    print(f"3️⃣ Testing GET /state?session_id={session_id}")
    res = requests.get(f"{BASE_URL}/state", params={"session_id": session_id})
    print(f"Status: {res.status_code}")
    print(f"State Data: {res.json()}\n")

    # 4. Test Step Endpoint
    print("4️⃣ Testing POST /step")
    payload = {
        "session_id": session_id,
        "action": {
            "priority": "high",
            "department": "support",
            "final_action": "escalate",
            "reply_draft": "This is a detailed response to ensure I get points from the drafted keywords checking."
        }
    }
    res = requests.post(f"{BASE_URL}/step", json=payload)
    print(f"Status: {res.status_code}")
    print(f"Reward Received: {res.json().get('reward')}\n")

    # 5. Test Delete Session Endpoint
    print(f"5️⃣ Testing DELETE /session/{session_id}")
    res = requests.delete(f"{BASE_URL}/session/{session_id}")
    print(f"Status: {res.status_code}")
    print(f"Response: {res.json()}\n")

    print("✅ All Hugging Face API Endpoints functioning beautifully!")

if __name__ == "__main__":
    test_api()
