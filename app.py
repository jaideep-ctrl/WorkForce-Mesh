from flask import Flask, render_template, jsonify, request
import pandas as pd
import os

app = Flask(__name__)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

WORKERS_FILE = os.path.join(DATA_DIR, "workers.csv")
BACKUP_WORKERS_FILE = os.path.join(DATA_DIR, "backup_workers.csv")


# ============================================================
# DEMO STATE
# ============================================================

demo_state = {
    "required_workers": 80,
    "confirmed_workers": 52,

    "offers": [],

    "wave1_activated": False,
    "wave2_activated": False,

    "wave1_radius": 5,
    "wave2_radius": 10,

    "incentive": 0,

    "recovery_status": "Not Started"
}


# ============================================================
# LOAD WORKERS
# ============================================================

def load_workers():

    try:

        df = pd.read_csv(WORKERS_FILE)

        df["distance"] = pd.to_numeric(
            df["distance"],
            errors="coerce"
        )

        df["distance"] = df["distance"].fillna(0)

        return df.to_dict(orient="records")

    except Exception as e:

        print("Worker CSV Error:", e)

        return []


# ============================================================
# LOAD BACKUP WORKERS
# ============================================================

def load_backup_workers():

    try:

        df = pd.read_csv(BACKUP_WORKERS_FILE)

        df["distance"] = pd.to_numeric(
            df["distance"],
            errors="coerce"
        )

        df["distance"] = df["distance"].fillna(0)

        return df.to_dict(orient="records")

    except Exception as e:

        print("Backup Worker CSV Error:", e)

        return []


# ============================================================
# TIME CONVERSION
# ============================================================

def convert_to_hour(value):

    try:

        if value is None:
            return None

        value = str(value).strip()

        # Example:
        # "6 PM"
        # "10 PM"

        parts = value.split()

        if len(parts) == 2:

            time_part = parts[0]
            period = parts[1].upper()

            hour = int(
                time_part.split(":")[0]
            )

            if period == "PM" and hour != 12:
                hour += 12

            if period == "AM" and hour == 12:
                hour = 0

            return hour

        # Example:
        # "18"

        return int(value)

    except:

        return None


# ============================================================
# AVAILABILITY CHECK
# ============================================================

def check_availability(
    availability,
    shift_start,
    shift_end
):

    try:

        parts = str(
            availability
        ).split("-")

        if len(parts) != 2:
            return False

        worker_start = convert_to_hour(
            parts[0].strip()
        )

        worker_end = convert_to_hour(
            parts[1].strip()
        )

        if (
            worker_start is None
            or worker_end is None
        ):
            return False

        return (
            worker_start <= shift_start
            and worker_end >= shift_end
        )

    except:

        return False


# ============================================================
# MATCHING SCORE
# ============================================================

def calculate_score(
    worker,
    required_skill,
    shift_start,
    shift_end,
    radius
):

    score = 0

    reasons = []

    worker_skill = str(
        worker.get("skill", "")
    ).strip().lower()

    required_skill_lower = str(
        required_skill
    ).strip().lower()

    distance = float(
        worker.get("distance", 0)
    )

    availability = str(
        worker.get("availability", "")
    )

    # --------------------------------------------------------
    # SKILL
    # --------------------------------------------------------

    if worker_skill == required_skill_lower:

        score += 40

        reasons.append({
            "type": "success",
            "text": "Skill matched"
        })

    else:

        reasons.append({
            "type": "warning",
            "text": "Different skill"
        })

    # --------------------------------------------------------
    # DISTANCE
    # --------------------------------------------------------

    if distance <= radius:

        distance_score = max(
            0,
            int(
                30
                - (distance / radius) * 30
            )
        )

        score += distance_score

        reasons.append({
            "type": "success",
            "text": f"{distance} km away"
        })

    else:

        reasons.append({
            "type": "danger",
            "text":
                f"{distance} km outside radius"
        })

    # --------------------------------------------------------
    # AVAILABILITY
    # --------------------------------------------------------

    if check_availability(
        availability,
        shift_start,
        shift_end
    ):

        score += 30

        reasons.append({
            "type": "success",
            "text": "Available during shift"
        })

    else:

        reasons.append({
            "type": "warning",
            "text":
                "Availability does not fully match"
        })

    return {
        "score": min(score, 100),
        "reasons": reasons
    }


