from setuptools import find_packages, setup

setup(
    name="fuzze",
    packages=find_packages(),
    version="0.1.0",
    description="Fuzze library",
    author="Gabriel Benoit",
    install_requires=[
        "antlr4-python3-runtime==4.9.3",
        "antlr4-tools",
        "json5",
        "jsbeautifier",
        "websocket-client",
        "simple_parsing",
    ],
)
