"""
auth.py
-------
Simple API KEY authentication. This is the same style used by many
real APIs for personal projects and server-to-server calls (Stripe's
"secret key" model, in spirit) — simpler to set up than a full
login/password system, but still means a stranger can't modify your
data just by finding your API's URL.

How it works:
  - The server has one secret value (from the API_KEY environment
    variable, or a default for local testing).
  - The client must send it in a request header: X-API-Key: <secret>
  - We only require this on WRITE endpoints (POST/PUT/DELETE).
    Reading data (GET) stays public, which is a common real pattern —
    e.g. anyone can view a public GitHub repo, but only you can push to it.
"""

import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

# In production you'd set this via an environment variable (see .env.example)
# rather than hard-coding it — never commit a real secret key to GitHub.
API_KEY = os.getenv("API_KEY", "dev-secret-key")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str = Security(api_key_header)):
    """
    A FastAPI dependency. Any endpoint that adds
        _: str = Depends(require_api_key)
    to its arguments will refuse to run unless the caller sent a
    matching X-API-Key header.
    """
    if key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Send it as an 'X-API-Key' header.",
        )
    return key