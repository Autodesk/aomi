[![Build Status](https://travis-ci.org/Autodesk/aomi.svg?branch=master)](https://travis-ci.org/Autodesk/aomi)[![PyPI](https://img.shields.io/pypi/v/aomi.svg)](https://pypi.python.org/pypi/aomi)[![Maintenance](https://img.shields.io/maintenance/yes/2017.svg)]()

# Aomi: Opinionlessly Express Opinions on Vault

If you are new to `aomi`, please checkout our [documentation](https://autodesk.github.io/aomi). You may be particularly interested in the [quickstart](https://autodesk.github.io/aomi/quickstart) guide.

# Contributing

All manner of contributions are welcome. The aomi tool is still relatively young, and emphasis has been placed on the data model concept more than staying current with the Vault API. We are looking for contributors of source code, documentation, and community support.

## Code

The aomi project is entirely Python, with some shell scripts binding the tests together. The structure is pretty standard for Python projects. Everything lives in one module [namespace](https://github.com/Autodesk/aomi/tree/master/aomi) and is loosely grouped into modules by context. Minimal PyDoc is required (and enforced by pylint) on each function.

When adding new [builtin](https://github.com/Autodesk/aomi/tree/master/aomi/templates) templates, a accompanying help file must be provided. This is a YAML file with a `name` and `help` element and it will feed the command line help for templates.

## Test

This project features the following tests (all are invoked with `make test`).

* Validation against the [pep8](https://www.python.org/dev/peps/pep-0008/) spec
* [pylint](https://www.pylint.org/) with default options
* Some unit [tests](https://github.com/Autodesk/aomi/tree/master/tests) powered by [nose2](http://nose2.readthedocs.io/en/latest/getting_started.html)
* Static security analysis with [bandit](https://pypi.python.org/pypi/bandit/1.0.1)
* Some integration [tests](https://github.com/Autodesk/aomi/tree/master/tests/integration) powered by [bats](https://github.com/sstephenson/bats).
* Checking for unused code paths with [vulture](https://pypi.python.org/pypi/vulture)

## Documentation

The README is focused on contribution guidelines. Operational docs are available on a static GitHub [page](https://autodesk.github.io/aomi/). These docs are maintained as [markdown](https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet) formatted documents within the [docs](https://github.com/Autodesk/aomi/tree/master/docs) directory. The static site is updated automatically based on the contents of this directory.

## Deployment

New docker containers are generated on merge to the `master` branch. New Python packages are pushed on every tagged commit, which happens during a [semantic version](http://semver.org/) bump. I tend to use the [avakas](https://github.com/otakup0pe/avakas) to handle version changes.

## Guidelines

* This project operates under a [Code of Conduct](https://autodesk.github.io/aomi/code_of_conduct).
* Changes are welcome via pull request!
* Please use informative commit messages and pull request descriptions.
* Please remember to update the documentation if needed.
* Please keep style consistent. This means PEP8 and pylint compliance at a minimum.
* Please add both unit and integration tests.

If you have any questions, please feel free to contact <jonathan.freedman@autodesk.com>.

# Errata

The [web page](https://autodesk.github.io/aomi) for `aomi` is based on the [hacker](https://github.com/pages-themes/hacker) Jekyll theme and has been heavily customized.

The Code of Conduct is version 1.4 of the [Contributor Covenant](http://contributor-covenant.org/).
