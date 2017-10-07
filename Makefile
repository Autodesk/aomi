ifndef TRAVIS
ifndef VIRTUAL_ENV
CIENV = $(shell pwd)/.ci-env/bin/
endif
endif

all: test package

version:
	cp version aomi/version

package: version
	python setup.py sdist

testenv:
	test -z $(TRAVIS) && (test -d .ci-env || ( mkdir .ci-env && virtualenv .ci-env )) || true
	test -z $(TRAVIS) && \
		(echo "Non Travis" && .ci-env/bin/pip install -r requirements.txt -r requirements-dev.txt --upgrade) || \
		(echo "Travis" && pip install -r requirements.txt -r requirements-dev.txt)

test: version testenv
	$(CIENV)coverage erase
	$(CIENV)pep8 aomi
	$(CIENV)pylint --rcfile=/dev/null aomi
	COVERAGE_FILE="$(pwd)/.coverage" $(CIENV)nose2 -v -C --coverage aomi
	$(CIENV)bandit -r aomi
	$(CIENV)vulture aomi
	./scripts/integration
	$(CIENV)coverage report -m
	test -z $(TRAVIS) && coverage erase || true

clean:
	rm -rf aomi.egg-info dist .aomi-test tests/*.pyc aomi/*.pyc \
		aomi/model/*.pyc docs/_site tests/__pycache__ aomi/__pycache__ \
		aomi/model/__pycache__ docs/.saas-cache

distclean: clean
	rm -rf build .ci-env aomi/version .vault .bats .bats-git

container:
	./scripts/container

.PHONY: all version package test clean distclean container
