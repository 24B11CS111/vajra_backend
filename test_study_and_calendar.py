import sys
import uuid
import requests
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_study_and_calendar():
    print("=== 1. TEST SIGNUP & AUTHENTICATION ===")
    test_email = f"prod_student_{uuid.uuid4().hex[:6]}@vajra.ai"
    signup_res = requests.post(f"{BASE_URL}/auth/signup", json={
        "email": test_email,
        "password": "Password123!",
        "full_name": "Product Student"
    })
    assert signup_res.status_code == 201, f"Signup failed: {signup_res.text}"
    token = signup_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"User signed up: {test_email}, token acquired.")

    print("\n=== 2. TEST SUBJECTS CRUD ===")
    # Create Subject
    subj_res = requests.post(f"{BASE_URL}/study/subjects", headers=headers, json={
        "name": "Astrophysics",
        "description": "Stellar dynamics and cosmic radiation",
        "color": "#8B5CF6",
        "priority": "high",
        "exam_date": (datetime.utcnow() + timedelta(days=14)).isoformat()
    })
    assert subj_res.status_code == 201, f"Subject create failed: {subj_res.text}"
    subj = subj_res.json()
    subj_id = subj["id"]
    print(f"Created Subject: {subj['name']} (ID: {subj_id})")

    # List Subjects
    list_subj = requests.get(f"{BASE_URL}/study/subjects", headers=headers).json()
    assert len(list_subj) >= 1, "Subjects list empty"
    print(f"Listed {len(list_subj)} subjects.")

    print("\n=== 3. TEST ASSIGNMENTS CRUD ===")
    # Create Assignment
    assign_res = requests.post(f"{BASE_URL}/study/assignments", headers=headers, json={
        "subject_id": subj_id,
        "subject_name": "Astrophysics",
        "title": "Dark Matter Problem Set 3",
        "description": "Calculate gravitational lensing angle",
        "due_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
        "priority": "high",
        "status": "IN_PROGRESS"
    })
    assert assign_res.status_code == 201, f"Assignment create failed: {assign_res.text}"
    assign = assign_res.json()
    assign_id = assign["id"]
    print(f"Created Assignment: {assign['title']} - Status: {assign['status']}")

    # Toggle status
    toggle_res = requests.post(f"{BASE_URL}/study/assignments/{assign_id}/toggle", headers=headers)
    assert toggle_res.status_code == 200, f"Toggle failed: {toggle_res.text}"
    toggled = toggle_res.json()
    print(f"Toggled Assignment Status: {toggled['status']}")

    print("\n=== 4. TEST CALENDAR EVENTS CRUD ===")
    event_res = requests.post(f"{BASE_URL}/calendar/events", headers=headers, json={
        "title": "Astrophysics Lab Session",
        "description": "Telescope data collection",
        "event_type": "study_session",
        "start_time": (datetime.utcnow() + timedelta(days=1, hours=4)).isoformat(),
        "end_time": (datetime.utcnow() + timedelta(days=1, hours=6)).isoformat(),
        "color": "#8B5CF6"
    })
    assert event_res.status_code == 201, f"Event create failed: {event_res.text}"
    event = event_res.json()
    event_id = event["id"]
    print(f"Created Calendar Event: {event['title']} (ID: {event_id})")

    list_events = requests.get(f"{BASE_URL}/calendar/events", headers=headers).json()
    assert len(list_events) >= 1, "Calendar events list empty"
    print(f"Listed {len(list_events)} calendar events.")

    print("\n=== 5. TEST AI STUDY & CALENDAR ACTIONS ===")
    # Create conversation
    conv_res = requests.post(f"{BASE_URL}/chat/conversations", headers=headers, json={"title": "AI Action Test"})
    conv_id = conv_res.json()["id"]

    # Ask AI to create an assignment
    print("Testing AI Action: 'Create a physics assignment for Friday'")
    msg1_res = requests.post(
        f"{BASE_URL}/chat/conversations/{conv_id}/messages/stream",
        headers=headers,
        json={"role": "user", "content": "Create a physics assignment for Friday."}
    )
    assert msg1_res.status_code == 200, f"AI stream failed: {msg1_res.text}"
    print("AI response stream received.")

    # Verify assignment was created in database!
    updated_assignments = requests.get(f"{BASE_URL}/study/assignments", headers=headers).json()
    created_phys = [a for a in updated_assignments if "Physics" in a["title"] or "Physics" in a["subject_name"]]
    assert len(created_phys) > 0, "AI tool failed to persist physics assignment in database!"
    print(f"VERIFIED: AI created real DB assignment: '{created_phys[0]['title']}' due {created_phys[0]['due_date']}")

    # Ask AI to mark assignment completed
    print("\nTesting AI Action: 'Mark my physics assignment completed'")
    msg2_res = requests.post(
        f"{BASE_URL}/chat/conversations/{conv_id}/messages/stream",
        headers=headers,
        json={"role": "user", "content": "Mark my physics assignment completed."}
    )
    assert msg2_res.status_code == 200
    updated_phys = requests.get(f"{BASE_URL}/study/assignments", headers=headers).json()
    completed_phys = [a for a in updated_phys if ("Physics" in a["title"] or "Physics" in a["subject_name"]) and a["status"] == "COMPLETED"]
    assert len(completed_phys) > 0, "AI tool failed to update assignment status to COMPLETED!"
    print("VERIFIED: AI updated DB assignment status to COMPLETED!")

    # Ask AI to schedule study session
    print("\nTesting AI Action: 'Schedule physics from 6 PM to 7 PM tomorrow'")
    msg3_res = requests.post(
        f"{BASE_URL}/chat/conversations/{conv_id}/messages/stream",
        headers=headers,
        json={"role": "user", "content": "Schedule physics study session from 6 PM to 7 PM tomorrow."}
    )
    assert msg3_res.status_code == 200
    cal_events = requests.get(f"{BASE_URL}/calendar/events", headers=headers).json()
    phys_sessions = [e for e in cal_events if "Physics" in e["title"]]
    assert len(phys_sessions) > 0, "AI tool failed to create calendar event in database!"
    print(f"VERIFIED: AI created real calendar event: '{phys_sessions[0]['title']}' at {phys_sessions[0]['start_time']}")

    print("\n>>> ALL STUDY, CALENDAR, AUTH, AND AI ACTION TESTS PASSED WITH 100% SUCCESS! <<<")

if __name__ == "__main__":
    test_study_and_calendar()
