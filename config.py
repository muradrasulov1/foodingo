import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    HOST = os.getenv("HOST", "localhost")
    PORT = int(os.getenv("PORT", 8000))
    
    # AI Configuration
    AI_MODEL = "gpt-4"
    AI_TEMPERATURE = 0.7
    MAX_TOKENS = 500
    
    # Voice Configuration
    SPEECH_TIMEOUT = 5.0  # seconds
    PHRASE_TIMEOUT = 1.0  # seconds
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required")
        return True 