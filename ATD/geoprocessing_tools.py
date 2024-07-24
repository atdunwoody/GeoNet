import geopandas as gpd
from shapely.geometry import Polygon,MultiPolygon
from shapely.ops import unary_union, cascaded_union
from shapely.geometry import box
from shapely.geometry import LineString, MultiLineString
import numpy as np
from shapely.geometry import shape, mapping
import fiona
import rasterio
from rasterio.features import shapes
import numpy as np
from shapely.geometry import shape, LineString
import geopandas as gpd


def erase(target_gdf, eraser_gdf):
    """
    Performs a geometric erase operation on the target GeoDataFrame using the eraser GeoDataFrame.

    Parameters:
    - target_gdf (GeoDataFrame): The GeoDataFrame to be erased.
    - eraser_gdf (GeoDataFrame): The GeoDataFrame that defines the areas to erase.

    Returns:
    - GeoDataFrame: The result of erasing the specified areas from the target GeoDataFrame.
    """
    # Ensure that the data is in the same projection
    if target_gdf.crs != eraser_gdf.crs:
        eraser_gdf = eraser_gdf.to_crs(target_gdf.crs)

    # Use overlay with the difference operation
    result_gdf = gpd.overlay(target_gdf, eraser_gdf, how='difference')

    # Handle the possibility of multi-part polygons by converting them to single-part
    result_gdf['geometry'] = result_gdf['geometry'].apply(lambda x: MultiPolygon([x]) if not x.is_valid else x)

    return result_gdf

def clip(target_gdf, clipper_gdf):
    """
    Performs a geometric clip operation where the target GeoDataFrame is clipped to the boundaries of the clipper GeoDataFrame.

    Parameters:
    - target_gdf (GeoDataFrame): The GeoDataFrame that will be clipped.
    - clipper_gdf (GeoDataFrame): The GeoDataFrame that defines the clip boundaries.

    Returns:
    - GeoDataFrame: The resulting GeoDataFrame after clipping.
    """
    # Ensure that both GeoDataFrames are in the same projection
    if target_gdf.crs != clipper_gdf.crs:
        clipper_gdf = clipper_gdf.to_crs(target_gdf.crs)
    
    # Perform the clip operation using spatial join and intersection
    clipped_gdf = gpd.overlay(target_gdf, clipper_gdf, how='intersection')
    
    return clipped_gdf

def multipolygon_to_polygon(input_geopackage, output_geopackage):
    """
    Convert a multipolygon from a GeoPackage to its exterior outline and save the result to another GeoPackage.

    Args:
        input_geopackage (str): Path to the input GeoPackage.
        layer_name (str): Layer name of the multipolygon in the input GeoPackage.
        output_geopackage (str): Path to the output GeoPackage.
        output_layer_name (str): Layer name for the output polygon in the output GeoPackage.
    """
    # Read the multipolygon from the GeoPackage
    gdf = gpd.read_file(input_geopackage)
    
    # Ensure the geometry is a multipolygon
    if not all(gdf.geometry.type.isin(['MultiPolygon', 'Polygon'])):
        raise ValueError("All geometries must be (multi)polygons")
    
    # Use unary_union to dissolve all polygons into a single outline
    outline = unary_union(gdf.geometry)

    # Create a new GeoDataFrame with the resulting outline
    result_gdf = gpd.GeoDataFrame(geometry=[outline], crs=gdf.crs)

    # Write the result to the output GeoPackage
    result_gdf.to_file(output_geopackage, driver='GPKG')
    return result_gdf

def fill_holes(gdf):
    """
    Fills all holes in polygons or multipolygons in a GeoDataFrame, making each geometry solid.

    Parameters:
    - gdf (GeoDataFrame): A GeoDataFrame containing the geometries to process.

    Returns:
    - GeoDataFrame: A new GeoDataFrame with all holes removed from the geometries.
    """
    def remove_holes(geometry):
        # Check if the geometry is None
        if geometry is None:
            return None
        
        if geometry.geom_type == 'Polygon':
            return Polygon(geometry.exterior)
        
        elif geometry.geom_type == 'MultiPolygon':
            # Use the .geoms property as per Shapely 1.8+ and avoid direct iteration
            return MultiPolygon([Polygon(poly.exterior) for poly in geometry.geoms])
        
        else:
            return geometry  # Return non-polygon geometries unchanged

    # Apply the remove_holes function to each geometry in the GeoDataFrame
    gdf['geometry'] = gdf['geometry'].apply(remove_holes)
    return gdf

