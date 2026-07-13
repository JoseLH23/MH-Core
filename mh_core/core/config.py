from pathlib import Path


# ===========================
# MH CORE CONFIGURATION
# ===========================

PROJECT_NAME = "MH Core"
VERSION = "2.0"

# Base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Base de datos
DATABASE_DIR = BASE_DIR / "database"

LEARNING_DIR = DATABASE_DIR / "learning"

HISTORY_FILE = LEARNING_DIR / "history.json"

# Logs
LOG_DIR = BASE_DIR.parent / "logs"

LOG_FILE = LOG_DIR / "mh_core.log"

# Dashboard
DASHBOARD_NAME = "MH Core Dashboard"

# Brain
BRAIN_NAME = "MH Brain"

# Prediction
DEFAULT_SUCCESS_THRESHOLD = 70

# Debug
DEBUG = True