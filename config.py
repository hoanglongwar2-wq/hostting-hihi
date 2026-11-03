import os
from pathlib import Path

BASE_DIR = Path(os.getenv("HOSTING_DATA_DIR", "/tmp/pyhost-data")).resolve()
PROJECTS_DIR = BASE_DIR / "projects"
DB_PATH = BASE_DIR / "hosting.db"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60 * 24
MAX_UPLOAD_MB = 2
MAX_PROJECTS_PER_USER = 3
MAX_FILES_PER_PROJECT = 30
MAX_FILE_BYTES = 200_000
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
