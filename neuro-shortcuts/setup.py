from setuptools import find_packages, setup


setup(
    name="neuro-shortcuts",
    version="0.0.1b1",
    packages=find_packages(),
    python_requires=">=3.7.0",
    install_requires=(),
    # TODO: console_scripts for running from python console
    scripts=["neu.py"],
)