def clean_shp(gdf):
    """
    Cleans a GeoDataFrame by:
    - Removing rows with None geometries.
    - Removing rows with invalid geometries and attempting to fix them.
    - Removing duplicate geometries.

    Parameters:
    - gdf (GeoDataFrame): The GeoDataFrame to clean.

    Returns:
    - GeoDataFrame: A cleaned GeoDataFrame.
    """
    # Remove rows where geometry is None
    gdf = gdf[gdf['geometry'].notnull()]

    # Fix invalid geometries if possible, remove if not fixable
    gdf['geometry'] = gdf['geometry'].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)

    # Remove duplicates based on geometries
    gdf = gdf.drop_duplicates(subset='geometry')

    return gdf

def fill_polygon_holes(input_gdf, output_file, dissolve_by=None):
    """
    Fills holes in the interior of polygons.

    Parameters:
    - input_gdf: Input GeoDataFrame containing polygons.
    - output_file: Path where the modified GeoDataFrame will be saved.
    """
    if isinstance(input_gdf, str):
        input_gdf = gpd.read_file(input_gdf)
    def fill_holes(geometry):
        if geometry.geom_type == 'Polygon':
            return Polygon(geometry.exterior)
        elif geometry.geom_type == 'MultiPolygon':
            return MultiPolygon([Polygon(poly.exterior) for poly in geometry.geoms])
        return geometry

    # Fill holes in the polygons
    filled_polygons = input_gdf.copy()
    filled_polygons['geometry'] = filled_polygons['geometry'].apply(fill_holes)
    
    # Dissolve the polygons
    if dissolve_by is not None:
        dissolved_polygons = filled_polygons.dissolve(by=dissolve_by)
    else:
        dissolved_polygons = filled_polygons.dissolve()
    
    # Save the result to a new file
    dissolved_polygons.to_file(output_file)

def create_buffer(gpkg_path, buffer_distance):
    # Open the GeoPackage with fiona to read the layer
    with fiona.open(gpkg_path) as src:
        # Schema of the new GeoPackage (adding buffered geometries)
        schema = src.schema.copy()
        schema['geometry'] = 'Polygon'  # Update geometry type if necessary
        
        # Create a new GeoPackage for output
        output_path = gpkg_path.replace('.gpkg', '_shapely_buffered.gpkg')
        with fiona.open(output_path, 'w', driver='GPKG', schema=schema, crs=src.crs) as dst:
            # Iterate over all records in the source layer, buffer them, and write to the new file
            for feature in src:
                geom = shape(feature['geometry'])
                buffered_geom = geom.buffer(buffer_distance)
                
                # Create new feature with the buffered geometry
                new_feature = {
                    'geometry': mapping(buffered_geom),
                    'properties': feature['properties']
                }
                
                dst.write(new_feature)
    
    return output_path

def raster_to_vector_perimeter(raster_path, output_vector_path, threshold=0):
    """
    Converts a raster to a vector line file based on a threshold.

    Parameters:
    raster_path (str): Path to the raster file.
    output_vector_path (str): Path where the vector file will be saved.
    threshold (int): Pixel intensity threshold to define features.
    """
    with rasterio.open(raster_path) as src:
        # Read the first band
        band = src.read(1)
        
        # Apply threshold to create a binary image
        mask = band > threshold
        
        # Extract shapes from the mask
        shapes_and_values = shapes(band, mask=mask, transform=src.transform)
        
        # Convert shapes to LineString if possible
        lines = []
        for geom, value in shapes_and_values:
            # Convert each shape to a shapely geometry
            s = shape(geom)
            if s.is_valid and s.geom_type == 'Polygon':
                # Convert polygon to line (boundary of the polygon)
                line = s.boundary
                if isinstance(line, LineString):
                    lines.append(line)
                elif line.geom_type == 'MultiLineString':
                    # If MultiLineString, take each component
                    for linestring in line:
                        lines.append(linestring)

        # Create a GeoDataFrame
        gdf = gpd.GeoDataFrame(geometry=lines, crs=src.crs)
        
        # Save to file
        gdf.to_file(output_vector_path, driver='GeoJSON')

