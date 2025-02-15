### Git-Hooks

This project uses `pre-commit` package for managing and maintaining pre-commit hooks.

To ensure code quality - please make sure that you have it configured.

1. Install `pre-commit` and following packages: `isort`, `black`, `flake8`, `mypy`, `pytest`. You can do so by updating
   your current environment. Activate your environment and then run: `conda env update -f ./pangeo_env.yml`
2. Install pre-commit hooks by running: `pre-commit install`
3. The command above will automatically run formatters, code checks and other steps defined in
   the `.pre-commit-config.yaml`
4. All of those checks will also be run whenever a new commit is being created i.e. when you run `git commit -m "blah"`
5. You can also run it manually with this command: `pre-commit run --all-files`
6. **IMPORTANT!** You can manually disable pre-commit hooks by running: `pre-commit uninstall`
   Use this only in exceptional cases.

In order to run hook commands without the need to actually have pre-commit hooks configured you can run:

```shell
isort .;black .;flake8 .;mypy ./v2;pytest -m "unit" -v
```

## Project Overview

SpectralHub is a Python library for processing and analyzing spectral data. The project provides tools for handling various types of spectral measurements and performing common analysis tasks.
