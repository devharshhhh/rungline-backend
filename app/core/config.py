from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./rungline.db"

    judge0_api_url: str = "https://judge0-ce.p.rapidapi.com"
    judge0_api_key: str = ""
    judge0_api_host: str = "judge0-ce.p.rapidapi.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
