import numpy as np
import gdal
import os

def load_raster(raster_path):
    """Load a raster file into a NumPy array."""
    ds = gdal.Open(raster_path)
    band = ds.GetRasterBand(1)
    arr = band.ReadAsArray()
    return arr, ds.GetGeoTransform(), ds.GetProjection()

def apply_threshold(arr, threshold):
    """Apply a threshold to define the stream network."""
    return np.where(arr > threshold, 1, 0)

def find_junctions(stream_network):
    """Identify junctions in the stream network where two or more streams meet."""
    junctions = np.zeros_like(stream_network)
    rows, cols = stream_network.shape
    print(f"Finding junctions in a {rows}x{cols} stream network.")
    for row in range(1, rows-1):
        #print progress every 100 rows and replace line in place
        if row % 100 == 0:
            print(f"Processing row {row} of {rows}...", end='\r')
        for col in range(1, cols-1):
            if stream_network[row, col] == 1:
                # Check the 8-connected neighborhood
                neighborhood = stream_network[row-1:row+2, col-1:col+2]
                # Consider the cell itself as non-stream for counting connections
                neighborhood[1, 1] = 0
                # Count unique connected components around the central cell
                label_count = count_connected_components(neighborhood)
                if label_count > 1:
                    junctions[row, col] = 1
    return junctions

def count_connected_components(neighborhood):
    """Count connected components in a 3x3 binary neighborhood."""
    from scipy.ndimage import label
    structure = np.array([[1,1,1],
                          [1,0,1],
                          [1,1,1]])
    labeled, num_features = label(neighborhood, structure)
    return num_features

def save_raster(out_path, array, geo_transform, projection):
    """Save a NumPy array as a raster file."""
    driver = gdal.GetDriverByName('GTiff')
    rows, cols = array.shape
    dataset = driver.Create(out_path, cols, rows, 1, gdal.GDT_Byte)
    dataset.SetGeoTransform(geo_transform)
    dataset.SetProjection(projection)
    band = dataset.GetRasterBand(1)
    band.WriteArray(array)
    dataset.FlushCache()

def main():
    raster_path = "Y:\ATD\LIDAR 2021 - 2020\Flow Skeleton\Test_fac_reproj_bilinear.tif"
    dir_path = os.path.dirname(raster_path)
    output_stream_path = os.path.join(dir_path, 'output_stream_network.tif')
    output_junctions_path = os.path.join(dir_path, 'output_junctions.tif')
    threshold = 10000  # Define the threshold based on your data

    # Load the raster
    flow_acc, geo_transform, projection = load_raster(raster_path)
    
    # Apply threshold to define streams
    stream_network = apply_threshold(flow_acc, threshold)
    
    # Find junctions
    junctions = find_junctions(stream_network)
    
    # Save results
    save_raster(output_stream_path, stream_network, geo_transform, projection)
    save_raster(output_junctions_path, junctions, geo_transform, projection)

    print("Processing completed. Stream network and junction maps have been saved.")

if __name__ == "__main__":
    main()
