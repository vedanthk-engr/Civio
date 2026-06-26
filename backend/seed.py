import json
import random
import uuid
import os
from datetime import datetime, timedelta
from backend.database import db

# Coordinate bounds for wards (from vertex_service)
WARD_BOUNDS = {
    "Indiranagar": {"north": 12.985, "south": 12.960, "east": 77.655, "west": 77.625, "zone": "East Zone"},
    "Koramangala": {"north": 12.948, "south": 12.920, "east": 77.640, "west": 77.610, "zone": "South Zone"},
    "Whitefield": {"north": 12.990, "south": 12.950, "east": 77.770, "west": 77.730, "zone": "Mahadevapura Zone"},
    "Jayanagar": {"north": 12.942, "south": 12.915, "east": 77.595, "west": 77.570, "zone": "South Zone"},
    "Malleshwaram": {"north": 13.010, "south": 12.985, "east": 77.580, "west": 77.555, "zone": "West Zone"},
    "HSR Layout": {"north": 12.925, "south": 12.895, "east": 77.660, "west": 77.630, "zone": "Bommanahalli Zone"}
}

CATEGORIES = {
    "POTHOLE": {
        "subcategories": ["deep pothole", "pothole cluster", "cracked surface", "subgrade depression"],
        "titles": ["Pothole on main crossing", "Deep pothole cluster", "Crumbling road edge", "Dangerous road dip"],
        "descriptions": ["Deep pothole causing motorbikes to skid near the turn.", "Several small potholes joined together, blocking the left lane.", "The side of the asphalt is breaking off, creating a steep drop.", "Slight depression in road asphalt is pooling water."],
        "dept": "Roads & Bridges"
    },
    "WATER_LEAK": {
        "subcategories": ["drinking water pipeline leak", "main valve leak", "sprinkler leak", "supply joint burst"],
        "titles": ["Drinking water pipe burst", "Valve leak flooding road", "Water line seepage", "Main line joint leak"],
        "descriptions": ["Clean drinking water has been gushing out of the pipe under the pavement.", "Municipal valve is leaking, causing flooding of the street.", "Water is slowly seeping from under the tiles, creating mud.", "Supply line joint is broken, water pressure is low in area."],
        "dept": "Water Supply & Sewerage"
    },
    "STREETLIGHT": {
        "subcategories": ["burnt bulb", "pole damage", "continuous glow", "wiring failure"],
        "titles": ["Flickering streetlight", "Completely dark streetlight", "Broke streetlight pole", "Daytime glow light"],
        "descriptions": ["The streetlight bulb is flickering, creating visual hazard.", "The light has been completely dark for a week, making street unsafe.", "A car hit the streetlight pole, now it is bent dangerously.", "Streetlight is glowing during daytime, wasting power."],
        "dept": "Electrical Engineering"
    },
    "WASTE": {
        "subcategories": ["dumpster overflow", "illegal garbage dump", "commercial waste dump"],
        "titles": ["Overflowing garbage bin", "Illegal garbage pile on corner", "Construction debris dump"],
        "descriptions": ["Public dumpster has not been cleared for 3 days. Trash is on the road.", "People are throwing domestic waste on the street corner.", "Unidentified truck dumped concrete debris on the footpath."],
        "dept": "Solid Waste Management"
    },
    "ROAD_DAMAGE": {
        "subcategories": ["missing manhole cover", "shoulder erosion", "speed breaker paint missing"],
        "titles": ["Missing storm drain cover", "Unmarked speed breaker", "Broken road divider"],
        "descriptions": ["A metal cover for the drain is missing, leaving a huge hole on street.", "New speed breaker has no reflective paint, dangerous at night.", "The concrete divider block has shifted into the driving lane."],
        "dept": "Roads & Bridges"
    },
    "ENCROACHMENT": {
        "subcategories": ["illegal shop extension", "hawkers blocking walkway", "vehicle parking block"],
        "titles": ["Shop display on pavement", "Hawkers blocking footpath", "Abandoned vehicle on road"],
        "descriptions": ["Shopkeeper has put metal racks on the public footpath.", "Multiple stalls are set up, forcing pedestrians to walk on main road.", "Old rust truck is parked permanently on the narrow side street."],
        "dept": "Town Planning & Revenue"
    },
    "SEWAGE": {
        "subcategories": ["clogged sewer line", "sewage overflow", "manhole leakage"],
        "titles": ["Sewage water backing up", "Leaking sewer manhole", "Foul smell sewer leak"],
        "descriptions": ["Black sewer water is bubbling up from the drain and running down the street.", "Manhole seal is broken, black water is oozing slowly.", "Sewer line blockage is causing backups in residential toilets."],
        "dept": "Water Supply & Sewerage"
    }
}

def get_random_coord(bounds):
    lat = random.uniform(bounds["south"], bounds["north"])
    lng = random.uniform(bounds["east"], bounds["west"])
    return lat, lng

