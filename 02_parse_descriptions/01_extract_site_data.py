# ---------------------------------------------------------------------------
# Extract site types
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-11-19
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Extract site types" assigns each site in the AKVEG Database to a site type from the AKVEG Map, excluding sites that fall outside of the categorical map domain.
# ---------------------------------------------------------------------------

# Import libraries
import os
import time
import pandas as pd
import geopandas as gpd
import rasterio
from akutils import *

# Set version date
version_date = '20261116'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
repository_folder = os.path.join(drive, root_folder, 'Repositories/class-descriptions')
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
region_geopackage = os.path.join(project_folder, 'data/data_input/region_data/region_data_3338.gpkg')
archive_folder = os.path.join(project_folder, 'data/data_input/database_archive', f'version_{version_date}')
site_geopackage = os.path.join(archive_folder, '03_site_visit_3338.gpkg' )
type_folder = os.path.join(project_folder, 'data/data_output/veg_types/rasters_final')
foliar_folder = os.path.join(project_folder, 'data/data_output/rasters_final/version_20260415')
topography_folder = os.path.join(drive, root_folder, 'Data/topography')
output_folder = os.path.join(project_folder, f'data/data_input/class_descriptions/version_{version_date}')

# Define input files
domain_layer = 'alaska_domain_v2p1_3338'
site_visit_layer = 'site_visits_all_20261116'
schema_input = os.path.join(repository_folder, 'AKVEG_MapClass_Schema.csv')
type_input = os.path.join(type_folder, 'types_10m_3338.tif')
water_input = os.path.join(foliar_folder, 'water_cvr_10m_3338.tif')
elevation_input = os.path.join(topography_folder, 'Elevation_10m_3338.tif')
slope_input = os.path.join(topography_folder, 'Slope_10m_3338.tif')

# Define output files
site_visit_output = os.path.join(output_folder, 'site_visits_compiled.csv')

#### EXTRACT AKVEG TYPES TO SITES
####------------------------------
print('Extracting AKVEG types to sites...')
start_time = time.time()

# Read schema data
schema_data = pd.read_csv(schema_input)

# Read data
domain_data = gpd.read_file(region_geopackage, layer=domain_layer)
site_visit_data = gpd.read_file(site_geopackage, layer=site_visit_layer)

# Clip site visit data to domain
site_visit_data = gpd.clip(site_visit_data, domain_data)

# Identify coordinates from site visit data
coordinates = [(x, y) for x, y in zip(site_visit_data.geometry.x, site_visit_data.geometry.y)]

# Extract AKVEG types to sites
print('\tExtracting AKVEG type...')
with rasterio.open(type_input) as src:
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['code'] = [x[0] for x in extracted_values]

# Extract water cover to sites
print('\tExtracting water cover percent...')
with rasterio.open(water_input) as src:
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['water_cover_pct'] = [x[0] for x in extracted_values]

# Extract elevation raster to sites
print('\tExtracting elevation...')
with rasterio.open(elevation_input) as src:
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['elevation_m'] = [x[0] for x in extracted_values]

# Extract slope raster to sites
print('\tExtracting slope...')
with rasterio.open(slope_input) as src:
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['slope_deg'] = [x[0] for x in extracted_values]

# Join schema table to raster value
site_visit_data = pd.merge(site_visit_data, schema_data, on='code', how='inner')

# Drop geometry
site_visit_data = site_visit_data.drop(columns=['geometry'])

# Export data to csv
site_visit_data.to_csv(site_visit_output, header=True, index=False, sep=',', encoding='utf-8')
end_timing(start_time)
