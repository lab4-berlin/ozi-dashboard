from setuptools import find_packages, setup

setup(
    name="dagster_etl",
    packages=find_packages(exclude=["dagster_etl_tests"]),
    install_requires=[
        "dagster",
        "dagster-cloud"
    ],
    extras_require={"dev": ["dagster-webserver", "pytest"]},
)
