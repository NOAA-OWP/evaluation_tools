#!/usr/bin/env python3
import subprocess
import sys
from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install

from pathlib import Path

# python root namespace package
# this namespace package follows PEP420
# https://packaging.python.org/guides/packaging-namespace-packages/#native-namespace-packages

# This namespace package structure and configuration follows a pattern
# presented here:
# https://medium.com/@jherreras/python-microlibs-5be9461ad979

NAMESPACE_PACKAGE_NAME = "evaluation_tools"

# Package author information
AUTHOR = "Jason Regina"
AUTHOR_EMAIL = "jarq6c@gmail.com"

# Namespace package version
VERSION = "1.0.0"
URL = "https://github.com/NOAA-OWP/evaluation_tools"

# Map subpackage namespace to relative location
# key: Subpackage slug, value: subpackage relative location
SUBPACKAGES = {
    "evaluation_tools.nwis_client": "python/nwis_client",
    "evaluation_tools._restclient": "python/_restclient",
    "evaluation_tools.gcp_client": "python/gcp_client",
}

# Short sub-package description
DESCRIPTION = (
    "Suite of tools for retrieving USGS NWIS observations and evaluating "
    "National Water Model (NWM) data."
)

# Read information from relevant package files
LONG_DESCRIPTION = Path("README.md").read_text()
LICENSE = Path("LICENSE").read_text()

# Package dependency requirements
REQUIREMENTS = []

# Development requirements
DEVELOPMENT_REQUIREMENTS = ["pytest"]


def install_subpackages(sources: dict, develop_flag: bool = False) -> None:
    """Install all subpackages in a namespace package

    Parameters
    ----------
    sources : dict
        key: subpackage slug, value: subpackage relative location
    develop_flag : bool, optional
        Install in normal or development mode, by default normal
    """
    # absolute path
    ROOT_DIR = Path(".").resolve()
    for k, v in sources.items():
        try:
            subpackage_dir = str(ROOT_DIR / v)
            if develop_flag:
                subprocess.check_call(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "-e",
                        subpackage_dir,
                    ]
                )
            else:
                subprocess.check_call(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        subpackage_dir,
                    ]
                )
        except Exception as e:
            print("An error occurred when installing {k}")
            raise


# Normal installation
class Install(install):
    def run(self):
        install_subpackages(SUBPACKAGES, develop_flag=False)
        super().run()


# Development installation
class Develop(develop):
    def run(self):
        install_subpackages(SUBPACKAGES, develop_flag=True)
        # Install development requirements
        for dev_requirement in DEVELOPMENT_REQUIREMENTS:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", dev_requirement]
            )


setup(
    name=NAMESPACE_PACKAGE_NAME,
    version=VERSION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    classifiers=[
        "Private :: Do Not Upload to pypi server",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url=URL,
    license=LICENSE,
    install_requires=REQUIREMENTS,
    extras_require={"test": DEVELOPMENT_REQUIREMENTS},
    python_requires=">=3.7",
    cmdclass={"install": Install, "develop": Develop},
)
