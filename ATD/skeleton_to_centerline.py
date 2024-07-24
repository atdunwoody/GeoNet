import geopandas as gpd
from shapely.geometry import LineString, Point, MultiPolygon
from shapely.ops import split, unary_union
import numpy as np
import rasterio
from rasterio.features import rasterize
from skimage.morphology import skeletonize

def create_centerline(multipolygon_file, output_CL_file, tolerance=50):
    """Process each polygon in each MultiPolygon in the GeoPackage to create centerlines, apply smoothing, and save them."""
    
    def polygon_to_raster(poly, cell_size=1):
        """Convert a polygon to a raster array."""
        bounds = poly.bounds
        width = int(np.ceil((bounds[2] - bounds[0]) / cell_size))
        height = int(np.ceil((bounds[3] - bounds[1]) / cell_size))
        transform = rasterio.transform.from_origin(bounds[0], bounds[3], cell_size, cell_size)
        raster = rasterize([(poly, 1)], out_shape=(height, width), transform=transform)
        return raster, transform

    def raster_to_centerline(raster, transform):
        """Convert raster array to a centerline geometry."""
        skeleton = skeletonize(raster == 1)
        points = [Point(*rasterio.transform.xy(transform, row, col, offset='center'))
                  for row in range(skeleton.shape[0]) for col in range(skeleton.shape[1]) if skeleton[row, col]]
        if points:
            line = LineString(points)
            return line
        return None

    def smooth_line(line, tolerance):
        """Smooth the line geometry using the Douglas-Peucker algorithm."""
        if line:
            return line.simplify(tolerance, preserve_topology=False)
        return line

    def calc_centerline(polygon, cell_size=1):
        """Main function to create and smooth centerline from a polygon."""
        raster, transform = polygon_to_raster(polygon, cell_size)
        centerline = raster_to_centerline(raster, transform)
        smoothed_centerline = smooth_line(centerline, tolerance)
        return smoothed_centerline

    gdf = gpd.read_file(multipolygon_file)
    centerlines = []

    # Loop over each row in the GeoDataFrame
    for _, row in gdf.iterrows():
        geometry = row['geometry']
        if isinstance(geometry, MultiPolygon):
            for polygon in geometry:
                centerline = calc_centerline(polygon)
                if centerline:
                    centerlines.append(centerline)
        elif geometry.geom_type == 'Polygon':
            centerline = calc_centerline(geometry)
            if centerline:
                centerlines.append(centerline)

    # Create a new GeoDataFrame for centerlines
    centerlines_gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries(centerlines), crs=gdf.crs)
    centerlines_gdf.to_file(output_CL_file, driver='GPKG')  # Save to a new GeoPackage

    return centerlines_gdf


flow_accumulation_file = r"Y:\ATD\LIDAR 2021 - 2020\Flow Skeleton\flow_skeleton_ndv_clip.tif"
output_vect_file = r"Y:\ATD\LIDAR 2021 - 2020\Flow Skeleton\2021_flow_skeleton_ndv_clip_poly.gpkg"
# raster_to_vector_polygon(flow_accumulation_file, output_vect_file)

polygon_file = r"Y:\ATD\LIDAR 2021 - 2020\Flow Skeleton\2021_flow_skeleton_ndv_clip_poly_filtered.gpkg"
output_CL_file = r"Y:\ATD\LIDAR 2021 - 2020\Flow Skeleton\2021_centerlines.gpkg"
create_centerline(output_vect_file, output_CL_file, tolerance=50)
