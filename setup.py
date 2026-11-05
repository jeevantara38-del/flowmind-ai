from setuptools import setup, find_packages

setup(
    name="flowmind",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "flowmind=flowmind.cli.main:main",
        ],
    },
)