def raster_to_vector_polygon(raster_path, output_vector_path, threshold=0):
    """
    Converts a raster to a vector polygon file based on a threshold.

    Parameters:
    raster_path (str): Path to the raster file.
    output_vector_path (str): Path where the GeoPackage file will be saved.
    threshold (int): Pixel intensity threshold to define features.
    """
    with rasterio.open(raster_path) as src:
        # Read the first band
        band = src.read(1)
        
        # Apply threshold to create a binary image
        mask = band > threshold
        
        # Extract shapes from the mask
        shapes_and_values = shapes(band, mask=mask, transform=src.transform)
        
        # Convert shapes to polygons
        polygons = []
        for geom, value in shapes_and_values:
            # Convert each shape to a shapely geometry
            s = shape(geom)
            if s.is_valid and s.geom_type == 'Polygon':
                polygons.append(s)

        # Create a GeoDataFrame
        gdf = gpd.GeoDataFrame(geometry=polygons, crs=src.crs)
        
        # Save to file as a GeoPackage
        gdf.to_file(output_vector_path, driver='GPKG')

import geopandas as gpd
from shapely.ops import unary_union


def combine_touching_polygons(input_gpkg, output_gpkg):
    """
    Combine touching polygons within a GeoPackage layer by creating a small buffer.

    Parameters:
    - input_gpkg: Path to the input GeoPackage file.
    - output_gpkg: Path to the output GeoPackage file.
    """
    # Load the GeoPackage
    gdf = gpd.read_file(input_gpkg)

    # Buffer the geometries slightly to merge touching polygons
    buffered_gdf = gdf.copy()
    buffered_gdf['geometry'] = gdf.geometry.buffer(0.5)  # Adjust the buffer size if necessary

    # Use unary_union to dissolve all geometries
    dissolved = buffered_gdf.unary_union

    # Create a new GeoDataFrame from the dissolved geometry
    result_gdf = gpd.GeoDataFrame(geometry=[dissolved], crs=buffered_gdf.crs)

    # Explode multi-part geometries into single-part geometries
    result_gdf = result_gdf.explode().reset_index(drop=True)

    # Reproject the result if needed and clean up the geometry
    result_gdf['geometry'] = result_gdf.geometry.buffer(-0.0001)  # Negate the initial buffer

    # Save the cleaned GeoDataFrame back to a GeoPackage
    result_gdf.to_file(output_gpkg, layer='merged_layer', driver='GPKG')



def main():

    chan_path = r"Y:\ATD\GIS\East_Troublesome\Watershed Statistical Analysis\Watershed Stats\Test - Slope\LM2 Channel Stats.gpkg"
    buffer_path = r"Y:\ATD\GIS\East_Troublesome\Watershed Statistical Analysis\Watershed Stats\Test - Slope\LM2 Centerline_shapely_buffered.gpkg"
    CL_path = r'Y:\\ATD\\GIS\\East_Troublesome\\Watershed Statistical Analysis\\Watershed Stats\\Test - Slope\\LM2 Centerline.gpkg'
    perp_path = r"Y:\ATD\GIS\East_Troublesome\Watershed Statistical Analysis\Watershed Stats\Test - Slope\Buffer as Lines\LM2 Centerline_perpendiculars_100m.gpkg"
    output_path = r"Y:\ATD\GIS\East_Troublesome\Watershed Statistical Analysis\Watershed Stats\Test - Slope\Chan Single.gpkg"
    section_path = r"Y:\ATD\GIS\East_Troublesome\Watershed Statistical Analysis\Watershed Stats\Test - Slope\LM2 Centerline_shapely_buffered_multipolygon.gpkg"
    buffer_outline_path = r"Y:\ATD\GIS\East_Troublesome\Watershed Statistical Analysis\Watershed Stats\Test - Slope\Buffer as Lines\Buffer outline.gpkg"
    
    
    
    #multi_poly_path = centerline_to_multipolygon(buffer_path, CL_path, length=10, width=200)
    buffer_gdf = gpd.read_file(buffer_outline_path)
    perp_gdf = gpd.read_file(perp_path)
    #clipped_gdf  = clip(perp_gdf, buffer_gdf)
    #clipped_gdf.to_file(output_path, driver='GPKG')


if __name__ == "__main__":
    main()