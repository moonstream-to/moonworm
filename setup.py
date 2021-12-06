from setuptools import find_packages, setup

from moonworm.version import MOONWORM_VERSION

long_description = ""
with open("README.md") as ifp:
    long_description = ifp.read()

setup(
    name="moonworm",
    version=MOONWORM_VERSION,
    packages=find_packages(),
    package_data={"moonworm": ["py.typed"]},
    install_requires=[
        "black",
        "inflection",
        "libcst",
        "moonstreamdb",
        "pysha3<2.0.0,>=1.0.0",
        "tqdm",
        "typing-extensions<4,>=3.7.4",
        "web3[tester]",
    ],
    extras_require={
        "dev": [
            "isort",
            "mypy",
            "wheel",
        ],
        "distribute": ["setuptools", "twine", "wheel"],
    },
    description="moonworm: Generate a command line interface to any Ethereum smart contract",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Moonstream",
    author_email="engineering@moonstream.to",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python",
        "License :: OSI Approved :: Apache Software License",
        "Topic :: Software Development :: Libraries",
    ],
    python_requires=">=3.6",
    url="https://github.com/bugout-dev/moonworm/",
    entry_points={"console_scripts": ["moonworm=moonworm.cli:main"]},
    include_package_data=True,
)
