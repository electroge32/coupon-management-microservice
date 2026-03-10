from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str
    wc_base_url: str
    wc_consumer_key: str
    wc_consumer_secret: str
    max_fixed_discount: int = 500000
    database_url: str = "sqlite:///./coupons.db"

    model_config = {"env_file": ".env"}


settings = Settings()
