.DEFAULT_GOAL := build

PYTHON=${PWD}/ve/bin/python3.4

system-virtualenv:
	dpkg -s python-virtualenv > /dev/null \
		|| sudo apt-get install python-virtualenv

ve/bin/python3.4:
	virtualenv --python=`which python3.4` ve

virtualenv: system-virtualenv ve/bin/python3.4

egg:
	${PYTHON} setup.py develop

build: system-virtualenv virtualenv egg

clean:
	rm -r ${PWD}/ve

.PHONY: build clean system-virtualenv virtualenv egg
