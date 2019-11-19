# Bridge Command Line Interface (CLI)

Bridge CLI is currently only available for ArcMAP. In QGIS, bridge can be used as a module in QGIS Processing modeler.

The GeoCat Bridge Command Line Interface (CLI) allows GeoCat Bridge
users to automate the publishing process, by setting up scheduled tasks
to publish ArcGIS map documents to a map server and publish the
associated metadata to a catalog server. In combination with scheduled
tasks Bridge can ensure that the data and metadata on the server is kept
up to date.

Supported servers for the Bridge CLI are:

-   MapServer
-   GeoServer
-   GeoNetwork
-   CSW (Catalog Server for the Web) servers

For supported versions see [Server requirements](2_background_and_requirements.html#server-requirements).

The GeoCat CLI executable \"bridge.exe\" can be found in the
installation directory of GeoCat Bridge. Typically in
`C:\Program Files (x86)\GeoCat\Bridge 3` (on 64 bits systems) or
`C:\Program Files\GeoCat\Bridge 3` (on 32 bits systems).

A Bridge Premium license is required for the Bridge CLI.

## Input

The Bridge CLI takes either an ESRI layer (.lyr) or an ESRI map document
(.mxd) as input. The layers in the input file will be published to the
selected map server.

When publishing to GeoServer and using Bridge in the [Managed
Workspace](7_server_configuration.html#managed-workspace) mode or when publishing to MapServer, Bridge will name the
GeoServer workspace or MapServer mapfile like this:

| Input                               | Workspace or Mapfile name                 |
| ----------------------------------- | ----------------------------------------- |
| Layer file                          | Filename of lyr file (without extension)  |
| MXD                                 | Filename of mxd file (without extension)  |

By default when publishing to GeoServer Bridge will publish the layers
in the selected workspace of the selected GeoServer configuration.

## Logging

The Bridge CLI logs its output to a separate log file which can be found
in the local data directory of the current user:
`C:\Users\<USER>\AppData\Local\GeoCat\Bridge 3\Bridge-cli_<DATE>.log`.
Log files older than 7 days are automatically removed from the system.

The log level can be changed by editing the NLog-CLI.config file in the
Bridge installation directory. Change the minlevel value of the
following line to change the log level:

``` bash
allowed values= Debug, Info, Warning, Error
<logger name="*" minlevel="Error" writeTo="file" />
```

## Exit-code

On successful completion the Bridge CLI exits with code 0. On failure
the Bridge CLI exits with code 1.

## Usage

You can either add the Bridge installation directory to your path or
execute the CLI from the Bridge installation directory. Call
`bridge help` from the Bridge installation directory to display help
content on the Bridge CLI. This will list the available commands:

``` bash
GeoCat Bridge CLI 3.0.0.0
Copyright c GeoCat 2010-2018

  remove     Remove the layer(s) from your server(s)

  publish    Publish your mxd or lyr file to a map server and/or catalog server

  export     Export data, symbology and metadata of layers locally

  list       List servers and layers from mxd or lyr file

To view help for the different actions run 'help list', 'help publish', 'help
remove' or 'help export'  
```

### List command

Call `bridge help list` to show the help contents for the list command:

``` bash
GeoCat Bridge CLI 3.0.0.0
Copyright c GeoCat 2010-2018

  -f, --file              [string] Path to mxd or lyr file to list layers

  -d, --dataservers       [flag] List dataservers to publish to

  -s, --server            [string] Identifier of server to list details

  -c, --catalogservers    [flag] List catalogservers to publish to

  -j, --json              [flag] Output JSON formatted messages

  -z, --localappdata      [string] Override localappdata folder location
```

#### Examples

List the available dataservers by calling either:

``` bash
bridge list -d
bridge list --dataservers
```

List the available catalogservers by calling either:

``` bash
bridge list -c
bridge list --catalogservers
```

List the layers available for publishing in an mxd or lyr file by
calling either:

``` bash
bridge list -l C:\path\to\mxd\file.mxd 
bridge list --layers C:\path\to\mxd\file.mxd
```

### Publish command

Call `bridge help publish` to show the help contents for the publish
command:

``` bash
GeoCat Bridge CLI 3.0.0.0
Copyright c GeoCat 2010-2018

  -f, --file             Required. [string] Path to mxd or lyr file to publish

  -d, --dataserver       [string] ID of dataserver to publish to

  -c, --catalogserver    [string] ID of catalogserver to publish to

  -l, --layers           [string] Specify layers to publish, separated by a
                         colon

  -m, --modes            [string] Specify what to publish, available values are
                         data and symbology. By default data and symbology are
                         published when a dataserver is specified

  -a, --all              [flag] Publish all layers, in case layers are turned
                         off in map document. In ManagedWorkspace mode all
                         layers are published by default

  -v, --verbose          [flag] Verbose mode, output logging to console

  -o, --logfile          [string] Path to optional log file, when specified
                         Bridge logs to default log file and the optional log
                         file

  -j, --json             [flag] Output JSON formatted messages

  -z, --localappdata     [string] Override localappdata folder location
```

#### Examples

Publish an mxd to server with ID `MS_1`:

``` bash
bridge publish -f C:\path\to\mxd\file.mxd -d MS_1
```

Publish an mxd to server with ID `MS_1`, but only layers roads and
sites:

``` bash
bridge publish -f C:\path\to\mxd\file.mxd -d MS_1 -l roads:sites
```

Publish an mxd to server with ID `MS_1`, but only publish data (no
symbology):

``` bash
bridge publish -f C:\path\to\mxd\file.mxd -d MS_1 -m data
```

Publish an mxd to server with ID `MS_1` but only layers roads and sites:

``` bash
bridge publish -f C:\path\to\mxd\file.mxd -d MS_1 -l roads:sites
```

Publish an mxd to server with ID `MS_1` and output log to command
prompt:

``` bash
bridge publish -f C:\path\to\mxd\file.mxd -d MS_1 -v
```

Publish an mxd to server with ID \"GS\_1\" and output log to another log
file:

``` bash
bridge publish -f C:\path\to\mxd\file.mxd -d GS_1 -o C:\path\to\logfile.log
```

### Remove command

Call `bridge help remove` to show the help contents for the publish
command:

``` bash
GeoCat Bridge CLI 3.0.0.0
Copyright c GeoCat 2010-2018

  -f, --file             Required. [string] Path to mxd or lyr file to remove

  -d, --dataserver       [string] ID of dataserver to remove layers from

  -c, --catalogserver    [string] ID of catalogserver to remove metadata from

  -o, --logfile          [string] Path to optional log file, when specified
                         Bridge logs to default log file and the optional log
                         file

  -v, --verbose          [flag] Verbose mode, output logging to console

  -j, --json             [flag] Output JSON formatted messages

  -z, --localappdata     [string] Override localappdata folder location
```

#### Examples

Remove the layers of an mxd from a dataserver with ID \"MS\_1\":

``` bash
bridge remove -f C:\path\to\mxd\file.mxd -d MS_1      
```

Remove the layers of an mxd from a dataserver with ID \"GS\_1\" and from
a catalogserver with ID \"GN\_1\"

``` bash
bridge remove -f C:\path\to\mxd\file.mxd -d GS_1 -c GN_1
```

Remove the layers of an mxd from a dataserver with ID \"MS\_1\" and
output log to another log file:

``` bash
bridge remove -f C:\path\to\mxd\file.mxd -d MS_1 -o C:\path\to\logfile.log
```

### Export command

Call `bridge help export` to show the help contents for the export
command:

``` bash
GeoCat Bridge CLI 3.0.0.0
Copyright c GeoCat 2010-2018

  -t, --target      Required. [string] Folder destination (target) to store
                    exported files

  -m, --metadata    [string] Export metadata, indicate what profile to use:
                    default, inspire, dutch

  -s, --sld         [string] Export SLD, indicate what SLD version to use: 1.0
                    (sld_1.0), 1.0 GS Vendor Extension (sld_1.0_GS), 1.1
                    (sld_1.1)

  -d, --data        [string] Export data, indicate what data format to use:
                    shapefile, geopackage, geopackage_map

  -f, --file        Required. [string] Path to mxd or lyr file to publish
```

Example usage, exporting metadata with default profile, symbology with
SLD version 1.0 with GeoServer vendor extensions and data with
GeoPackage format:

``` bash
bridge export -f C:\path\to\mxd\file.mxd -t C:\export -m default -s sld_1.0_GS -d geopackage
```
