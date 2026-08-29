# BC-001
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    app_name: str = "uplift-demo"
    tax_rate: float = 0.08
    currency: str = "USD"

    # BC-001, BC-003
    model_config = SettingsConfigDict(env_prefix="UPLIFT_")
