from typing import Any


class ProviderManager:
    def __init__(self, providers: dict[str, Any], default_provider: str = "simulated") -> None:
        self.providers = providers
        self.default_provider = default_provider

    def generate_reply(self, message: str, provider_name: str | None = None) -> Any:
        selected_name = provider_name or self.default_provider
        provider = self.providers.get(selected_name)
        if provider is None:
            raise ValueError(f"Unknown provider: {selected_name}")
        return provider.generate_reply(message)
