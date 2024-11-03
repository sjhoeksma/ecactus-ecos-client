import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ecactus-ecos-client",
    version="0.1.4",
    author="S.J.Hoeksma",
    author_email="",
    description="Client for Ecactus ECOS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sjhoeksma/ecactus-ecos-client",
    packages=setuptools.find_packages(),
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Home Automation",
    ],
    python_requires=">=3.10",
)
