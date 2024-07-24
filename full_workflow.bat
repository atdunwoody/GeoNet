@echo off
REM Activate the Conda environment
CALL conda activate geonet

REM Change to the project directory
CD C:\Users\adunw\OneDrive\Documents\GitHub\GeoNet

python pygeonet_prepare.py 
REM Execute Python scripts for Nonlinear Filtering, Slope and Curvature
REM python pygeonet_nonlinear_filter.py 
python pygeonet_slope_curvature.py 2>> error_log.txt

python pygeonet_grass_py3.py 2>> error_log.txt

python pygeonet_clip_raster.py 2>> error_log.txt

REM Execute remaining Python scripts
python pygeonet_skeleton_definition.py 2>> error_log.txt
python pygeonet_fast_marching.py 2>> error_log.txt
python pygeonet_channel_head_definition.py 2>> error_log.txt

REM Deactivate the Conda environment
CALL conda deactivate

@echo on

pause
