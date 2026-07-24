from __future__ import annotations

from pathlib import Path
import os


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent
ENGINE_ROOT = REPO_ROOT / "director-os"
PRODUCT_ROOT = REPO_ROOT / "director-os-product"
INTEGRATIONS_ROOT = REPO_ROOT / "director-os-integrations"
REFERENCE_ROOT = REPO_ROOT / "director-os-reference"
DATA_ROOT = APP_ROOT / "data"
DATABASE_PATH = Path(os.environ.get("DIRECTOR_OS_DATABASE", str(DATA_ROOT / "director_os.sqlite")))
JOB_PACKAGE_ROOT = APP_ROOT / "job-packages"
MANUAL_EXPORT_ROOT = APP_ROOT / "manual-exports"
RESULT_MEDIA_ROOT = Path(os.environ.get("DIRECTOR_OS_RESULT_MEDIA_ROOT", str(APP_ROOT / "result-media")))
MAX_RESULT_UPLOAD_BYTES = int(os.environ.get("DIRECTOR_OS_MAX_RESULT_UPLOAD_BYTES", str(500 * 1024 * 1024)))

APP_NAME = "Director OS"
APP_VERSION = "1.0"
HOST = "127.0.0.1"
PORT = 8787
