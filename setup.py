#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from typing import List

# Setup requirements

try:
    from setuptools import find_packages, setup
except ImportError:
    print(
        "setuptools is needed in order to build. Install it using your package manager (usually python-setuptools) or via pip (pip install setuptools)."
    )
    sys.exit(1)


def parse_requirements(filename: str) -> List[str]:
    """load requirements from a pip requirements file"""
    lineiter = (line.strip() for line in open(filename))
    return [str(line) for line in lineiter if line and not line.startswith("#")]


# Extra requirements installable using pip -e '.[<extra>]'
EXTRAS_REQUIRE = {
    "tests": [
        "tox",
        "black>=23.1.0,<24",
        "click==8.1.3",
        "coverage-badge==1.0.1",
        "coverage==7.1.0",
        "flake8",
        "isort",
        "moto<5.0",
        "pytest-cov>=4.0.0",
        "pytest-datafiles>=2.0.1",
        "pytest-env>=0.8.1",
        "pytest-logger>=0.5.1",
        "pytest-datafiles<=2.0.1",
        "pytest-mock>=3.10.0",
        "pytest-runner>=6.0.0",
        "pytest-xdist>=3.1.0",
        "pytest-lazy-fixture>=0.6.3,<0.7",
        "pytest-sugar>=0.9.4",
        "pytest>=7.2.1,<8",
    ],
}


setup(
    name="voyance",
    version="1.0.1",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    entry_points={
        "console_scripts": ["voyance=clairvoyance.voyance:cli"],
    },
    install_requires=parse_requirements("requirements.txt"),
    package_dir={"": "."},
    packages=find_packages(),
    package_data={"": ["*.toml"]},
    extras_require=EXTRAS_REQUIRE,
)
