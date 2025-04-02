from setuptools import setup, find_packages

setup(
    name="llm-router-api",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "python-dotenv",
        "neo4j",
        "google-generativeai",
        "mistralai",
        "openai",
        "rich",
        "loguru",
        "python-json-logger",
        "tenacity",
        "requests"
    ],
) 