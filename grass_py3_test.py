from __future__ import division
import os
import sys
import shutil
import subprocess
from time import perf_counter 
from pygeonet_rasterio import *
import pygeonet_prepare as Parameters
import configparser

print("Appending path")
sys.path.append(r'C:\OSGeo4W\apps\grass\grass83\etc\python')


def set_grass_environment(gisbase, gisdbase, location, mapset):
    os.environ['GISBASE'] = gisbase
    os.environ['PATH'] += os.pathsep + os.path.join(gisbase, 'bin')
    os.environ['PATH'] += os.pathsep + os.path.join(gisbase, 'scripts')
    os.environ['PATH'] += os.pathsep + os.path.join(gisbase, 'lib')
    os.environ['GISDBASE'] = gisdbase
    gisrc_content = f"GISDBASE: {gisdbase}\nLOCATION_NAME: {location}\nMAPSET: {mapset}\nGUI: text"
    gisrc_path = os.path.join(gisdbase, 'gisrc')
    with open(gisrc_path, 'w') as rc:
        rc.write(gisrc_content)
    os.environ['GISRC'] = gisrc_path

def create_location_from_geotiff(gisdbase, location_name, geotiff_path):
    location_path = os.path.join(gisdbase, location_name)
    print(f"location_path: {location_path}")
    if not os.path.exists(location_path):
        # Create a new GRASS GIS location from the GeoTIFF file
        print(f"Creating a new location from the GeoTIFF file: {geotiff_path}")
        
        # Get the projection of the GeoTIFF file
        dataset = gdal.Open(geotiff_path)
        projection = dataset.GetProjection()
        srs = osr.SpatialReference(wkt=projection)
        proj4 = srs.ExportToProj4()

        # Create a new location with the projection of the GeoTIFF file
        try:
            subprocess.run(['grass', '-c', geotiff_path, location_path, '-e', proj4], check=True)
            print(f"Created new location: {location_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error creating location: {e}")

def start_grass_session(gisbase, gisdbase, location, mapset):
    sys.path.append(os.path.join(os.environ['GISBASE'], 'etc', 'python'))
    import grass.script as gscript
    import grass.script.setup as gsetup
    
    gsetup.init(gisbase, gisdbase, location, mapset)
    print("GRASS session initiated.")

def load_config():
    config = configparser.ConfigParser()
    config.read('GeoNet_my_project.cfg')
    return config

if __name__ == "__main__":
    config = load_config()
    geofloodhomedir = config['Section']['geofloodhomedir']
    projectname = config['Section']['projectname']
    dem_name = "PM_filtered_grassgis"
    output_dir = os.path.join(geofloodhomedir, config['Section']['output_dir'])
    dem_path = os.path.join(output_dir, "GIS", projectname, "{}.tif".format(dem_name))
    grass_executable = config['Section']['grass_executable']
    gisbase = config['Section']['gisbase']
    gisdbase = config['Section']['gisdb']
    

    location = projectname
    mapset = 'PERMANENT'
    geotiff_path = dem_path
    print(f"dem_path: {dem_path}")
    # Set up the GRASS environment
    set_grass_environment(gisbase, gisdbase, location, mapset)
    
    # Create a new location based on the GeoTIFF file
    create_location_from_geotiff(gisdbase, location, geotiff_path)
    
    # Start the GRASS session
    start_grass_session(gisbase, gisdbase, location, mapset)
    
    # Example GRASS command
    current_mapset = gscript.read_command('g.mapset', flags='p').strip()
    print(f"Current mapset: {current_mapset}")

