import requests

BASE_URL = "http://127.0.0.1:5000"


def test_server():
    print("\n" + "=" * 60)
    print("WORKFORCE MESH - FULL SYSTEM TEST")
    print("=" * 60)

    try:
        response = requests.get(
            f"{BASE_URL}/health",
            timeout=5
        )

        print("\n[1] Server Health")
        print("Status:", response.status_code)
        print("Response:", response.text)

    except Exception as e:
        print("\n[ERROR] Flask server is not running.")
        print("Start it using: python app.py")
        print(e)
        return False

    return True


def test_dashboard():
    print("\n[2] Dashboard")

    response = requests.get(
        f"{BASE_URL}/dashboard-state"
    )

    print("Status:", response.status_code)
    print("Response:", response.json())


def test_shortage():
    print("\n[3] Shortage Detection")

    data = {
        "required_workers": 80,
        "confirmed_workers": 52
    }

    response = requests.post(
        f"{BASE_URL}/detect-shortage",
        json=data
    )

    print("Status:", response.status_code)
    print("Response:", response.json())


def test_activate_mesh():
    print("\n[4] Activate Workforce Mesh")

    response = requests.post(
        f"{BASE_URL}/activate-mesh",
        json={
            "radius": 5
        }
    )

    print("Status:", response.status_code)
    print("Response:", response.json())


def test_worker_availability():
    print("\n[5] Worker Availability")

    response = requests.get(
        f"{BASE_URL}/worker-availability"
    )

    print("Status:", response.status_code)
    print("Response:", response.json())


def test_matching():
    print("\n[6] Wave 1 Worker Matching")

    data = {
        "required_skill": "Warehouse Operator",
        "shift_start": "6 PM",
        "shift_end": "10 PM",
        "radius": 5
    }

    response = requests.post(
        f"{BASE_URL}/find-suitable-workers",
        json=data
    )

    print("Status:", response.status_code)
    print("Response:", response.json())


def test_simulator():
    print("\n[7] What-if Simulator")

    data = {
        "required_workers": 100,
        "confirmed_workers": 52,
        "wave1_recovery": 15,
        "wave2_recovery": 12
    }

    response = requests.post(
        f"{BASE_URL}/simulate",
        json=data
    )

    print("Status:", response.status_code)

    result = response.json()

    print("Initial Shortage :", result.get("initial_shortage"))
    print("After Wave 1     :", result.get("after_wave1"))
    print("Wave 2 Recovery  :", result.get("wave2_recovery"))
    print("Final Shortage   :", result.get("final_shortage"))
    print("Scenario Result  :", result.get("scenario_status"))

    # Expected result
    print("\nExpected:")
    print("Initial Shortage = 48")
    print("After Wave 1     = 33")
    print("Wave 2 Recovery  = 12")
    print("Final Shortage   = 21")


def test_wave2():
    print("\n[8] Wave 2")

    response = requests.post(
        f"{BASE_URL}/wave2"
    )

    print("Status:", response.status_code)
    print("Response:", response.json())


def test_backup_workers():
    print("\n[9] Backup Workers")

    response = requests.get(
        f"{BASE_URL}/backup-workers"
    )

    print("Status:", response.status_code)
    print("Response:", response.json())


def test_wave2_check():
    print("\n[10] Wave 2 Requirement Check")

    response = requests.get(
        f"{BASE_URL}/check-wave2"
    )

    print("Status:", response.status_code)
    print("Response:", response.json())


def main():

    if not test_server():
        return

    test_dashboard()
    test_shortage()
    test_activate_mesh()
    test_worker_availability()
    test_matching()
    test_simulator()
    test_wave2()
    test_backup_workers()
    test_wave2_check()

    print("\n" + "=" * 60)
    print("FULL SYSTEM TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()