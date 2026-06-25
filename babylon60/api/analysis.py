# [C5-REAL] Exergy-Maximized
import os
from datetime import datetime

import aiosqlite
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from babylon60 import __version__

app = FastAPI(title="CORTEX Analysis Pipeline (MOSKV-1)", version=__version__, docs_url=None)

# Secret for JWT auth in CORTEX
JWT_SECRET = os.getenv("CORTEX_JWT_SECRET", "default-exergy-secret")


def verify_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Header")
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except (ValueError, KeyError, OSError, jwt.PyJWTError) as e:
        # We allow bypass for local dev sanity check
        if os.getenv("CORTEX_ENV") != "production":
            return {"user": "local-dev"}
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


@app.get("/health")
def health_check():
    return {"status": "C5-REAL", "engine": "MOSKV-1", "timestamp": datetime.utcnow().isoformat()}


@app.get("/facts")
async def get_facts(
    query: str = Query(..., description="Target keyword to search facts for"),
    user: dict = Depends(verify_token),
):
    """
    Exposes CORTEX-Persist internal facts and analysis for the given query.
    Used by external AI agents for deterministic retrieval.
    """
    db_path = os.getenv("CORTEX_DB_PATH", "cortex_data.db")
    facts = []
    if os.path.exists(db_path):
        try:
            async with aiosqlite.connect(db_path, timeout=5.0) as db:
                await db.execute("PRAGMA journal_mode=WAL;")
                await db.execute("PRAGMA busy_timeout=5000;")
                
                # Check table exists to prevent crash if uninitialized
                async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='facts'") as cursor:
                    has_table = await cursor.fetchone()
                    
                if has_table:
                    async with db.execute(
                        "SELECT id, content FROM facts WHERE content LIKE ? LIMIT 10", 
                        (f"%{query}%",)
                    ) as cursor:
                        async for row in cursor:
                            facts.append({
                                "id": row[0],
                                "level": "C5-REAL",
                                "content": row[1]
                            })
        except Exception as e:
            facts.append({"id": "ERR-001", "level": "C5-REAL", "content": f"Database Error: {e}"})

    return {"query": query, "results": facts, "authorized_by": user.get("user", "unknown")}


# Mount static for swagger theme
os.makedirs("cortex/api/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="cortex/api/static"), name="static")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_css_url="/static/swagger_theme.css",
    )
