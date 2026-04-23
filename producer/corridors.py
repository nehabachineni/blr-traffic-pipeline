# producer/corridors.py

"""
Urban Traffic Pipeline — Corridor Definitions

Each corridor represents a real logistics route in Bangalore.

Rules:
- No logic in this file
- Only static definitions
- Easy to extend (add/remove corridors without breaking anything)
"""

CORRIDORS = [
    {
        "route_id": "silk_board_to_hebbal",
        "origin": "12.9176,77.6233",
        "destination": "13.0358,77.5970",
        "origin_label": "Silk Board Junction",
        "dest_label": "Hebbal Flyover",
        "tier": 1,
        "logistics_reason": "City spine — high variance corridor"
    },
    {
        "route_id": "nelamangala_to_hebbal",
        "origin": "13.1200,77.3900",
        "destination": "13.0358,77.5970",
        "origin_label": "Nelamangala Toll",
        "dest_label": "Hebbal Flyover",
        "tier": 1,
        "logistics_reason": "NH48 freight entry"
    },
    {
        "route_id": "orr_marathahalli_to_kr_puram",
        "origin": "12.9591,77.6974",
        "destination": "13.0050,77.6950",
        "origin_label": "Marathahalli Bridge",
        "dest_label": "KR Puram Bridge",
        "tier": 1,
        "logistics_reason": "ORR congestion cascade"
    },
    {
        "route_id": "koramangala_to_attibele",
        "origin": "12.9352,77.6245",
        "destination": "12.7800,77.7700",
        "origin_label": "Koramangala",
        "dest_label": "Attibele",
        "tier": 2,
        "logistics_reason": "TN freight corridor"
    },
    {
        "route_id": "dairy_circle_to_jigani",
        "origin": "12.9400,77.5900",
        "destination": "12.8000,77.6400",
        "origin_label": "Dairy Circle",
        "dest_label": "Jigani",
        "tier": 2,
        "logistics_reason": "Industrial corridor"
    }
]

