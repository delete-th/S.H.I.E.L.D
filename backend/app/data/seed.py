"""
Generates mock Singapore-context data for demo purposes.
Run once: python -m app.data.seed
"""
import json
import random
import uuid
from datetime import datetime, timedelta
from faker import Faker

fake = Faker("en_GB")  # closest to Singapore English naming
random.seed(42)

# --- Singapore-realistic data pools ---

SG_LOCATIONS = [
    "Jurong East MRT", "Tampines Mall", "Orchard Road",
    "Bugis Junction", "Woodlands Checkpoint", "Changi Airport T3",
    "HDB Block 412 Ang Mo Kio", "Sengkang Bus Interchange",
    "Punggol Waterway", "Toa Payoh Central", "Bishan Park",
    "Raffles Place MRT", "Clementi MRT", "Yishun Bus Interchange",
    "Bedok North Ave 3", "Geylang Lorong 14", "Pasir Ris Park",
    "Boon Lay Shopping Centre", "Choa Chu Kang MRT", "Serangoon NEX"
]

INCIDENT_TYPES = [
    "Theft", "Vandalism", "Suspicious Person", "Trespassing",
    "Public Disturbance", "Assault", "Shoplifting", "Fight",
    "Drunk and Disorderly", "Missing Person", "Drug Suspicious Activity",
    "Vehicle Break-in", "Harassment", "Unlicensed Hawking"
]

SEVERITIES = ["low", "medium", "high", "critical"]
SEVERITY_WEIGHTS = [0.4, 0.35, 0.2, 0.05]  # most are low/medium

STATUSES = ["open", "closed", "under_investigation"]
STATUS_WEIGHTS = [0.3, 0.5, 0.2]

NATIONALITIES = ["Singaporean", "Malaysian", "Chinese National", "Indian National", "Filipino"]

CLOTHING = [
    "black hoodie", "white t-shirt", "blue jeans", "red jacket",
    "grey sweater", "green polo shirt", "black cap", "yellow raincoat"
]

HAIR = ["short black", "long brown", "bald", "short grey", "dyed blonde"]

BUILD = ["slim", "medium build", "stocky", "tall and thin", "short and stout"]

OFFENCE_TYPES = [
    "Theft under Section 379 PC",
    "Mischief under Section 426 PC",
    "Voluntarily causing hurt under Section 323 PC",
    "Criminal trespass under Section 447 PC",
    "Possession of controlled drugs under MDA",
    "Disorderly behaviour under MOPA",
    "Outrage of modesty under Section 354 PC",
    "Cheating under Section 420 PC"
]

# --- Generator functions ---

def random_sg_datetime(days_back: int = 365) -> str:
    dt = datetime.now() - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )
    return dt.isoformat()

def generate_cases(n: int = 100) -> list:
    cases = []
    for _ in range(n):
        severity = random.choices(SEVERITIES, SEVERITY_WEIGHTS)[0]
        status = random.choices(STATUSES, STATUS_WEIGHTS)[0]
        incident_type = random.choice(INCIDENT_TYPES)
        location = random.choice(SG_LOCATIONS)

        cases.append({
            "id": str(uuid.uuid4()),
            "incident_type": incident_type,
            "location": location,
            "severity": severity,
            "status": status,
            "description": (
                f"{incident_type} reported at {location}. "
                f"Victim {fake.first_name()} {fake.last_name()} reported the incident. "
                f"{'Suspect fled before officers arrived.' if random.random() > 0.5 else 'Suspect apprehended on scene.'}"
            ),
            "officer_id": f"C-{random.randint(1000, 9999)}",
            "created_at": random_sg_datetime(),
            "resolved": status == "closed"
        })
    return cases

def generate_offenders(n: int = 50) -> list:
    offenders = []
    for _ in range(n):
        gender = random.choice(["Male", "Female"])
        age = random.randint(17, 65)
        offenders.append({
            "id": str(uuid.uuid4()),
            "name": fake.name_male() if gender == "Male" else fake.name_female(),
            "nric_last4": f"{''.join(random.choices('0123456789', k=3))}{random.choice('ABCDEFGHIJZ')}",
            "age": age,
            "gender": gender,
            "nationality": random.choice(NATIONALITIES),
            "description": {
                "height_cm": random.randint(155, 185),
                "build": random.choice(BUILD),
                "hair": random.choice(HAIR),
                "last_seen_wearing": random.choice(CLOTHING)
            },
            "known_offences": random.sample(OFFENCE_TYPES, k=random.randint(1, 3)),
            "last_known_location": random.choice(SG_LOCATIONS),
            "risk_level": random.choices(
                ["low", "medium", "high"],
                weights=[0.5, 0.35, 0.15]
            )[0],
            "outstanding_warrant": random.random() > 0.75,
            "last_updated": random_sg_datetime(days_back=180)
        })
    return offenders

def generate_cctv_locations(n: int = 30) -> list:
    """
    Mock CCTV camera positions around Singapore.
    lat/lng are real Singapore coordinates with small random offsets.
    """
    base_coords = [
        (1.3521, 103.8198),   # central
        (1.3000, 103.8500),   # east
        (1.4000, 103.7800),   # north
        (1.3200, 103.7500),   # west
        (1.2800, 103.8300),   # south
    ]

    cameras = []
    for i in range(n):
        base = random.choice(base_coords)
        cameras.append({
            "id": f"CAM-{str(i+1).zfill(3)}",
            "location_name": random.choice(SG_LOCATIONS),
            "lat": round(base[0] + random.uniform(-0.02, 0.02), 6),
            "lng": round(base[1] + random.uniform(-0.02, 0.02), 6),
            "status": random.choices(
                ["online", "offline", "maintenance"],
                weights=[0.8, 0.1, 0.1]
            )[0],
            "feed_url": f"rtsp://mock-cctv/{i+1}/stream",  # mock RTSP URL
            "last_checked": random_sg_datetime(days_back=1)
        })
    return cameras


# --- Main ---

if __name__ == "__main__":
    import os
    os.makedirs("app/data", exist_ok=True)

    print("Generating mock cases...")
    cases = generate_cases(100)
    with open("app/data/mock_cases.json", "w") as f:
        json.dump(cases, f, indent=2)
    print(f"  ✓ {len(cases)} cases written to app/data/mock_cases.json")

    print("Generating mock offenders...")
    offenders = generate_offenders(50)
    with open("app/data/mock_offenders.json", "w") as f:
        json.dump(offenders, f, indent=2)
    print(f"  ✓ {len(offenders)} offenders written to app/data/mock_offenders.json")

    print("Generating mock CCTV locations...")
    cameras = generate_cctv_locations(30)
    with open("app/data/mock_cctv_locations.json", "w") as f:
        json.dump(cameras, f, indent=2)
    print(f"  ✓ {len(cameras)} cameras written to app/data/mock_cctv_locations.json")

    print("\n✅ All mock data generated successfully.")