from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional
from backend.database import db

router = APIRouter(prefix="/gamification", tags=["Gamification"])

@router.get("/quests")
async def list_active_quests(userId: str = Query(...)):
    user = db.get_document("users", userId)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    all_quests = db.list_documents("quests")
    
    # Format and check completion status
    completed = user.get("completedQuests", [])
    active = []
    
    for q in all_quests:
        q_id = q["id"]
        is_done = q_id in completed
        # Simulate partial progress for demo purposes
        # Amit Patel (cit_3) has active progress, Sneha (cit_4) has some, etc.
        progress = 0
        if is_done:
            progress = q["requirements"]["count"]
        elif userId == "cit_3":
            progress = min(q["requirements"]["count"] - 1, 2)
        elif userId == "cit_1" and q["requirements"].get("category") == "STREETLIGHT":
            progress = 2
            
        active.append({
            "quest": q,
            "completed": is_done,
            "progress": progress,
            "target": q["requirements"]["count"]
        })
        
    return active

@router.post("/progress")
async def update_quest_progress(payload: dict = Body(...)):
    userId = payload.get("userId")
    action_type = payload.get("action")  # "REPORT" | "VERIFY" | "PATROL"
    category = payload.get("category")
    
    if not userId or not action_type:
        raise HTTPException(status_code=400, detail="Missing 'userId' or 'action' in request body")
        
    user = db.get_document("users", userId)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    quests = db.list_documents("quests")
    updated = False
    newly_completed = []
    
    completed_list = user.get("completedQuests", [])
    
    for q in quests:
        q_id = q["id"]
        if q_id in completed_list:
            continue
            
        req = q["requirements"]
        if req["action"] == action_type:
            # Check category requirement
            if req.get("category") and req.get("category") != category:
                continue
                
            # For hackathon demo, trigger direct completion of matching quests on action
            completed_list.append(q_id)
            newly_completed.append(q_id)
            
            # Award reward
            reward = q["reward"]
            user["xp"] = user.get("xp", 0) + reward.get("xp", 100)
            user["level"] = 1 + (user["xp"] // 500)
            
            if reward.get("badgeId"):
                badges = user.get("badges", [])
                if reward["badgeId"] not in badges:
                    badges.append(reward["badgeId"])
                    user["badges"] = badges
                    
            if reward.get("title"):
                # Title reward
                badges = user.get("badges", [])
                title_badge = f"Title: {reward['title']}"
                if title_badge not in badges:
                    badges.append(title_badge)
                    user["badges"] = badges
            
            updated = True
            
    if updated:
        user["completedQuests"] = completed_list
        # Increment action stats
        if action_type == "REPORT":
            user["issuesReported"] = user.get("issuesReported", 0) + 1
        elif action_type == "VERIFY":
            user["issuesVerified"] = user.get("issuesVerified", 0) + 1
            
        db.save_document("users", userId, user)
        
    return {
        "success": True,
        "newlyCompleted": newly_completed,
        "userStats": {
            "xp": user.get("xp"),
            "level": user.get("level"),
            "badges": user.get("badges")
        }
    }

@router.get("/leaderboard")
async def get_leaderboard(ward: Optional[str] = None):
    users = db.list_documents("users")
    # Filter only citizens for leaderboard
    citizens = [x for x in users if x.get("role") == "CITIZEN"]
    if ward:
        citizens = [x for x in citizens if x.get("ward") == ward]
        
    # Sort by XP descending
    citizens.sort(key=lambda item: item.get("xp", 0), reverse=True)
    
    leaderboard = []
    for idx, c in enumerate(citizens):
        leaderboard.append({
            "rank": idx + 1,
            "userId": c["id"],
            "displayName": c["displayName"],
            "xp": c["xp"],
            "level": c["level"],
            "badgesCount": len(c.get("badges", [])),
            "trustScore": c.get("trustScore", 50.0),
            "ward": c.get("ward")
        })
    return leaderboard
