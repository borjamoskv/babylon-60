# [C5-REAL] Exergy-Maximized
"""
Outreach Router.

API endpoints for B2B developer outreach pipeline of CORTEX Persist.
Allows viewing leads, monitoring stats, and triggering extraction/outreach batches.
"""

import csv
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel

from cortex import config
from cortex.auth import require_permission


# Helper dependency to bypass authentication on localhost/developer local mode
def require_local_or_permission(permission: str):
    if config.DEPLOY_MODE == "local":
        async def bypass():
            return None
        return bypass
    else:
        return require_permission(permission)

# Import local outreach functions dynamically to avoid boot conflicts
from scratch.github_lead_extractor import main as run_extractor
from scratch.github_lead_outreach import send_outreach_emails as run_outreach

logger = logging.getLogger("cortex.routes.outreach")

router = APIRouter(prefix="/v1/outreach", tags=["outreach"])

# Global operation states
_status_state = {
    "is_extracting": False,
    "is_sending": False,
    "last_error": None,
    "last_run_summary": None
}

CSV_PATH = "scratch/github_leads_cortex.csv"
LOG_PATH = "scratch/sent_leads_log.json"

class ExtractRequest(BaseModel):
    target_leads: int = 10
    queries: Optional[list[str]] = None

class OutreachRequest(BaseModel):
    limit: int = 5

def background_extract(target: int, queries: Optional[list[str]]):
    global _status_state
    _status_state["is_extracting"] = True
    _status_state["last_error"] = None
    try:
        run_extractor(target_leads=target, output_file=CSV_PATH, custom_queries=queries)
    except Exception as e:
        logger.error(f"Error in background lead extraction: {e}")
        _status_state["last_error"] = f"Extraction failed: {str(e)}"
    finally:
        _status_state["is_extracting"] = False

def background_send(limit: int):
    global _status_state
    _status_state["is_sending"] = True
    _status_state["last_error"] = None
    try:
        summary = run_outreach(limit=limit)
        _status_state["last_run_summary"] = summary
    except Exception as e:
        logger.error(f"Error in background email outreach: {e}")
        _status_state["last_error"] = f"Outreach failed: {str(e)}"
    finally:
        _status_state["is_sending"] = False

@router.get("/stats")
async def get_stats(
    _=Depends(require_local_or_permission("read"))
):
    """Get outreach status and summary statistics."""
    total_leads = 0
    languages = {"es": 0, "en": 0}
    repos = {}
    
    # Read leads CSV
    if os.path.exists(CSV_PATH):
        try:
            with open(CSV_PATH, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    total_leads += 1
                    lang = row.get("Language", "en") or "en"
                    languages[lang] = languages.get(lang, 0) + 1
                    repo = row.get("Repo", "unknown")
                    repos[repo] = repos.get(repo, 0) + 1
        except Exception as e:
            logger.warning(f"Error reading CSV stats: {e}")

    # Read sent emails log
    sent_emails = []
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH) as f:
                sent_emails = json.load(f)
        except Exception as e:
            logger.warning(f"Error reading sent log stats: {e}")

    sent_count = len(sent_emails)
    pending_count = max(0, total_leads - sent_count)

    return {
        "status": {
            "is_extracting": _status_state["is_extracting"],
            "is_sending": _status_state["is_sending"],
            "last_error": _status_state["last_error"],
            "last_run_summary": _status_state["last_run_summary"]
        },
        "stats": {
            "total_leads": total_leads,
            "sent_emails": sent_count,
            "pending_emails": pending_count,
            "languages": languages,
            "top_repos": dict(sorted(repos.items(), key=lambda x: x[1], reverse=True)[:5])
        }
    }

@router.get("/leads")
async def get_leads(
    limit: int = Query(100, ge=1, le=1000),
    language: Optional[str] = None,
    status: Optional[str] = None,
    _=Depends(require_local_or_permission("read"))
):
    """Retrieve extracted leads with their email status."""
    leads = []
    
    # Load sent emails list
    sent_emails = set()
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH) as f:
                sent_emails = set(json.load(f))
        except Exception as e:
            logger.warning(f"Error loading sent log: {e}")

    if not os.path.exists(CSV_PATH):
        return []

    try:
        with open(CSV_PATH, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get("Email", "").strip()
                is_sent = email in sent_emails
                lead_status = "Sent" if is_sent else "Pending"
                
                lead_lang = row.get("Language", "en") or "en"
                
                # Filters
                if language and lead_lang != language:
                    continue
                if status and lead_status.lower() != status.lower():
                    continue

                leads.append({
                    "username": row.get("Username", ""),
                    "name": row.get("Name", ""),
                    "email": email,
                    "company": row.get("Company", ""),
                    "website": row.get("Website", ""),
                    "location": row.get("Location", ""),
                    "bio": row.get("Bio", ""),
                    "github_url": row.get("GitHub URL", ""),
                    "repo": row.get("Repo", ""),
                    "language": lead_lang,
                    "status": lead_status
                })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading CSV: {str(e)}")

    # Slice the results
    return leads[:limit]

@router.post("/extract")
async def extract_leads(
    request: ExtractRequest,
    background_tasks: BackgroundTasks,
    _=Depends(require_local_or_permission("write"))
):
    """Trigger background job to extract more GitHub leads."""
    if _status_state["is_extracting"]:
        raise HTTPException(status_code=400, detail="Extraction task is already running.")
    
    background_tasks.add_task(background_extract, request.target_leads, request.queries)
    return {"status": "Extraction started in background", "target_leads": request.target_leads}

@router.post("/send")
async def send_outreach(
    request: OutreachRequest,
    background_tasks: BackgroundTasks,
    _=Depends(require_local_or_permission("write"))
):
    """Trigger background outreach batch email execution."""
    if _status_state["is_sending"]:
        raise HTTPException(status_code=400, detail="Outreach sender task is already running.")
    
    background_tasks.add_task(background_send, request.limit)
    return {"status": "Outreach batch execution started in background", "limit": request.limit}

@router.post("/reset")
async def reset_sent_log(
    _=Depends(require_local_or_permission("write"))
):
    """Clear sent emails log to allow re-sending outreach (developer option)."""
    try:
        with open(LOG_PATH, "w") as f:
            json.dump([], f)
        _status_state["last_run_summary"] = None
        return {"status": "Sent log reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset log: {str(e)}")
