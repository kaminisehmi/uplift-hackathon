from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    app_name: str = "uplift-demo"
    tax_rate: float = 0.08
    currency: str = "USD"

    model_config = SettingsConfigDict(env_prefix="UPLIFT_")
