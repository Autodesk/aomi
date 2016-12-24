all: test package

version:
	cp version aomi/version

package: version
	python setup.py sdist

testenv:
	test -z $(TRAVIS) && (test -d .ci-env || ( mkdir .ci-env && virtualenv .ci-env ))
	.ci-env/bin/pip install -r requirements.txt -r requirements-dev.txt

test: version testenv
	.ci-env/bin/pep8 aomi
	.ci-env/bin/pylint --rcfile=/dev/null aomi
	.ci-env/bin/nose2
	./scripts/integration

clean:
	rm -rf aomi.egg-info dist .aomi-test tests/*.pyc aomi/*.pyc

distclean: clean
	rm -rf build .ci-env aomi/version .vault .bats .bats-git

container:
	./scripts/container

.PHONY: all version package test clean distclean container
