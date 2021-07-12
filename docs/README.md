# Building HTML documentation for GeoCat Bridge

The easiest way to build the HTML documentation for GeoCat Bridge, is by running the Python script ```builddocs.py```.

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
