# allow overriding the name of the venv directory
VENV_DIR ?= venv

.PHONY: ${VENV_DIR}/ venv clean

# set up the venv with all dependencies for development
${VENV_DIR}/: requirements.txt
	python3 -m venv ${VENV_DIR}
	. ${VENV_DIR}/bin/activate
	python3 -m pip --require-virtualenv install -r requirements.txt

# make sure `make venv` always works no matter what $VENV_DIR is
venv: ${VENV_DIR}/

gus:
	git clone git@gitlab.inria.fr:CORSE/gus.git
	cd gus
	git submodule init
	git submodule update --depth 1

docker: gus
	docker build .
	
deps:
	python3 -m pip install -r requirements.txt --break-system-packages

binaries:
	mkdir -p __build__
	mkdir -p polyhedral
	./shifumi.py --include polybench/utilities/ --compilers-conf=config/cc-docker.list --sources-conf='config/benchmarks-docker.list' --versions-conf='config/versions-docker.list' --always-link-with 'polybench/utilities/polybench.c' --build-directory=__build__ --linker-options '-lm -Lgem5_deps -lm5 -Lperfpipedream/build-static -lpapi' --fuzz-directory polyhedral --reports-directory polyhedral --use-cache

docker-build-binaries-arm:
	mkdir -p __build__
	./shifumi.py --include polybench/utilities/ --compilers-conf=config/cc-docker.list --sources-conf='config/benchmarks-docker.list' --versions-conf='config/versions-docker.list' --always-link-with 'polybench/utilities/polybench.c' --build-directory=__build__ --linker-options '-lm -Lperfpipedream/build-arm-ok -lperf-pipedream'

clean:
	rm -rf ${VENV_DIR}