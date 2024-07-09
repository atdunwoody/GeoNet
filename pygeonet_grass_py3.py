import configparser
import os
import shutil
import subprocess
import logging
import time
import sys
from osgeo import gdal, osr
from pygeonet_rasterio import *

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config():
    config = configparser.ConfigParser()
    config.read('GeoNet_my_project.cfg')
    return config

def set_environment_variables(gisbase, gisdb, geofloodhomedir):
    os.environ['GISBASE'] = gisbase
    os.environ['PATH'] += os.pathsep + os.path.join(gisbase, 'bin')
    os.environ['GISDBASE'] = gisdb
    # Update to include grass83/bin in the PATH environment variable correctly.
    # os.environ['PATH'] += os.pathsep + r"C:\OSGeo4W\apps\grass\grass83\bin"

    print('GISBASE: ',os.environ['GISBASE'])
    print('GISDBASE: ',os.environ['GISDBASE'])
    


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


def main():
    filteredDemArray = read_geotif_filteredDEM()
    
    config = load_config()
    geofloodhomedir = config['Section']['geofloodhomedir']
    projectname = config['Section']['projectname']
    dem_name = "PM_filtered_grassgis"
    output_dir = os.path.join(geofloodhomedir, config['Section']['output_dir'])
    dem_path = os.path.join(output_dir, "GIS", projectname, f"{dem_name}.tif")
    grass_executable = config['Section']['grass_executable']
    gisbase = config['Section']['gisbase']
    gisdb = config['Section']['gisdb']


    set_environment_variables(gisbase, gisdb, geofloodhomedir)
    #delete_location(os.path.join(gisdb, projectname))
    #time.sleep(2)  # Ensure the location is deleted

    #create_grass_location(grass_executable, projectname, 'PERMANENT', dem_path, gisdb)
    #time.sleep(5)  # Ensure the location is created

    #validate_dem_projection(dem_path)

    # Import the DEM into GRASS GIS
    geotiff = Parameters.pmGrassGISfileName
    demFileName = Parameters.demFileName
    geotiffmapraster = demFileName.split('.')[0]
    print('GRASSGIS layer name: ',geotiffmapraster)
    logging.info(f"Importing DEM {dem_path} into GRASS GIS with explicit projection handling")
    subprocess.run([grass_executable, '--exec', 'r.in.gdal', f'input={geotiff}', f'output={geotiffmapraster}', '-o', '--overwrite'], check=True)
    
    subbasinThreshold = defaults.thresholdAreaSubBasinIndexing
    if (not hasattr(Parameters, 'xDemSize')) or (not hasattr(Parameters, 'yDemSize')):
        Parameters.yDemSize=np.size(filteredDemArray,0)
        Parameters.xDemSize=np.size(filteredDemArray,1)
    if Parameters.xDemSize > 4000 or Parameters.yDemSize > 4000:
        logging.info('Using swap memory option for large size DEM')
        subprocess.run([grass_executable, '--exec', 'r.watershed', '-am', '--overwrite', 
                        f'elevation={geotiffmapraster}', 
                        f'threshold={subbasinThreshold}', 
                        f'drainage=dra1v23'], check=True)
        subprocess.run([grass_executable, '--exec', 'r.watershed', '-am', '--overwrite',
                        f'elevation={geotiffmapraster}',
                        f'threshold={subbasinThreshold}',
                        'accumulation=acc1v23'], check=True)
    else:
        subprocess.run([grass_executable, '--exec', 'r.watershed', '-a', '--overwrite',
                        f'elevation={geotiffmapraster}',
                        f'threshold={subbasinThreshold}',
                        'drainage=dra1v23', 'accumulation=acc1v23'], 
                        check=True)
    
    # Manage extensions
    extensions = ['r.stream.basins', 'r.stream.watersheds']
    for extension in extensions:
        try:
            # Check if the extension is installed and install if missing
            subprocess.run([grass_executable, '--exec', 'g.extension', 'extension=' + extension], check=True)
        except subprocess.CalledProcessError:
            # Handle cases where the extension installation fails
            logging.error(f"Failed to install extension {extension}")
            
    # Hydrological analysis
    logging.info("Identify outlets by negative flow direction")
    subprocess.run([grass_executable, '--exec', 
                    'r.mapcalc', '--overwrite',
                    f'expression=outletmap = if(dra1v23, 1, null())'], 
                    check=True)
    logging.info("Converting outlet raster to vector")
    subprocess.run([grass_executable, '--exec', 
                    'r.to.vect', '--overwrite',
                    f'input=outletmap', 'output=outletpoints', 'type=point'], 
                    check=True)
    
    logging.info("Delineating basins according to outlets")
    subprocess.run([grass_executable, '--exec', 
                    'r.stream.basins', '--overwrite',
                    'direction=dra1v23', 'points=outletpoints', 
                    'basins=outletbasins'], check=True)

    logging.info("Exporting rasters and vectors")
    outlet_filename = geotiffmapraster + '_outlets.tif'
    subprocess.run([grass_executable, '--exec', 'r.out.gdal', '--overwrite',
                    f'input=outletmap', 'type=Float32',
                    f'output={os.path.join(Parameters.geonetResultsDir, outlet_filename)}',
                    'format=GTiff'], check=True)
    
    outputFAC_filename = geotiffmapraster + '_fac.tif'
    subprocess.run([grass_executable, '--exec', 'r.out.gdal', '--overwrite',
                    f'input=acc1v23', 'type=Float64',
                    f'output={os.path.join(Parameters.geonetResultsDir, outputFAC_filename)}',
                    'format=GTiff'], check=True)

    outputFDR_filename = geotiffmapraster + '_fdr.tif'
    subprocess.run([grass_executable, '--exec', 'r.out.gdal', '--overwrite',
                    f'input=dra1v23', 'type=Int32',
                    f'output={os.path.join(Parameters.geonetResultsDir, outputFDR_filename)}',
                    'format=GTiff'], check=True)

    outputBAS_filename = geotiffmapraster + '_basins.tif'
    subprocess.run([grass_executable, '--exec', 'r.out.gdal', '--overwrite',
                    f'input=outletbasins', 'type=Int32',
                    f'output={os.path.join(Parameters.geonetResultsDir, outputBAS_filename)}',
                    'format=GTiff'], check=True)
    
    logging.info("Hydrological analysis completed. Results saved.")

if __name__ == "__main__":
    main()
