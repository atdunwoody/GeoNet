import os
import sys
import subprocess
import os
import sys
import subprocess

# define GRASS Database
# add your path to grassdata (GRASS GIS database) directory
#gisdb = "~/grassdata"
# the following path is the default path on MS Windows
gisdb = "~/Documents/grassdata"

# specify (existing) Location and Mapset
location = "TEST"
mapset = "PERMANENT"

# path to the GRASS GIS launch script
# we assume that the GRASS GIS start script is available and on PATH
# query GRASS itself for its GISBASE
# (with fixes for specific platforms)
# needs to be edited by the user
#executable = r"C:\OSGeo4W\apps\grass\grass83"
if sys.platform.startswith("win"):
    # MS Windows
    executable = r"C:\OSGeo4W\bin\grass83.bat"
    # uncomment when using standalone WinGRASS installer
    # executable = r'C:\Program Files (x86)\GRASS GIS <version>\grass.bat'
    # this can be skipped if GRASS executable is added to PATH

# query GRASS GIS itself for its Python package path
grass_cmd = [executable, "--config", "python_path"]
process = subprocess.run(grass_cmd, check=True, text=True, stdout=subprocess.PIPE)

# define GRASS-Python environment
sys.path.append(process.stdout.strip())

import grass.script as g

def export_rasters(geotiffmapraster, results_directory):
    """
    Exports GRASS GIS raster layers to GeoTIFF format.

    Parameters:
    geotiffmapraster (str): Base name for the raster layers.
    results_directory (str): Directory to save the exported GeoTIFF files.
    """
    # Export outlets raster
    session = g.setup.init(gisdb, location, mapset)

    outlet_filename = geotiffmapraster + '_outlets.tif'
    g.run_command('r.out.gdal', input='outletmap', type='Float32',
                  output=os.path.join(results_directory, outlet_filename),
                  format='GTiff', overwrite=True)

    # Export flow accumulation raster
    outputFAC_filename = geotiffmapraster + '_fac.tif'
    g.run_command('r.out.gdal', input='acc1v23', type='Float64',
                  output=os.path.join(results_directory, outputFAC_filename),
                  format='GTiff', overwrite=True)

    # Export flow direction raster
    outputFDR_filename = geotiffmapraster + '_fdr.tif'
    g.run_command('r.out.gdal', input='dra1v23', type='Int32',
                  output=os.path.join(results_directory, outputFDR_filename),
                  format='GTiff', overwrite=True)

    # Export basins raster
    outputBAS_filename = geotiffmapraster + '_basins.tif'
    g.run_command('r.out.gdal', input='outletbasins', type='Int16',
                  output=os.path.join(results_directory, outputBAS_filename),
                  format='GTiff', overwrite=True)
    session.finish()
def main():
    # Example usage
    geotiffmapraster = 'PM_filtered_grassgis'
    results_directory = 'C:\\Users\\adunw\\Documents\\grassdata\\TEST\\PERMANENT'
    export_rasters(geotiffmapraster, results_directory)

if __name__ == '__main__':
    main()

