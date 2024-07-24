import numpy as np
import gdal

def load_raster(raster_path):
    """Load a raster file into a NumPy array."""
    ds = gdal.Open(raster_path)
    band = ds.GetRasterBand(1)
    arr = band.ReadAsArray()
    return arr, ds.GetGeoTransform(), ds.GetProjection()

def apply_threshold(arr, threshold):
    """Apply a threshold to define the stream network."""
    return np.where(arr > threshold, 1, 0)

def find_nodes(stream_network):
    """Identify nodes in the stream network."""
    nodes = np.zeros_like(stream_network)
    rows, cols = stream_network.shape
    print(f"Finding nodes in a {rows}x{cols} stream network.")
    for row in range(1, rows-1):
        for col in range(1, cols-1):
            # Check the 8-connected neighborhood
            neighborhood = stream_network[row-1:row+2, col-1:col+2]
            if stream_network[row, col] == 1:
                # Count stream neighbors
                count = np.sum(neighborhood) - 1  # subtract the center cell
                if count != 2:
                    nodes[row, col] = 1
    return nodes

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
    raster_path = r"C:\Users\alextd\Documents\GitHub\GeoNet\GeoOutputs\GIS\2021_LIDAR_fl_tr_3000\2021_DEM_Full_3000_fac.tif"
    output_stream_path = 'output_stream_network.tif'
    output_nodes_path = 'output_nodes.tif'
    threshold = 3000  # Define the threshold based on your data

    # Load the raster
    flow_acc, geo_transform, projection = load_raster(raster_path)
    
    # Apply threshold to define streams
    stream_network = apply_threshold(flow_acc, threshold)
    
    # Find nodes
    nodes = find_nodes(stream_network)
    
    # Save results
    save_raster(output_stream_path, stream_network, geo_transform, projection)
    save_raster(output_nodes_path, nodes, geo_transform, projection)

    print("Processing completed. Stream network and nodes maps have been saved.")

if __name__ == "__main__":
    main()
