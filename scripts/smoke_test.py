#!/usr/bin/env python3
import sys
import time
import requests

BASE_URL = "http://localhost:8000"

def main():
    print("=" * 60)
    print("      GOVERNMENT SCHEME AGENT - SMOKE TEST PIPELINE")
    print("=" * 60)

    # 1. Health Check
    print("\n[1/7] Testing GET /health...")
    try:
        res = requests.get(f"{BASE_URL}/health", timeout=5)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        print("  ✓ Health check passed!")
    except Exception as e:
        print(f"  ❌ Health check failed: {e}")
        sys.exit(1)

    # 2. Signup
    print("\n[2/7] Testing POST /auth/signup...")
    email = f"smoketest_{int(time.time())}@example.com"
    signup_payload = {
        "name": "Smoke Test Citizen",
        "email": email,
        "password": "Password123!",
        "consent": True
    }
    res = requests.post(f"{BASE_URL}/auth/signup", json=signup_payload, timeout=5)
    assert res.status_code == 201, f"Signup failed: {res.text}"
    print(f"  ✓ User created: {email}")

    # 3. Login
    print("\n[3/7] Testing POST /auth/login...")
    login_res = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": email, "password": "Password123!"},
        timeout=5
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  ✓ Login successful, JWT token acquired!")

    # 4. Profile Update
    print("\n[4/7] Testing PUT /profile...")
    prof_payload = {
        "age": 22,
        "gender": "female",
        "state": "Maharashtra",
        "district": "Pune",
        "annual_income": 120000.0,
        "social_category": "SC"
    }
    prof_res = requests.put(f"{BASE_URL}/profile", json=prof_payload, headers=headers, timeout=5)
    assert prof_res.status_code == 200, f"Profile update failed: {prof_res.text}"
    print("  ✓ Profile updated successfully!")

    # 5. Mode 1 Discovery
    print("\n[5/7] Testing Mode 1 Discovery (POST /discover/query)...")
    query_payload = {"prompt": "scholarship for engineering student in maharashtra"}
    m1_res = requests.post(f"{BASE_URL}/discover/query", json=query_payload, headers=headers, timeout=10)
    assert m1_res.status_code == 200, f"Mode 1 failed: {m1_res.text}"
    m1_data = m1_res.json()
    print(f"  ✓ Mode 1 returned {len(m1_data.get('results', []))} scheme matches!")

    # 6. Mode 2 Discovery
    print("\n[6/7] Testing Mode 2 Discovery (POST /discover/profile)...")
    m2_res = requests.post(f"{BASE_URL}/discover/profile", json={}, headers=headers, timeout=10)
    assert m2_res.status_code == 200, f"Mode 2 failed: {m2_res.text}"
    m2_data = m2_res.json()
    print(f"  ✓ Mode 2 returned {len(m2_data.get('results', []))} matched schemes!")

    # 7. Notifications
    print("\n[7/7] Testing GET /notifications...")
    notif_res = requests.get(f"{BASE_URL}/notifications", headers=headers, timeout=5)
    assert notif_res.status_code == 200, f"Notifications failed: {notif_res.text}"
    print(f"  ✓ Notifications endpoint returned {len(notif_res.json().get('notifications', []))} items!")

    print("\n" + "=" * 60)
    print("      🎉 ALL SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
