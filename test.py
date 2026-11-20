from src.config import get_settings


settings = get_settings()


# ADAPTATION: the reference test.py prints the raw OpenAI API key.
# Never print secrets - show only whether the key is configured.
print("OpenAI API Key:", "configured" if settings.openai_api_key else "not set")
print("OpenAI Model:", settings.openai_model)
print("Offline mode:", settings.offline_mode)
