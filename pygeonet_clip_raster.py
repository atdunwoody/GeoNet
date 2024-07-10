from shapely.geometry import box
import rasterio
from rasterio.mask import mask
import os
import glob
from pygeonet_rasterio import *

def get_raster_extent(raster_path):
    """Retrieve the bounding box of the raster and convert it to a polygon."""
    with rasterio.open(raster_path) as src:
        bounds = src.bounds
        return box(bounds.left, bounds.bottom, bounds.right, bounds.top)

def clip_raster(input_raster, clipping_polygon):
    """Clip the raster using the provided polygon and overwrite the original raster."""
    with rasterio.open(input_raster) as src:
        out_image, out_transform = mask(src, [clipping_polygon], crop=True)
        out_meta = src.meta.copy()
        
        # Update the metadata to reflect the new dimensions, transform, and NoData value
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
            "nodata": -9999  # Set NoData value to -9999
        })
        
        # Set NoData value in the array
        out_image[out_image == src.nodata] = -9999
        
        # Write the clipped raster back to the same file
        with rasterio.open(input_raster, "w", **out_meta) as dest:
            dest.write(out_image)

def clip_all_rasters(input_folder, clipping_raster):
    """Clip all rasters in the input folder by the polygon extent of the clipping raster and set NoData value."""
    # Get the polygon from the bounds of the clipping raster
    clipping_polygon = get_raster_extent(clipping_raster)
    
    # Process each raster in the input folder
    for raster_file in glob.glob(os.path.join(input_folder, '*.tif')):
        print(f"Clipping raster: {raster_file}")
        clip_raster(raster_file, clipping_polygon)

# Specify the paths to your data
input_folder = os.path.dirname(Parameters.pmGrassGISfileName)
clipping_raster = Parameters.pmGrassGISfileName

# Run the function to clip and overwrite all rasters with NoData value set
clip_all_rasters(input_folder, clipping_raster)
