import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    PROJECT_NAME: str = "AgentCart - Agentic Commerce with Razorpay"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Razorpay Test Credentials (can be configured via .env or frontend)
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_mock_key123")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "mock_secret_456")
    RAZORPAY_MOCK_MODE: bool = os.getenv("RAZORPAY_MOCK_MODE", "true").lower() == "true"
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    
    # Gemini / LLM API Key (optional - built-in autonomous heuristic engine fallback provided)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Financial Guardrails Default Limits (in INR)
    DEFAULT_MAX_TRANSACTION_LIMIT: float = 10000.0  # Hard ceiling
    DEFAULT_AUTO_APPROVE_LIMIT: float = 3000.0      # Auto-approve threshold (UAP style)

    # CORS Origins (Comma-separated string or list)
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

settings = Settings()
