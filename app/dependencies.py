from app.config import Settings
from app.core.bp_client import BackpackTFClient
from app.core.scanner import Scanner


settings = Settings()
bp = BackpackTFClient(settings.bp_api_key, settings.bp_token)
scanner = Scanner(bp)
