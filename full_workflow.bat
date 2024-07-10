@echo off
REM Activate the Conda environment
CALL conda activate geonet

REM Change to the project directory
CD C:\Users\adunw\OneDrive\Documents\GitHub\GeoNet

REM Execute Python scripts for Nonlinear Filtering, Slope and Curvature
python pygeonet_nonlinear_filter.py
python pygeonet_slope_curvature.py

python pygeonet_grass_py3.py

python pygeonet_clip_raster.py

REM Execute remaining Python scripts
python pygeonet_skeleton_definition.py
python pygeonet_fast_marching.py
python pygeonet_channel_head_definition.py

REM Deactivate the Conda environment
CALL conda deactivate

@echo on
