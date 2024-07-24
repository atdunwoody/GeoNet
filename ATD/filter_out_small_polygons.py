import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon
from geoprocessing_tools import combine_touching_polygons

def filter_out_small_polygons(input_gpkg, output_gpkg, area_threshold):
    """
    Removes polygons with an area below a specified threshold from MultiPolygon geometries in a GeoPackage.

    Parameters:
        input_gpkg (str): Path to the input GeoPackage.
        output_gpkg (str): Path to the output GeoPackage where the results will be saved.
        area_threshold (float): Area threshold below which polygons will be removed.

    Returns:
        None
    """
    # Load the GeoPackage
    gdf = gpd.read_file(input_gpkg)
    
    # Function to filter polygons
    def filter_polygons(geometry):
        if isinstance(geometry, MultiPolygon):
            # Filter out small polygons and create a new MultiPolygon
            return MultiPolygon([poly for poly in geometry if poly.area >= area_threshold])
        elif isinstance(geometry, Polygon) and geometry.area < area_threshold:
            # Return None if the Polygon is smaller than the threshold (will be removed)
            return None
        return geometry

    # Apply the filtering function to all geometries
    gdf['geometry'] = gdf['geometry'].apply(filter_polygons)

    # Remove rows where geometry became None
    gdf = gdf.dropna(subset=['geometry'])

    # Save the cleaned GeoDataFrame to a new GeoPackage
    gdf.to_file(output_gpkg, driver='GPKG')

input_gpkg = r"Y:\ATD\LIDAR 2021 - 2020\Flow Skeleton\2021_flow_skeleton.gpkg"
out_gpkg = r"Y:\ATD\LIDAR 2021 - 2020\Flow Skeleton\2021_flow_skeleton_combined.gpkg"
area_threshold = 200  # Define the area threshold based on your data

combine_touching_polygons(input_gpkg, out_gpkg)