# Library folder

This folder contains Python libraries on which GeoCat Bridge depends, and for which a specific version is required.  

Python package sources are copied into this folder using the `/scripts/update_libs.py` script.  

To update the libraries, run the following command:

```
python scripts/update_libs.py
```

This script will clone the required Python libraries from Git and copy them to the `/geocatbridge/libs/` directory.  
For details, check the script itself (e.g. Git URLs, source directories, tag names, etc.).

Both the `libs/` and `dependencies/` directories are ignored by Git (`.gitignore`) for the top level project.
