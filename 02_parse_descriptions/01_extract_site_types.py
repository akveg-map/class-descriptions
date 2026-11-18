# ---------------------------------------------------------------------------
# Extract site types
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-11-18
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Extract site types" assigns each site in the AKVEG Database to a site type from the AKVEG Map, excluding sites that fall outside of the categorical map domain.
# ---------------------------------------------------------------------------

# Import libraries
import os
import time
import sys
from datetime import datetime
import numpy as np
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
type_folder = os.path.join(project_folder, 'data/data_output/veg_types/rasters_final')
site_geopackage = os.path.join(archive_folder, '03_site_visit_3338.gpkg')

# Define input files
domain_layer = 'alaska_domain_v2p1_3338'
site_layer = 'site_visits_all_20261116'
schema_input = os.path.join(repository_folder, 'AKVEG_MapClass_Schema.csv')
type_input = os.path.join(type_folder, 'types_10m_3338.tif')

# Define output files
site_output = os.path.join(archive_folder, '03_site_visit_type_assignments.csv')

#### EXTRACT AKVEG TYPES TO SITES
####------------------------------
print('Extracting AKVEG types to sites...')
start_time = time.time()

# Read data
domain_data = gpd.read_file(region_geopackage, layer=domain_layer)
site_visit_data = gpd.read_file(site_geopackage, layer=site_layer)

# Clip site visit data to domain
site_visit_data = gpd.clip(site_visit_data, domain_shape)

# Identify coordinates from site visit data
coordinates = [(x, y) for x, y in zip(site_visit_data.geometry.x, site_visit_data.geometry.y)]

# Extract AKVEG types to sites
print('\tExtracting ESA land cover type...')
with rasterio.open(esa_input) as src:
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['esa_type'] = [x[0] for x in extracted_values]