# ============================================================
# SHORTAGE
# ============================================================

def get_current_shortage():

    return max(
        0,
        demo_state["required_workers"]
        - demo_state["confirmed_workers"]
    )


# ============================================================
# OFFER COUNTS
# ============================================================

def get_offer_counts():

    offers = demo_state["offers"]

    accepted = len([
        o for o in offers
        if o["status"] == "Accepted"
    ])

    declined = len([
        o for o in offers
        if o["status"] == "Declined"
    ])

    pending = len([
        o for o in offers
        if o["status"] == "Pending"
    ])

    return {
        "total": len(offers),
        "accepted": accepted,
        "declined": declined,
        "pending": pending
    }


# ============================================================
# RECOVERY STATUS
# ============================================================

def calculate_recovery_status():

    shortage = get_current_shortage()

    counts = get_offer_counts()

    if shortage == 0:

        return "Recovered"

    if demo_state["wave2_activated"]:

        return "Wave 2 Active"

    if counts["pending"] > 0:

        return "Waiting for Responses"

    if (
        demo_state["wave1_activated"]
        and counts["pending"] == 0
        and shortage > 0
    ):

        return "Wave 1 Exhausted"

    if demo_state["wave1_activated"]:

        return "Wave 1 Active"

    return "Shortage Detected"


# ============================================================
# NEXT BEST ACTION
# ============================================================

def get_next_action():

    shortage = get_current_shortage()

    counts = get_offer_counts()

    # RECOVERED

    if shortage == 0:

        return {
            "type": "success",
            "title": "Workforce Fully Recovered",
            "message":
                "All required workers have been confirmed."
        }

    # WAVE 2 ACTIVE

    if demo_state["wave2_activated"]:

        return {
            "type": "danger",
            "title": "Wave 2 Active",
            "message":
                f"Searching within "
                f"{demo_state['wave2_radius']} km "
                f"with ₹{demo_state['incentive']} incentive."
        }

    # PENDING OFFERS

    if counts["pending"] > 0:

        return {
            "type": "info",
            "title": "Waiting for Worker Responses",
            "message":
                f"{counts['pending']} shift offer(s) "
                "are waiting for response."
        }

    # WAVE 1 EXHAUSTED

    if (
        demo_state["wave1_activated"]
        and counts["pending"] == 0
        and shortage > 0
    ):

        return {
            "type": "warning",
            "title": "Wave 1 Exhausted",
            "message":
                f"{shortage} worker(s) are still required. "
                "Activate Wave 2."
        }

    # WAVE 1 ACTIVE

    if demo_state["wave1_activated"]:

        return {
            "type": "info",
            "title": "Wave 1 Active",
            "message":
                "Suitable workers are being evaluated."
        }

    # SHORTAGE

    return {
        "type": "danger",
        "title": "Workforce Shortage Detected",
        "message":
            f"{shortage} worker(s) are required. "
            "Activate Workforce Mesh."
    }


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "dashboard.html"
    )


# ============================================================
# DETECT SHORTAGE
# ============================================================

@app.route(
    "/detect-shortage",
    methods=["POST"]
)
def detect_shortage():

    data = request.get_json() or {}

    required = int(
        data.get(
            "required_workers",
            80
        )
    )

    confirmed = int(
        data.get(
            "confirmed_workers",
            52
        )
    )

    demo_state["required_workers"] = required

    demo_state["confirmed_workers"] = confirmed

    return jsonify({

        "success": True,

        "required_workers":
            required,

        "confirmed_workers":
            confirmed,

        "shortage":
            get_current_shortage(),

        "next_action":
            get_next_action()

    })


