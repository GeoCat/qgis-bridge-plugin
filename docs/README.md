# Building HTML documentation for GeoCat Bridge

This `docs` folder is a standalone [MkDocs](https://www.mkdocs.org) project, using the
[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme. The documentation pages
themselves live as Markdown files under [`docs/`](docs), the theme customizations under
[`overrides/`](overrides), and the build is configured in [`mkdocs.yml`](mkdocs.yml).

All commands below are run from *this* `docs` folder (not the repository root).

## Setup

Set up a Python virtual environment once:

```
python3 -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate
```

Then install the build dependencies into it:

```
pip install -r requirements.txt
```

Activate the `venv` (see above) again whenever you come back to work on the docs in a new terminal session.

While editing, preview the docs locally with live-reload:

```
mkdocs serve
```

The easiest way to build the HTML documentation for GeoCat Bridge, is by running the Python script ```builddocs.py```.
This script wraps `mkdocs build` and also knows how to build documentation for older, tagged releases of the plugin
(published side-by-side on GitHub Pages, e.g. `v4.5`, `v4.6`, ...).

Please run ```python builddocs.py -h``` to get a description of all available parameters.


## Common usage examples

### Build latest version (HEAD)

```python builddocs.py``` 

or 

```python builddocs.py --version latest```

If ```--version``` is omitted, the latest state will be built of the current branch or a specific branch
if the ```--branch``` parameter is set.
Note that the current branch may still have uncommitted edits (no checkout will be performed in that case).

### Build last available stable version

```python builddocs.py --version stable```

Finds the latest stable Git tag, performs a checkout for it and builds the docs.
Note that if the current branch has uncommitted edits, the script will not build any docs in this case.

### Build all stable versions and HEAD

```python builddocs.py --version all```

Note that if the current branch has uncommitted edits, the script will not perform any checkout
and only build the current state of the docs but not of the stable tags. In that case, setting ```--version all```
will have the same effect as omitting ```--version``` or setting it to ```--version latest```.

### Build latest version (HEAD) on branch "my-branch"

```python builddocs.py --branch my-branch```
