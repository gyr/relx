"""
This module contains the factory for creating provider instances.
"""

from typing import Dict, Any

from .base import ArtifactProvider
from .obs import OBSArtifactProvider


def get_artifact_provider(
    provider_name: str, api_url: str, config: Dict[str, Any]
) -> ArtifactProvider:
    """
    Factory function to get an ArtifactProvider instance.

    :param provider_name: The name of the provider (e.g., "obs").
    :param api_url: The API URL for the provider (e.g., OBS instance URL).
    :param config: The global configuration dictionary.
    :return: An instance of an ArtifactProvider.
    :raises ValueError: If an unknown provider name is given.
    """
    if provider_name == "obs":
        artifacts_config = config.get("artifacts", {})
        return OBSArtifactProvider(
            api_url=api_url,
            invalid_start=artifacts_config.get("invalid_start", []),
            invalid_extensions=artifacts_config.get("invalid_extensions", []),
        )
    # Add other providers here in the future
    else:
        raise ValueError(f"Unknown artifact provider: {provider_name}")
