import os
from logging.config import dictConfig

from dynaconf import Dynaconf, Validator

dir_path = os.path.dirname(os.path.realpath(__file__))

# Configure Dynaconf
settings = Dynaconf(
    root_path=dir_path,
    environments=True,
    settings_files=[
        "settings.toml",
        f"{os.path.expanduser('~')}/clairvoyance.toml",
    ],
    ENVVAR_PREFIX_FOR_DYNACONF="CLAIRVOYANCE",
    ENVVAR_FOR_DYNACONF="CLAIRVOYANCE_SETTINGS",
)

# Register validators
settings.validators.register(
    # Ensure some parameters exists (are required)
    Validator(
        "ECR.registry_id", must_exist=True, messages=(dict(must_exist_true="Bla"))
    ),
    Validator("ECR.repositories", must_exist=True),
)


dictConfig(settings.LOGGING)
