"""
This module contains the factory for creating provider instances.
"""

from typing import Dict, Any

from .base import ArtifactProvider, UserProvider, PackageProvider
from .obs_artifact import OBSArtifactProvider
from .obs_user import OBSUserProvider
from .obs_package import OBSPackageProvider


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


def get_user_provider(provider_name: str, api_url: str) -> UserProvider:
    """
    Factory function to get a UserProvider instance.

    :param provider_name: The name of the provider (e.g., "obs").
    :param api_url: The API URL for the provider (e.g., OBS instance URL).
    :return: An instance of a UserProvider.
    :raises ValueError: If an unknown provider name is given.
    """
    if provider_name == "obs":
        return OBSUserProvider(
            api_url=api_url,
        )
    # Add other providers here in the future
    else:
        raise ValueError(f"Unknown user provider: {provider_name}")


def get_package_provider(provider_name: str, api_url: str) -> PackageProvider:
    """
    Factory function to get a PackageProvider instance.

    :param provider_name: The name of the provider (e.g., "obs").
    :param api_url: The API URL for the provider (e.g., OBS instance URL).
    :return: An instance of a PackageProvider.
    :raises ValueError: If an unknown provider name is given.
    """
    if provider_name == "obs":
        return OBSPackageProvider(
            api_url=api_url,
        )
    # Add other providers here in the future
    else:
        raise ValueError(f"Unknown package provider: {provider_name}")
