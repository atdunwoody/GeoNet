import os
import subprocess
import sys

# define GRASS data settings (adapt to your needs)
gisdb = r"C:\Users\adunw\Documents\grassdata"
location = "geonet"
mapset = "PERMANENT"
executable = r"C:\OSGeo4W\bin\grass83.bat"

grass_cmd = [executable, "--config", "python_path"]
process = subprocess.run(grass_cmd, check=True, text=True, stdout=subprocess.PIPE)

# define GRASS-Python environment
sys.path.append(process.stdout.strip())

# import (some) GRASS Python bindings
import grass.script as gs

# launch session
session = gs.setup.init(gisdb, location, mapset)

# example calls
gs.message("Current GRASS GIS 8 environment:")
print(gs.gisenv())

gs.message("Available raster maps:")
for rast in gs.list_strings(type="raster"):
    print(rast)

gs.message("Available vector maps:")
for vect in gs.list_strings(type="vector"):
    print(vect)

# clean up at the end
session.finish()