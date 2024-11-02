# eCactus ecos client

Client to communicate with the API behind eCactus Ecos.

## Installation

    pip install ecactus-ecos-client

## Usage

See the [example](examples/example.py) on how to use this library.

## Development

This project uses [pipenv](https://pypi.org/project/pipenv/) for dependency and environment management.
When not installed run `pip install --user pipenv` to install it

Install dependencies using

    pipenv install --dev

Using the env

    pipenv shell

## Testing

Run a simple example test

    python3 examples/example.py <username> <password>

## Packaging

Create a package using

    python3 setup.py sdist bdist_wheel

This creates a package in `dist`

Upload the package using

    python3 -m twine upload dist/*
