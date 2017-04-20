PYTHON=./env/bin/python3
SRC=analytics/

.PHONY: lint tags

lint:
	${PYTHON} -m pylint ${SRC} 	&& \
	${PYTHON} -m pycodestyle ${SRC} && \
	${PYTHON} -m pydocstyle ${SRC}

tags:
	ctags -R --python-kinds=-i .

