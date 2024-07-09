import rasterio
from rasterio.mask import mask
import os
import glob
from pygeonet_rasterio import *

def get_raster_extent(raster_path):
    """Retrieve the bounding box of the raster."""
    with rasterio.open(raster_path) as src:
        return src.bounds

def clip_raster(input_raster, clipping_bounds):
    """Clip the raster using the provided bounds, set NoData value, and overwrite the original raster."""
    with rasterio.open(input_raster) as src:
        out_image, out_transform = mask(src, [clipping_bounds], crop=True)
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
    """Clip all rasters in the input folder by the extent of the clipping raster and set NoData value."""
    # Get the bounds of the clipping raster
    bounds = get_raster_extent(clipping_raster)
    
    # Process each raster in the input folder
    for raster_file in glob.glob(os.path.join(input_folder, '*.tif')):
        #make sure the raster is not the clipping raster
        if raster_file != clipping_raster:
            # Clip the raster and overwrite the original file
            clip_raster(raster_file, bounds)

# Specify the paths to your data
input_folder = os.path.dirname(Parameters.pmGrassGISfileName)
clipping_raster = Parameters.pmGrassGISfileName

# Run the function to clip and overwrite all rasters with NoData value set
clip_all_rasters(input_folder, clipping_raster)