# ============================================================
# ACTIVATE MESH
# ============================================================

@app.route(
    "/activate-mesh",
    methods=["POST"]
)
def activate_mesh():

    demo_state["wave1_activated"] = True

    return jsonify({

        "success": True,

        "message":
            "Workforce Mesh activated.",

        "wave1_activated":
            True,

        "next_action":
            get_next_action()

    })


# ============================================================
# FIND SUITABLE WORKERS
# ============================================================

@app.route(
    "/find-suitable-workers",
    methods=["POST"]
)
def find_suitable_workers():

    data = request.get_json() or {}

    required_skill = data.get(
        "skill",
        "Warehouse Operator"
    )

    radius = float(
        data.get(
            "radius",
            5
        )
    )

    # --------------------------------------------------------
    # GET SHIFT VALUES
    # --------------------------------------------------------

    shift_start_raw = data.get(
        "shift_start",
        "6 PM"
    )

    shift_end_raw = data.get(
        "shift_end",
        "10 PM"
    )

    # --------------------------------------------------------
    # CONVERT SHIFT START
    # --------------------------------------------------------

    shift_start = convert_to_hour(
        shift_start_raw
    )

    if shift_start is None:

        shift_start = 18

    # --------------------------------------------------------
    # CONVERT SHIFT END
    # --------------------------------------------------------

    shift_end = convert_to_hour(
        shift_end_raw
    )

    if shift_end is None:

        shift_end = 22

    # --------------------------------------------------------
    # LOAD WORKERS
    # --------------------------------------------------------

    workers = load_workers()

    matched_workers = []

    # --------------------------------------------------------
    # MATCH WORKERS
    # --------------------------------------------------------

    for worker in workers:

        distance = float(
            worker.get(
                "distance",
                0
            )
        )

        if distance > radius:
            continue

        result = calculate_score(
            worker,
            required_skill,
            shift_start,
            shift_end,
            radius
        )

        worker_data = dict(worker)

        worker_data["score"] = (
            result["score"]
        )

        worker_data["reasons"] = (
            result["reasons"]
        )

        worker_data["wave"] = 1

        matched_workers.append(
            worker_data
        )

    # --------------------------------------------------------
    # SORT BY SCORE
    # --------------------------------------------------------

    matched_workers.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return jsonify({

        "success": True,

        "workers":
            matched_workers,

        "count":
            len(matched_workers),

        "wave":
            1

    })


# ============================================================
# WORKER AVAILABILITY
# ============================================================

@app.route(
    "/worker-availability"
)
def worker_availability():

    return jsonify({

        "success": True,

        "workers":
            load_workers()

    })


# ============================================================
# MATCHED WORKERS
# ============================================================

@app.route(
    "/matched-workers"
)
def matched_workers():

    return jsonify({

        "success": True,

        "workers":
            load_workers()

    })


# ============================================================
# SEND OFFER
# ============================================================

@app.route(
    "/send-offer",
    methods=["POST"]
)
def send_offer():

    data = request.get_json() or {}

    worker_name = data.get(
        "worker_name"
    )

    score = data.get(
        "score",
        0
    )

    reasons = data.get(
        "reasons",
        []
    )

    wave = data.get(
        "wave",
        1
    )

    # DUPLICATE CHECK

    for offer in demo_state["offers"]:

        if offer["worker_name"] == worker_name:

            return jsonify({

                "success": False,

                "message":
                    "Offer already sent to this worker."

            }), 400

    # CREATE OFFER

    offer = {

        "id":
            len(demo_state["offers"]) + 1,

        "worker_name":
            worker_name,

        "score":
            score,

        "reasons":
            reasons,

        "wave":
            wave,

        "status":
            "Pending"
    }

    demo_state["offers"].append(
        offer
    )

    return jsonify({

        "success": True,

        "message":
            f"Shift offer sent to {worker_name}.",

        "offer":
            offer,

        "next_action":
            get_next_action()

    })


