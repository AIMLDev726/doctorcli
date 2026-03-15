class DoctorCliError(Exception):
    """Base application error."""


class ConfigurationError(DoctorCliError):
    """Raised when required configuration is missing or invalid."""


class ProviderError(DoctorCliError):
    """Raised when a provider request fails."""


class StorageError(DoctorCliError):
    """Raised when local persistence fails."""
