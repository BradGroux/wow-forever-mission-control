# Every target wraps one ./mc command, so `make X` and `./mc X` are interchangeable.
PY ?= python3
MC = $(PY) mc
PORT ?= 8000

.PHONY: help import init validate generate plan serve doctor test addon-test lint leakcheck check sync

help:            ## list targets
	@grep -E '^[a-z-]+:.*##' Makefile | sed 's/:.*##/\t/'

init:            ## setup interview -> config/roster.json
	$(MC) init

validate:        ## check the roster
	$(MC) validate --strict

generate:        ## rebuild the page data, PLAN.md and the Grok Bot canvas
	$(MC) generate

plan:            ## print your plan as Markdown
	$(MC) plan

serve:           ## open the page at http://localhost:$(PORT)
	$(MC) serve --port $(PORT)

import:          ## import addon data: make import SV="/path/to/LegacyTracker.lua"
	$(MC) import-addon "$(SV)"
	$(MC) generate

doctor:          ## CI checks
	$(MC) doctor

test:            ## unit tests
	$(PY) -m unittest discover -s tests -v

addon-test:      ## needs lua5.1 and luac5.1
	luac5.1 -p addon/LegacyTracker/LegacyTracker.lua
	lua5.1 addon/test/harness.lua addon/LegacyTracker/LegacyTracker.lua > /tmp/LegacyTracker.sv.lua
	diff -u addon/test/SavedVariables.sample.lua /tmp/LegacyTracker.sv.lua

leakcheck:       ## run before opening a pull request upstream
	$(MC) leakcheck

check: validate doctor test   ## everything CI runs except the addon

sync:            ## pull template updates from upstream (see docs/updating.md)
	git remote get-url upstream >/dev/null 2>&1 || git remote add upstream https://github.com/BradGroux/wow-forever-mission-control.git
	git fetch upstream
	git merge upstream/main --allow-unrelated-histories --no-edit
	$(MC) generate
