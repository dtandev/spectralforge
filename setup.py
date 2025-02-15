# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

setup(
    name="spectralforge",
    version="0.0.1",
    description="tbd",  # noqa
    long_description=open("README.md").read(),  # opis do PyPI, np. z pliku README.md
    long_description_content_type="text/markdown",
    author="Dariusz Tanajewski",  #
    author_email="dariusz.tanajewski@terraeye.co",
    url="https://github.com/dtandev/spectralforge",
    packages=find_packages(),  # automatyczne wykrywanie podpakietów
    install_requires=[  # lista zależności
        "geopandas>=0.14.3",
        "numpy>=1.26.4",
        "psycopg2-binary>=2.9.10",
        "matplotlib>=3.8.4",
        "rasterio>=1.3.9",
        "beautifulsoup4>=4.12.3",
        "rasterio>=1.3.9",
        "shapely>=2.0.4",
        "json5>=0.9.25",
        "scipy>=1.13.0",
    ],
    classifiers=[  # klasyfikatory, np. licencja, wersje Pythona
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: GNU License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",  # minimalna wersja Pythona
)
