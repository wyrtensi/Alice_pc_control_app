"""Entry point for the HTTP API server."""

from __future__ import annotations

import uvicorn

from alice_pc_control_app.api import app


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
