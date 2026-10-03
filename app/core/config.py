from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./rungline.db"

    judge0_api_url: str = "http://localhost:2358"
    judge0_auth_token: str = ""

    judge0_rapidapi_key: str = ""
    judge0_rapidapi_host: str = "judge0-ce.p.rapidapi.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()