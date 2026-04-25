# producer/corridors.py

"""
Urban Traffic Pipeline — Corridor Definitions

Each corridor represents a real logistics route in Bangalore.

- No logic in this file
- Only static definitions
- Easy to extend (add/remove corridors without breaking anything)
"""

CORRIDORS = [
    {
        "route_id": "silk_board_to_hebbal",
        "origin": {"lat": 12.9176,"lng":77.6233},
        "destination": {"lat":13.0358,"lng":77.5970},
        "origin_label": "Silk Board Junction",
        "dest_label": "Hebbal Flyover",
        "tier": 1,
        "logistics_reason": "City spine — high variance corridor"
    },
    {
        "route_id": "nelamangala_to_hebbal",
        "origin": {"lat":13.1200,"lng":77.3900},
        "destination": {"lat":13.0358,"lng":77.5970},
        "origin_label": "Nelamangala Toll",
        "dest_label": "Hebbal Flyover",
        "tier": 1,
        "logistics_reason": "NH48 freight entry"
    },
    {
        "route_id": "orr_marathahalli_to_kr_puram",
        "origin": {"lat":12.9591,"lng":77.6974},
        "destination": {"lat":13.0050,"lng":77.6950},
        "origin_label": "Marathahalli Bridge",
        "dest_label": "KR Puram Bridge",
        "tier": 1,
        "logistics_reason": "ORR congestion cascade"
    },
    {
        "route_id": "koramangala_to_attibele",
        "origin": {"lat":12.9352,"lng":77.6245},
        "destination": {"lat":12.7800,"lng":77.7700},
        "origin_label": "Koramangala",
        "dest_label": "Attibele",
        "tier": 2,
        "logistics_reason": "TN freight corridor"
    },
    {
        "route_id": "dairy_circle_to_jigani",
        "origin": {"lat":12.9400,"lng":77.5900},
        "destination": {"lat":12.8000,"lng":77.6400},
        "origin_label": "Dairy Circle",
        "dest_label": "Jigani",
        "tier": 2,
        "logistics_reason": "Industrial corridor"
    }
]

