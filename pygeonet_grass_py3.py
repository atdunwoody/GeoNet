import configparser
import os
import shutil
import sys
import subprocess
import logging
import time

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
    os.environ['PATH'] += r"C:\OSGeo4W\apps\grass\grass83\scripts"
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

def create_grass_location(grass_executable, location, mapset, dem_path, gisdb):
    try:
        subprocess.run([grass_executable, '--exec', 'g.proj', f'georef={dem_path}', f'location={location}'], check=True)
        subprocess.run([grass_executable, '--exec', 'g.mapset', '-c', f'mapset={mapset}', f'location={location}', f'dbase={gisdb}'], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to create location/mapset with error: {e}")
        sys.exit(-1)

def run_grass_command(grass_executable, command, *args):
    cmd = [grass_executable, '--exec', command] + list(args)
    subprocess.run(cmd, check=True)

def main():
    config = load_config()
    geofloodhomedir = config['Section']['geofloodhomedir']
    projectname = config['Section']['projectname']
    dem_name = "PM_filtered_grassgis"
    output_dir = os.path.join(geofloodhomedir, config['Section']['output_dir'])
    dem_path = os.path.join(output_dir, "GIS", "TEST", f"{dem_name}.tif")
    grass_executable = r'C:\OSGeo4W\bin\grass83.bat'
    gisbase = r"C:\Users\adunw\Documents\grassdata"
    gisdb = r"C:\Users\adunw\Documents\grassdata"
    print(gisdb)
    
    set_environment_variables(gisbase, gisdb, geofloodhomedir)
    location_path = os.path.join(gisdb, projectname)
    delete_location(location_path)
    time.sleep(2)  # Ensure the location is deleted

    create_grass_location(grass_executable, projectname, 'PERMANENT', dem_path, gisdb)
    time.sleep(5)  # Ensure the location is created

    # Import the DEM into GRASS GIS
    run_grass_command(grass_executable, 'r.in.gdal', f'input={dem_path}', f'output={dem_name}')

    # Compute flow accumulation and drainage directions
    run_grass_command(grass_executable, 'r.watershed', f'elevation={dem_name}', 'accumulation=acc1v23', 'drainage=dra1v23')

    # Identify outlets and delineate basins
    run_grass_command(grass_executable, 'r.mapcalc', f'expression=outletmap = if(dra1v23, 1, null())')
    run_grass_command(grass_executable, 'r.to.vect', f'input=outletmap', 'output=outletpoints', 'type=point')
    run_grass_command(grass_executable, 'r.stream.basins', 'direction=dra1v23', 'points=outletpoints', 'basins=outletbasins')

    logging.info("Hydrological analysis completed. Results saved.")

if __name__ == '__main__':
    main()