# ============================================================
# ACCEPT OFFER
# ============================================================

@app.route(
    "/accept-offer",
    methods=["POST"]
)
def accept_offer():

    data = request.get_json() or {}

    worker_name = data.get(
        "worker_name"
    )

    offer = next(
        (
            o for o in demo_state["offers"]
            if o["worker_name"] == worker_name
            and o["status"] == "Pending"
        ),
        None
    )

    if offer is None:

        return jsonify({

            "success": False,

            "message":
                "Pending offer not found."

        }), 404

    offer["status"] = "Accepted"

    if (
        demo_state["confirmed_workers"]
        < demo_state["required_workers"]
    ):

        demo_state["confirmed_workers"] += 1

    return jsonify({

        "success": True,

        "message":
            f"{worker_name} accepted the shift.",

        "confirmed_workers":
            demo_state["confirmed_workers"],

        "shortage":
            get_current_shortage(),

        "next_action":
            get_next_action()

    })


# ============================================================
# DECLINE OFFER
# ============================================================

@app.route(
    "/decline-offer",
    methods=["POST"]
)
def decline_offer():

    data = request.get_json() or {}

    worker_name = data.get(
        "worker_name"
    )

    offer = next(
        (
            o for o in demo_state["offers"]
            if o["worker_name"] == worker_name
            and o["status"] == "Pending"
        ),
        None
    )

    if offer is None:

        return jsonify({

            "success": False,

            "message":
                "Pending offer not found."

        }), 404

    offer["status"] = "Declined"

    return jsonify({

        "success": True,

        "message":
            f"{worker_name} declined the shift.",

        "shortage":
            get_current_shortage(),

        "next_action":
            get_next_action()

    })


# ============================================================
# OFFER STATUS
# ============================================================

@app.route(
    "/offer-status"
)
def offer_status():

    return jsonify({

        "success": True,

        "offers":
            demo_state["offers"],

        "counts":
            get_offer_counts(),

        "next_action":
            get_next_action()

    })


# ============================================================
# WAVE 2
# ============================================================

@app.route(
    "/wave2",
    methods=["POST"]
)
def activate_wave2():

    shortage = get_current_shortage()

    # DYNAMIC INCENTIVE

    if shortage <= 5:

        incentive = 50

    elif shortage <= 10:

        incentive = 100

    elif shortage <= 20:

        incentive = 150

    else:

        incentive = 200

    demo_state["wave2_activated"] = True

    demo_state["wave2_radius"] = 10

    demo_state["incentive"] = incentive

    return jsonify({

        "success": True,

        "message":
            "Wave 2 activated.",

        "radius":
            10,

        "incentive":
            incentive,

        "shortage":
            shortage,

        "next_action":
            get_next_action()

    })


# ============================================================
# BACKUP WORKERS
# ============================================================

@app.route(
    "/backup-workers"
)
def backup_workers():

    if not demo_state["wave2_activated"]:

        return jsonify({

            "success": False,

            "message":
                "Wave 2 is not active yet.",

            "workers": []

        })

    workers = load_backup_workers()

    matched_workers = []

    for worker in workers:

        distance = float(
            worker.get(
                "distance",
                0
            )
        )

        if distance > demo_state["wave2_radius"]:
            continue

        result = calculate_score(
            worker,
            "Warehouse Operator",
            18,
            22,
            demo_state["wave2_radius"]
        )

        worker_data = dict(worker)

        worker_data["score"] = (
            result["score"]
        )

        worker_data["reasons"] = (
            result["reasons"]
        )

        worker_data["wave"] = 2

        matched_workers.append(
            worker_data
        )

    matched_workers.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return jsonify({

        "success": True,

        "workers":
            matched_workers,

        "radius":
            demo_state["wave2_radius"],

        "incentive":
            demo_state["incentive"],

        "wave":
            2

    })


# ============================================================
# CHECK WAVE 2
# ============================================================

