.DEFAULT_GOAL := build

PYTHON=${PWD}/ve/bin/python3

system-virtualenv:
	dpkg -s python-virtualenv > /dev/null \
		|| sudo apt-get install python-virtualenv

ve/bin/python3:
	virtualenv --python=`which python3` ve

virtualenv: system-virtualenv ve/bin/python3

egg:
	${PYTHON} setup.py develop

build: system-virtualenv virtualenv egg

clean:
	rm -rf ${PWD}/ve ${PWD}/build ${PWD}/dist

.PHONY: build clean system-virtualenv virtualenv egg
