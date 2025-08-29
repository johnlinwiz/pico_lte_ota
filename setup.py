import os
import re
import sys

sys.path.pop(0)
from setuptools import setup

sys.path.append("./sdist_upip")
import sdist_upip

version_reference = os.getenv("GITHUB_REF", default="0.1.0")
release_version_search = re.search(r"(\d+.\d+.\d+)", version_reference)
if release_version_search:
    release_version = release_version_search.group()
    print(f"Version: {release_version}")
else:
    raise ValueError("Version was not found")

setup(
    name="pico_lte_ota",
    version=release_version,
    description="Micropython library for upgrading code over-the-air (OTA) - Sixfab Pico LTE version",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=[""],
    project_urls={"Source": "https://github.com/johnlinwiz/pico_lte_ota"},
    author="John Lin",
    author_email="johnlinwiz@gmail.com",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords=["OTA", "Microcontroller", "Micropython"],
    cmdclass={"sdist": sdist_upip.sdist},
)