@app.route(
    "/check-wave2"
)
def check_wave2():

    shortage = get_current_shortage()

    counts = get_offer_counts()

    required = (
        shortage > 0
        and demo_state["wave1_activated"]
        and counts["pending"] == 0
    )

    return jsonify({

        "success": True,

        "wave2_required":
            required,

        "shortage":
            shortage,

        "pending":
            counts["pending"],

        "next_action":
            get_next_action()

    })
# ============================================================
# SIMULATOR
# ============================================================

@app.route(
    "/simulate",
    methods=["POST"]
)
def simulate():

    data = request.get_json() or {}

    # --------------------------------------------------------
    # INPUT VALUES
    # --------------------------------------------------------

    required = int(
        data.get(
            "required_workers",
            80
        )
    )

    confirmed = int(
        data.get(
            "confirmed_workers",
            52
        )
    )

    # Accept both possible frontend field names
    wave1_workers = int(
        data.get(
            "wave1_recovery",
            data.get(
                "wave1_workers",
                20
            )
        )
    )

    wave2_workers = int(
        data.get(
            "wave2_recovery",
            data.get(
                "wave2_workers",
                15
            )
        )
    )

    # --------------------------------------------------------
    # INITIAL SHORTAGE
    # --------------------------------------------------------

    initial_shortage = max(
        0,
        required - confirmed
    )

    # --------------------------------------------------------
    # WAVE 1 RECOVERY
    # --------------------------------------------------------

    wave1_recovery = min(
        initial_shortage,
        max(
            0,
            wave1_workers
        )
    )

    after_wave1 = max(
        0,
        initial_shortage - wave1_recovery
    )

    # --------------------------------------------------------
    # WAVE 2 RECOVERY
    # --------------------------------------------------------

    wave2_recovery = min(
        after_wave1,
        max(
            0,
            wave2_workers
        )
    )

    # --------------------------------------------------------
    # FINAL SHORTAGE
    # --------------------------------------------------------

    final_shortage = max(
        0,
        after_wave1 - wave2_recovery
    )

    # --------------------------------------------------------
    # SCENARIO STATUS
    # --------------------------------------------------------

    if final_shortage == 0:

        scenario_status = (
            "Workforce fully recoverable"
        )

    elif wave1_recovery == 0:

        scenario_status = (
            "Wave 1 cannot recover the shortage"
        )

    else:

        scenario_status = (
            "Additional workforce required"
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return jsonify({

        "success": True,

        "initial_shortage":
            initial_shortage,

        "wave1_recovery":
            wave1_recovery,

        "after_wave1":
            after_wave1,

        "wave2_recovery":
            wave2_recovery,

        "final_shortage":
            final_shortage,

        "scenario_status":
            scenario_status

    })
# ============================================================
# DASHBOARD STATE
# ============================================================

@app.route(
    "/dashboard-state"
)
def dashboard_state():

    shortage = get_current_shortage()

    counts = get_offer_counts()

    demo_state["recovery_status"] = (
        calculate_recovery_status()
    )

    return jsonify({

        "success": True,

        "required_workers":
            demo_state["required_workers"],

        "confirmed_workers":
            demo_state["confirmed_workers"],

        "shortage":
            shortage,

        "offers":
            demo_state["offers"],

        "offer_counts":
            counts,

        "wave1_activated":
            demo_state["wave1_activated"],

        "wave2_activated":
            demo_state["wave2_activated"],

        "wave1_radius":
            demo_state["wave1_radius"],

        "wave2_radius":
            demo_state["wave2_radius"],

        "incentive":
            demo_state["incentive"],

        "recovery_status":
            demo_state["recovery_status"],

        "next_action":
            get_next_action()

    })


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/health"
)
def health():

    return jsonify({

        "status": "OK",

        "version":
            "Step 3E Part 3 - Real-time Recovery Intelligence"

    })


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("WORKFORCE MESH")
    print("Adaptive Workforce Recovery")
    print("=" * 60)
    print()
    print("Server running at:")
    print("http://127.0.0.1:5000")
    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )