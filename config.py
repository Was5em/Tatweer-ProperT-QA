import os

class QAConfig:
    LOGO_FILE = "logo.png"
    PAGE_TITLE = "OS Precision Audit | Enterprise"
    PAGE_ICON = "logo.png"

    PRIMARY_COLOR = "#ed4224"
    SECONDARY_COLOR = "#0a192f"
    BG_COLOR = "#ffffff"
    CARD_BG = "#ffffff"
    TEXT_MAIN = "#0a192f"
    TEXT_LIGHT = "#546e7a"
    WHITE = "#ffffff"
    SUCCESS_COLOR = "#28a745"
    DANGER_COLOR = "#dc3545"

    PRICE_INPUT_1M = 0.075
    PRICE_OUTPUT_1M = 0.30
    MODEL_NAME = "models/gemini-2.5-flash"

    @classmethod
    def calculate_cost(cls, input_tokens: int, output_tokens: int) -> float:
        input_tokens = input_tokens or 0
        output_tokens = output_tokens or 0
        return (input_tokens * (cls.PRICE_INPUT_1M / 1_000_000)) + \
               (output_tokens * (cls.PRICE_OUTPUT_1M / 1_000_000))

    @staticmethod
    def _get_secret(key: str, default: str = "") -> str:
        """Retrieves config values from streamlit secrets or environment variables."""
        try:
            import streamlit as st
            val = st.secrets.get(key)
            if val is not None:
                return val
        except Exception:
            pass
        return os.environ.get(key, default)

    @classmethod
    def get_api_key(cls) -> str:
        return cls._get_secret("GOOGLE_API_KEY", "")

    @classmethod
    def get_database_url(cls) -> str:
        host = cls._get_secret("DB_HOST", cls._get_secret("POSTGRES_HOST", ""))
        port = cls._get_secret("DB_PORT", cls._get_secret("POSTGRES_PORT", "5432"))
        db_name = cls._get_secret("DB_NAME", cls._get_secret("POSTGRES_DB", ""))
        user = cls._get_secret("DB_USER", cls._get_secret("POSTGRES_USER", ""))
        password = cls._get_secret("DB_PASSWORD", cls._get_secret("POSTGRES_PASSWORD", ""))

        if host and db_name and user and password:
            return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

        url = cls._get_secret("DATABASE_URL", "")
        if url:
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url

        return "sqlite:///qa_database.db"

    @classmethod
    def get_s3_config(cls) -> dict:
        return {
            "access_key": cls._get_secret("AWS_ACCESS_KEY_ID", ""),
            "secret_key": cls._get_secret("AWS_SECRET_ACCESS_KEY", ""),
            "region": cls._get_secret("AWS_REGION", cls._get_secret("AWS_DEFAULT_REGION", "us-east-1")),
            "bucket": cls._get_secret("AWS_S3_BUCKET", ""),
            "endpoint_url": cls._get_secret("AWS_S3_ENDPOINT_URL", ""),
        }

    @classmethod
    def is_s3_enabled(cls) -> bool:
        cfg = cls.get_s3_config()
        return bool(cfg["access_key"] and cfg["secret_key"] and cfg["bucket"])

    @classmethod
    def get_admin_user(cls) -> str:
        return cls._get_secret("ADMIN_USERNAME", "admin")

    @classmethod
    def get_admin_pass(cls) -> str:
        return cls._get_secret("ADMIN_PASSWORD", "admin123")

    @classmethod
    def get_auditor_user(cls) -> str:
        return cls._get_secret("AUDITOR_USERNAME", "auditor1")

    @classmethod
    def get_auditor_pass(cls) -> str:
        return cls._get_secret("AUDITOR_PASSWORD", "user123")

    @classmethod
    def get_cookie_secret(cls) -> str:
        return cls._get_secret("COOKIE_SIGNING_SECRET", "super_secret_default_key_987654321")

    @classmethod
    def is_default_credentials(cls) -> bool:
        return (cls.get_admin_pass() == "admin123" or 
                cls.get_auditor_pass() == "user123" or 
                cls.get_cookie_secret() == "super_secret_default_key_987654321")
