
import configparser
import os
import shutil
import subprocess
import logging
import time
import sys
from osgeo import gdal, osr

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config():
    config = configparser.ConfigParser()
    config.read('GeoNet_my_project.cfg')
    return config

def set_environment_variables(gisbase, gisdb, geofloodhomedir):
    os.environ['GISBASE'] = gisbase
    os.environ['PATH'] += os.pathsep + os.path.join(gisbase, 'extrabin')
    os.environ['GISDBASE'] = gisdb
    # Update to include grass83/bin in the PATH environment variable correctly.
    os.environ['PATH'] += os.pathsep + r"C:\OSGeo4W\apps\grass\grass83\bin"

    if not os.path.exists(gisdb):
        os.makedirs(gisdb)

def delete_location(location_path):
    if os.path.exists(location_path):
        try:
            shutil.rmtree(location_path)
            logging.info(f"Deleted existing location: {location_path}")
        except Exception as e:
            logging.error(f"Could not delete location {location_path}. {e}")
            sys.exit(-1)

def get_projection(dem_path):
    dataset = gdal.Open(dem_path)
    projection = dataset.GetProjection()
    srs = osr.SpatialReference(wkt=projection)
    return srs.ExportToProj4()

def create_grass_location(grass_executable, location, mapset, dem_path, gisdb):
    dem_projection = get_projection(dem_path)
    
    try:
        # Correct command line format for g.proj and g.mapset
        subprocess.run([grass_executable, '--exec', 'g.proj', '-c', 'proj4={}'.format(dem_projection), 'location={}'.format(location)], check=True, cwd=gisdb)
        subprocess.run([grass_executable, '--exec', 'g.mapset', '-c', 'mapset={}'.format(mapset), 'location={}'.format(location)], check=True, cwd=gisdb)
        logging.info(f"Created new location with projection: {dem_projection}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to create location/mapset with error: {e}")
        sys.exit(-1)

def validate_dem_projection(dem_path):
    dataset = gdal.Open(dem_path)
    if not dataset:
        logging.error("Unable to open the DEM file.")
        return

    proj = dataset.GetProjection()
    srs = osr.SpatialReference(wkt=proj)
    if srs.IsProjected():
        logging.info(f"DEM Projection is: {srs.GetAttrValue('PROJCS')}")
    else:
        logging.error("DEM does not have a valid projected coordinate system.")
    
    geotransform = dataset.GetGeoTransform()
    if geotransform:
        width = dataset.RasterXSize
        height = dataset.RasterYSize
        minx = geotransform[0]
        maxy = geotransform[3]
        maxx = minx + width * geotransform[1]
        miny = maxy + height * geotransform[5]  # Note: geotransform[5] is negative
        logging.info(f"Bounds of the DEM are: minx={minx}, maxx={maxx}, miny={miny}, maxy={maxy}")
    else:
        logging.error("Unable to get the geotransform for the DEM.")



def export_raster(grass_executable, raster_name, output_path):
    try:
        subprocess.run([grass_executable, '--exec', 'r.out.gdal', f'input={raster_name}', f'output={output_path}', 'format=GTiff', '--overwrite'], check=True)
        logging.info(f"Exported raster {raster_name} to {output_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to export raster {raster_name} with error: {e}")

def export_vector(grass_executable, vector_name, output_path):
    try:
        subprocess.run([grass_executable, '--exec', 'v.out.ogr', f'input={vector_name}', f'output={output_path}', 'format=ESRI_Shapefile', '--overwrite'], check=True)
        logging.info(f"Exported vector {vector_name} to {output_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to export vector {vector_name} with error: {e}")

def main():
    config = load_config()
    geofloodhomedir = config['Section']['geofloodhomedir']
    projectname = config['Section']['projectname']
    dem_name = "PM_filtered_grassgis"
    output_dir = os.path.join(geofloodhomedir, config['Section']['output_dir'])
    dem_path = os.path.join(output_dir, "GIS", projectname, f"{dem_name}.tif")
    grass_executable = config['Section']['grass_executable']
    gisbase = config['Section']['gisbase']
    gisdb = config['Section']['gisdb']
    mapset = config['Section']['mapset']

    print(f'Output directory: {output_dir}\n'
          f'DEM path: {dem_path}\n'
          f'GRASS executable: {grass_executable}\n'
          f'GIS base: {gisbase}\n',
          f'GIS database: {gisdb}\n')
    
    raster_output_dir = os.path.join(output_dir, 'rasters')
    vector_output_dir = os.path.join(output_dir, 'vectors')
    os.makedirs(raster_output_dir, exist_ok=True)
    os.makedirs(vector_output_dir, exist_ok=True)

    set_environment_variables(gisbase, gisdb, geofloodhomedir)
    #delete_location(os.path.join(gisdb, projectname))
    time.sleep(2)  # Ensure the location is deleted

    #create_grass_location(grass_executable, projectname, 'PERMANENT', dem_path, gisdb)
    #time.sleep(5)  # Ensure the location is created

    validate_dem_projection(dem_path)

    # Import the DEM into GRASS GIS
    logging.info(f"Importing DEM {dem_path} into GRASS GIS with explicit projection handling")
    subprocess.run([grass_executable, '--exec', 'r.in.gdal', f'input={dem_path}', f'output={dem_name}', '-o', '--overwrite'], check=True)

    # Hydrological analysis
    # subprocess.run([grass_executable, '--exec', 'r.watershed', f'elevation={dem_name}', 'accumulation=acc1v23', 'drainage=dra1v23'], check=True)
    # subprocess.run([grass_executable, '--exec', 'r.mapcalc', f'expression=outletmap = if(dra1v23, 1, null())'], check=True)
    # subprocess.run([grass_executable, '--exec', 'r.to.vect', f'input=outletmap', 'output=outletpoints', 'type=point'], check=True)
    # subprocess.run([grass_executable, '--exec', 'r.stream.basins', 'direction=dra1v23', 'points=outletpoints', 'basins=outletbasins'], check=True)

    export_raster(grass_executable, 'acc1v23', os.path.join(raster_output_dir, 'accumulation.tif'))
    export_raster(grass_executable, 'dra1v23', os.path.join(raster_output_dir, 'drainage.tif'))
    export_vector(grass_executable, 'outletpoints', os.path.join(vector_output_dir, 'outlet_points.shp'))
    export_vector(grass_executable, 'outletbasins', os.path.join(vector_output_dir, 'outlet_basins.shp'))

if __name__ == "__main__":
    main()