def seed_demo_data():
    print("Seeding database with demo data...")
    
    # 1. Seed Users
    citizens = [
        {"id": "cit_1", "displayName": "Rohan Sharma", "photoURL": "", "ward": "Indiranagar", "role": "CITIZEN", "xp": 1450, "level": 4, "badges": ["Pothole Hunter", "First Responder"], "trustScore": 88.0, "issuesReported": 18, "issuesVerified": 12, "dailyStreak": 3},
        {"id": "cit_2", "displayName": "Priya Nair", "photoURL": "", "ward": "Koramangala", "role": "CITIZEN", "xp": 980, "level": 3, "badges": ["Water Guardian"], "trustScore": 75.0, "issuesReported": 10, "issuesVerified": 25, "dailyStreak": 0},
        {"id": "cit_3", "displayName": "Amit Patel", "photoURL": "", "ward": "Whitefield", "role": "CITIZEN", "xp": 2300, "level": 6, "badges": ["Patrol Pioneer", "Elite Scout", "Water Guardian"], "trustScore": 95.0, "issuesReported": 32, "issuesVerified": 45, "dailyStreak": 7},
        {"id": "cit_4", "displayName": "Sneha Reddy", "photoURL": "", "ward": "HSR Layout", "role": "CITIZEN", "xp": 420, "level": 2, "badges": [], "trustScore": 60.0, "issuesReported": 4, "issuesVerified": 8, "dailyStreak": 1}
    ]
    
    authorities = [
        {"id": "auth_1", "displayName": "Officer K. Rao (Roads)", "photoURL": "", "ward": "Indiranagar", "role": "AUTHORITY", "xp": 0, "level": 1, "badges": [], "trustScore": 100.0, "issuesReported": 0, "issuesVerified": 0},
        {"id": "auth_2", "displayName": "Officer M. Gowda (Water)", "photoURL": "", "ward": "Koramangala", "role": "AUTHORITY", "xp": 0, "level": 1, "badges": [], "trustScore": 100.0, "issuesReported": 0, "issuesVerified": 0},
        {"id": "auth_3", "displayName": "Officer S. Murthy (Waste)", "photoURL": "", "ward": "Whitefield", "role": "AUTHORITY", "xp": 0, "level": 1, "badges": [], "trustScore": 100.0, "issuesReported": 0, "issuesVerified": 0}
    ]
    
    for u in citizens + authorities:
        db.save_document("users", u["id"], u)
        
    # 2. Seed Quests
    quests = [
        {"id": "q1", "title": "Night Watch", "description": "Report 3 broken streetlights this week", "type": "REPORT", "requirements": {"action": "REPORT", "count": 3, "category": "STREETLIGHT"}, "reward": {"xp": 150, "title": "Light Keeper"}, "difficulty": "EASY"},
        {"id": "q2", "title": "Water Guardian", "description": "Verify 5 water leak reports in your ward", "type": "VERIFY", "requirements": {"action": "VERIFY", "count": 5, "category": "WATER_LEAK"}, "reward": {"xp": 200, "badgeId": "Water Guardian"}, "difficulty": "MEDIUM"},
        {"id": "q3", "title": "Patrol Pioneer", "description": "Complete a 500m neighbourhood patrol scan", "type": "PATROL", "requirements": {"action": "PATROL", "count": 1}, "reward": {"xp": 300}, "difficulty": "MEDIUM"},
        {"id": "q4", "title": "Monsoon Shield", "description": "Report 5 blocked drains before the rains", "type": "SPECIAL", "requirements": {"action": "REPORT", "count": 5, "category": "SEWAGE"}, "reward": {"xp": 500, "title": "Monsoon Shield"}, "difficulty": "HARD"}
    ]
    for q in quests:
        db.save_document("quests", q["id"], q)
        
    # 3. Seed 300 Issues
    random.seed(42) # stable coordinate seed
    
    statuses = ["REPORTED", "VERIFIED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]
    
    for i in range(300):
        issue_id = f"ISS-{100000 + i}"
        ward = random.choice(list(WARD_BOUNDS.keys()))
        bounds = WARD_BOUNDS[ward]
        lat, lng = get_random_coord(bounds)
        
        category = random.choice(list(CATEGORIES.keys()))
        cat_info = CATEGORIES[category]
        
        idx = random.randint(0, len(cat_info["subcategories"]) - 1)
        subcat = cat_info["subcategories"][idx]
        title = cat_info["titles"][idx]
        description = cat_info["descriptions"][idx]
        
        status = random.choice(statuses)
        # Weight statuses so older issues are resolved, newer are active
        reported_days_ago = random.randint(1, 365)
        reported_time = datetime.utcnow() - timedelta(days=reported_days_ago)
        
        if reported_days_ago > 30:
            status = random.choice(["RESOLVED", "CLOSED"])
        elif reported_days_ago > 10:
            status = random.choice(["ASSIGNED", "IN_PROGRESS", "RESOLVED"])
        else:
            status = random.choice(["REPORTED", "VERIFIED", "ASSIGNED"])
            
        severity = random.randint(2, 10)
        risk = "LOW"
        if severity >= 8: risk = "CRITICAL"
        elif severity >= 6: risk = "HIGH"
        elif severity >= 4: risk = "MEDIUM"
        
        cost = random.randint(1000, 25000)
        time_repair = f"{random.randint(1, 5)} hours" if severity < 7 else f"{random.randint(1, 3)} days"
        
        sla_hours = 24 if severity >= 9 else 72 if severity >= 7 else 168 if severity >= 4 else 336
        sla_deadline = reported_time + timedelta(hours=sla_hours)
        
        sla_breached = False
        resolved_time = None
        if status in ["RESOLVED", "CLOSED"]:
            resolved_days = random.randint(1, min(14, reported_days_ago))
            res_date = reported_time + timedelta(days=resolved_days)
            resolved_time = res_date.isoformat() + "Z"
            if res_date > sla_deadline:
                sla_breached = True
        else:
            if datetime.utcnow() > sla_deadline:
                sla_breached = True
                
        reporter = random.choice(citizens)["id"]
        
        issue_doc = {
            "id": issue_id,
            "title": f"{title} ({ward})",
            "description": description,
            "category": category,
            "subcategory": subcat,
            "location": {
                "lat": lat,
                "lng": lng,
                "address": f"Plot No. {random.randint(10, 499)}, Road No. {random.randint(1, 8)}, {ward}, Bengaluru",
                "ward": ward,
                "zone": bounds["zone"]
            },
            "mediaUrls": ["https://images.unsplash.com/photo-1515162305285-0293e4767cc2?q=80&w=300"],
            "thumbnailUrl": "https://images.unsplash.com/photo-1515162305285-0293e4767cc2?q=80&w=150",
            "aiAnalysis": {
                "severityScore": severity,
                "confidenceScore": round(random.uniform(0.75, 0.98), 2),
                "estimatedRepairCost": cost,
                "estimatedRepairTime": time_repair,
                "safetyRisk": risk,
                "structuralDamage": random.choice([True, False]) if severity > 6 else False,
                "geminiDescription": f"Technical inspection indicates structural failure of type {subcat}.",
                "duplicateOfId": None
            },
            "reportedBy": reporter,
            "verifiedBy": [random.choice(citizens)["id"] for _ in range(random.randint(0, 3))],
            "upvotes": random.randint(0, 30),
            "communityNotes": [f"Verified water seepage on site." for _ in range(random.randint(0, 1))],
            "status": status,
            "assignedDepartment": cat_info["dept"] if status in ["ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"] else None,
            "assignedOfficerId": random.choice(authorities)["id"] if status in ["ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"] else None,
            "reportedAt": reported_time.isoformat() + "Z",
            "slaDeadline": sla_deadline.isoformat() + "Z",
            "resolvedAt": resolved_time,
            "slaBreached": sla_breached,
            "reporterTrustScore": random.randint(60, 98),
            "validationScore": round(random.uniform(40, 95), 1)
        }
        
        # Save Issue
        db.save_document("issues", issue_id, issue_doc)
        
        # Seed matching Work Order for assigned / in progress / resolved issues
        if status in ["ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]:
            wo_id = f"WO-{random.randint(10000, 99999)}"
            wo_status = "SCHEDULED"
            if status == "RESOLVED" or status == "CLOSED":
                wo_status = "COMPLETED"
            elif status == "IN_PROGRESS":
                wo_status = "IN_PROGRESS"
                
            wo_doc = {
                "id": wo_id,
                "issueId": issue_id,
                "title": f"Repair Work Order: {title}",
                "description": f"Repair instruction log for {subcat}. Execute excavation, apply repair compound, and level surface.",
                "requiredMaterials": ["Asphalt Mix", "Sealant Clamps"] if category in ["POTHOLE", "ROAD_DAMAGE"] else ["PVC Pipe Joints", "Emulsion Seal"],
                "estimatedCost": cost,
                "estimatedDuration": time_repair,
                "requiredSkills": ["Civil Works"],
                "safetyNotes": "Wear boots, high-vis vests. Block lane access.",
                "department": cat_info["dept"],
                "assignedTo": issue_doc["assignedOfficerId"],
                "priority": "P1" if severity >= 9 else "P2" if severity >= 7 else "P3" if severity >= 4 else "P4",
                "scheduledDate": (reported_time + timedelta(days=1)).strftime("%Y-%m-%d"),
                "completedDate": (reported_time + timedelta(days=3)).strftime("%Y-%m-%d") if wo_status == "COMPLETED" else None,
                "status": wo_status,
                "createdAt": reported_time.isoformat() + "Z",
                "approvedBy": "auth_1"
            }
            db.save_document("work_orders", wo_id, wo_doc)
            db.update_document("issues", issue_id, {"workOrderId": wo_id})

    print(f"Seeding completed successfully! 300 issues seeded.")

if __name__ == "__main__":
    seed_demo_data()
