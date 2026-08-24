import os
from dotenv import load_dotenv

# Load .env file
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(project_root, ".env"))

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres_secure_pwd@localhost:5432/bbsr_digital_twin")

# API Keys and Passwords (e.g. for Copernicus Open Access Hub, CDSE, or EarthEngine)
CDSE_USERNAME = os.getenv("CDSE_USERNAME", None)
CDSE_PASSWORD = os.getenv("CDSE_PASSWORD", None)

# Request parameters
REQUEST_TIMEOUT = int(os.getenv("ETL_REQUEST_TIMEOUT", "60"))
MAX_RETRIES = int(os.getenv("ETL_MAX_RETRIES", "3"))
BACKOFF_FACTOR = float(os.getenv("ETL_BACKOFF_FACTOR", "2.0"))

# Geographic parameters: Bhubaneswar BMC Ward Bounds Bounding Box
# Format: [min_lon, min_lat, max_lon, max_lat] -> [85.732, 20.211, 85.904, 20.367]
BHUBANESWAR_BBOX = [85.732, 20.211, 85.904, 20.367]

# Default data settings
DEFAULT_WORLDPOP_YEAR = int(os.getenv("WORLDPOP_YEAR", "2020"))
DEFAULT_WEATHER_DAYS = int(os.getenv("WEATHER_BACKFILL_DAYS", "10"))
