all: test package

package: version
	cp version aomi/version
	python setup.py sdist

test:
	cp version aomi/version
	test -d .ci-env || ( mkdir .ci-env && virtualenv .ci-env )
	.ci-env/bin/pip install -r requirements.txt -r requirements-dev.txt
	.ci-env/bin/pep8 aomi
	.ci-env/bin/nose2
	./scripts/integration

clean:
	rm -rf aomi.egg-info dist

distclean: clean
	rm -rf build .ci-env aomi/version .vault .bats

container:
	./scripts/container
