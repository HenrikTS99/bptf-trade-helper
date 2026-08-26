from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bp_api_key: str
    bp_token: str
    steam_id: str

    model_config = SettingsConfigDict(env_file=".env")
