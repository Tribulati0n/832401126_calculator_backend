"""Configuration for the Flask application.

Every value can be overridden through environment variables so the same
code runs unchanged in local development, Docker and hosted platforms
such as Render.
"""

from __future__ import annotations

import os


class Config:
    # Where the SQLite file lives.  ``instance/`` keeps it out of the
    # repository; DATABASE_PATH overrides it (useful for ephemeral
    # filesystems on some hosts).
    INSTANCE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance")
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH", os.path.join(INSTANCE_DIR, "calculator.db")
    )

    # Origins allowed to call the API.  The front end is served from a
    # different origin in this separation architecture, so CORS must
    # explicitly admit it.  Comma-separated list or "*".
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS", "*"
    ).split(",")

    # Port used by ``app.run`` locally; hosted platforms inject PORT.
    PORT = int(os.environ.get("PORT", "5000"))
