from setuptools import find_packages, setup

long_description = ""
with open("README.md") as ifp:
    long_description = ifp.read()

setup(
    name="centipede",
    version="0.0.1",
    packages=find_packages(),
    package_data={"centipede": ["py.typed"]},
    install_requires=["web3", "eth-tester"],
    extras_require={
        "dev": [
            "black",
            "mypy",
            "wheel",
        ],
        "distribute": ["setuptools", "twine", "wheel"],
    },
    description="testnet: Write Python tests for your Ethereum code using testnet.bash.",
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
    url="https://github.com/bugout-dev/testnet.bash",
)
