from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    openai_api_key: str
    deepgram_api_key: str
    allowed_origins: str = "http://localhost:3000"
    livekit_sip_trunk_id: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def sip_enabled(self) -> bool:
        return bool(self.livekit_sip_trunk_id)


settings = Settings()
