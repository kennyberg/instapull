from .base import VisionProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider

_REGISTRY = {
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
}

PROVIDER_NAMES = sorted(_REGISTRY.keys())


def get_provider(name: str) -> VisionProvider:
    """Return a ready-to-use vision provider loaded from environment variables."""
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown provider '{name}'. Available options: {', '.join(PROVIDER_NAMES)}"
        )
    return _REGISTRY[name].from_env()
