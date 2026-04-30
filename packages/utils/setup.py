from setuptools import setup, find_packages

setup(
    name="cloudvisor-utils",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "structlog>=24.1.0",
        "opentelemetry-api>=1.22.0",
        "opentelemetry-sdk>=1.22.0",
        "opentelemetry-exporter-otlp>=1.22.0",
        "opentelemetry-instrumentation-fastapi>=0.43b0",
    ],
)
