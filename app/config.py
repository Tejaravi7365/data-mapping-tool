from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    Application-level configuration.

    For this MVP most connection details are passed in the request body,
    but this class allows future environment-based configuration
    (e.g. default Redshift cluster, logging settings, etc.).
    """

    app_name: str = "Data Mapping Sheet Generator"

    class Config:
        env_file = ".env"


settings = Settings()

