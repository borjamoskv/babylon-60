# [C5-REAL] Exergy-Maximized
import os
import csv
import json
import tempfile
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from cortex.routes import outreach as outreach_router

@pytest.fixture
def temp_outreach_files(monkeypatch):
    # Create temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "leads.csv")
        log_path = os.path.join(tmpdir, "sent_log.json")
        
        # Write dummy CSV leads
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Username", "Name", "Email", "Company", "Website", "Location", "Bio", "GitHub URL", "Repo", "Language"])
            writer.writeheader()
            writer.writerow({
                "Username": "testuser1",
                "Name": "Test User 1",
                "Email": "user1@example.com",
                "Company": "AI Corp",
                "Website": "http://user1.ai",
                "Location": "Madrid, Spain",
                "Bio": "AI agent engineer developing ZK memory persistence",
                "GitHub URL": "https://github.com/testuser1",
                "Repo": "owner/repo1",
                "Language": "es"
            })
            writer.writerow({
                "Username": "testuser2",
                "Name": "Test User 2",
                "Email": "user2@example.com",
                "Company": "Web3 Labs",
                "Website": "http://user2.io",
                "Location": "San Francisco, USA",
                "Bio": "ZK researcher building vector persistance layers",
                "GitHub URL": "https://github.com/testuser2",
                "Repo": "owner/repo2",
                "Language": "en"
            })

        # Write dummy sent log
        with open(log_path, "w") as f:
            json.dump(["user1@example.com"], f)

        # Monkeypatch the paths in outreach router module
        monkeypatch.setattr(outreach_router, "CSV_PATH", csv_path)
        monkeypatch.setattr(outreach_router, "LOG_PATH", log_path)
        
        yield csv_path, log_path

def test_get_outreach_stats(temp_outreach_files) -> None:
    app = FastAPI()
    app.include_router(outreach_router.router)

    with TestClient(app) as client:
        response = client.get("/v1/outreach/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["total_leads"] == 2
    assert data["stats"]["sent_emails"] == 1
    assert data["stats"]["pending_emails"] == 1
    assert data["stats"]["languages"]["es"] == 1
    assert data["stats"]["languages"]["en"] == 1
    assert data["stats"]["top_repos"] == {"owner/repo1": 1, "owner/repo2": 1}
    assert data["status"]["is_extracting"] is False
    assert data["status"]["is_sending"] is False

def test_get_outreach_leads(temp_outreach_files) -> None:
    app = FastAPI()
    app.include_router(outreach_router.router)

    with TestClient(app) as client:
        response = client.get("/v1/outreach/leads")

    assert response.status_code == 200
    leads = response.json()
    assert len(leads) == 2
    
    # Check lead 1 details
    lead1 = next(lead for lead in leads if lead["username"] == "testuser1")
    assert lead1["name"] == "Test User 1"
    assert lead1["email"] == "user1@example.com"
    assert lead1["language"] == "es"
    assert lead1["status"] == "Sent"

    # Check lead 2 details
    lead2 = next(lead for lead in leads if lead["username"] == "testuser2")
    assert lead2["name"] == "Test User 2"
    assert lead2["email"] == "user2@example.com"
    assert lead2["language"] == "en"
    assert lead2["status"] == "Pending"

def test_reset_sent_log(temp_outreach_files) -> None:
    csv_path, log_path = temp_outreach_files
    app = FastAPI()
    app.include_router(outreach_router.router)

    with TestClient(app) as client:
        response = client.post("/v1/outreach/reset")

    assert response.status_code == 200
    assert response.json()["status"] == "Sent log reset successfully"

    # Verify that the sent log file has indeed been cleared
    with open(log_path) as f:
        sent_emails = json.load(f)
    assert len(sent_emails) == 0
