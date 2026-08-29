from pydantic import BaseSettings


class AppSettings(BaseSettings):
    app_name: str = "uplift-demo"
    tax_rate: float = 0.08
    currency: str = "USD"

    class Config:
        env_prefix = "UPLIFT_"
