# ---------------------------------------------------------------------------
# Create database export
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-11-18
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Create database export" compiles a local copy of a static database export saved as csv tables. The static database copy provides a stable reference and archive version.
# ---------------------------------------------------------------------------

# Import libraries
import os
import time
import sys
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
database_repository = os.path.join(drive, root_folder, 'Repositories/akveg-database')
credentials_folder = os.path.join(drive, root_folder,
                                  'OneDrive - University of Alaska/ACCS_Teams/Vegetation',
                                  'AKVEG_Database/Credentials/akveg_private_read/')
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
region_geopackage = os.path.join(project_folder, 'data/data_input/region_data/region_data_3338.gpkg')
bioclim_geopackage = os.path.join(project_folder, 'data/data_input/region_data/bioclimatic_zones_v2p1_3338.gpkg')
site_folder = os.path.join(project_folder, 'data/data_input/site_data', f'version_{version_date}')
output_folder = os.path.join(project_folder, 'data/data_input/database_archive', f'version_{version_date}')
output_geopackage = os.path.join(output_folder, '03_site_visit_3338.gpkg')

# Define input files
domain_layer = 'alaskayukon_project_v2p1_3338'
bioclim_layer = 'AlaskaYukon_USNVC_ZonesRegions_v2p1_3338'
validation_input = os.path.join(project_folder,
                                'Data/Data_Input/grid_data',
                                'AlaskaYukon_100_Tiles_100m_3338.tif')
coast_input = os.path.join(project_folder,
                           'Data/Data_Input/ancillary_data/processed/CoastDist_10m_3338.tif')
esa_input = os.path.join(project_folder,
                         'Data/Data_Input/ancillary_data/processed',
                         'AlaskaYukon_ESAWorldCover2_10m_3338.tif')
fire_input = os.path.join(project_folder,
                          'Data/Data_Input/ancillary_data/processed',
                          'AlaskaYukon_FireYear_10m_3338.tif')

# Define queries
taxa_file = os.path.join(database_repository, 'user_tools/queries/00_taxonomy.sql')
project_file = os.path.join(database_repository, 'user_tools/queries/01_project.sql')
site_file = os.path.join(database_repository, 'user_tools/queries/02_site.sql')
site_visit_file = os.path.join(database_repository, 'user_tools/queries/03_site_visit.sql')
vegetation_file = os.path.join(database_repository, 'user_tools/queries/05_vegetation.sql')
abiotic_file = os.path.join(database_repository, 'user_tools/queries/06_abiotic_top_cover.sql')
tussock_file = os.path.join(database_repository, 'user_tools/queries/07_whole_tussock_cover.sql')
ground_file = os.path.join(database_repository, 'user_tools/queries/08_ground_cover.sql')
structural_file = os.path.join(database_repository, 'user_tools/queries/09_structural_group_cover.sql')
shrub_file = os.path.join(database_repository, 'user_tools/queries/11_shrub_structure.sql')
environment_file = os.path.join(database_repository, 'user_tools/queries/12_environment.sql')
soilmetrics_file = os.path.join(database_repository, 'user_tools/queries/13_soil_metrics.sql')
soilhorizons_file = os.path.join(database_repository, 'user_tools/queries/14_soil_horizons.sql')

# Define output files
taxa_output = os.path.join(output_folder, '00_taxonomy.csv')
project_output = os.path.join(output_folder, '01_project.csv')
site_visit_output = os.path.join(output_folder, '03_site_visit.csv')
vegetation_output = os.path.join(output_folder, '05_vegetation_cover.csv')
abiotic_output = os.path.join(output_folder, '06_abiotic_cover.csv')
tussock_output = os.path.join(output_folder, '07_whole_tussock_cover.csv')
ground_output = os.path.join(output_folder, '08_ground_cover.csv')
structural_output = os.path.join(output_folder, '09_structural_cover.csv')
shrub_output = os.path.join(output_folder, '11_shrub_structure.csv')
environment_output = os.path.join(output_folder, '12_environment.csv')
soilmetrics_output = os.path.join(output_folder, '13_soil_metrics.csv')
soilhorizons_output = os.path.join(output_folder, '14_soil_horizons.csv')

# Create a connection to the AKVEG PostgreSQL database
authentication_file = os.path.join(credentials_folder, 'authentication_akveg_private_read.csv')
database_connection = connect_database_postgresql(authentication_file)

#### QUERY AND PROCESS AKVEG SITE VISITS
####------------------------------
print('Processing site visit data...')
start_time = time.time()

# Read site data from AKVEG Database
print('\tQuerying site data...')
with open(site_file, 'r') as site_read:
    site_query = site_read.read()
site_data = query_to_dataframe(database_connection, site_query)

# Read site visit data from AKVEG Database
print('\tQuerying site visit data...')
with open(site_visit_file, 'r') as site_visit_read:
    site_visit_query = site_visit_read.read()
site_visit_data = query_to_dataframe(database_connection, site_visit_query)

# Join site_visit and site tables
print('\tJoining site and site visit tables...')
site_visit_data = pd.merge(site_visit_data, site_data, on='site_code', how='outer')

# Assign observation year
site_visit_data['observe_datetime'] = pd.to_datetime(site_visit_data['observe_date'])
site_visit_data['observe_year'] = site_visit_data['observe_datetime'].dt.year

# Create geodataframe
print('\tProcessing geodataframe for export in EPSG:3338...')
site_visit_data = gpd.GeoDataFrame(
    site_visit_data,
    geometry=gpd.points_from_xy(site_visit_data.longitude_dd,
                                site_visit_data.latitude_dd),
    crs='EPSG:4269')

# Convert geodataframe to EPSG:3338
site_visit_data = site_visit_data.to_crs(crs='EPSG:3338')

# Extract coordinates in EPSG:3338
site_visit_data['cent_x'] = site_visit_data.geometry.x
site_visit_data['cent_y'] = site_visit_data.geometry.y

# Subset points to project domain
print('\tEnforcing project domain...')
domain_data = gpd.read_file(region_geopackage, layer=domain_layer)
site_visit_data = gpd.clip(site_visit_data, domain_data)

# Extract bioclimatic zone and vegetation region
print('\tAttributing bioclimatic zone and vegetation region...')
bioclim_data = gpd.read_file(bioclim_geopackage, layer=bioclim_layer)[
    ['geometry', 'zone', 'region']].rename(columns={'zone': 'bioclim_zone'})
site_visit_data = gpd.sjoin(site_visit_data, bioclim_data, how="left", predicate="within")
if 'index_right' in site_visit_data.columns:
    site_visit_data = site_visit_data.drop(columns=['index_right'])

# Identify coordinates from site visit data
coordinates = [(x, y) for x, y in zip(site_visit_data.geometry.x, site_visit_data.geometry.y)]

# Extract validation raster to sites
print('\tExtracting validation grid...')
with rasterio.open(validation_input) as src:
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['valid'] = [x[0] for x in extracted_values]

# Extract coast raster to sites
print('\tExtracting distance to coast...')
with rasterio.open(coast_input) as src:
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['coast'] = [x[0] for x in extracted_values]

# Extract ESA raster to sites
print('\tExtracting ESA land cover type...')
with rasterio.open(esa_input) as src:
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['esa_type'] = [x[0] for x in extracted_values]

# Extract fire raster to sites
print('\tExtracting most recent burn year...')
with rasterio.open(fire_input) as src:
    # Extract raster values
    extracted_values = src.sample(coordinates)
    # Append values to data frame
    site_visit_data['fire_year'] = [x[0] for x in extracted_values]

# Parse plot radius
print('\tConverting plot radius...')
site_visit_data['plot_radius_m'] = 0
site_visit_data['plot_radius_m'] = np.where((site_visit_data['perspective'] == 'aerial')
                                            & (site_visit_data['plot_dimensions_m'] == 'unknown'),
                                            20, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where((site_visit_data['perspective'] == 'aerial')
                                            & (site_visit_data['plot_dimensions_m'] == '100×100'),
                                            20, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where((site_visit_data['perspective'] == 'ground')
                                            & (site_visit_data['plot_dimensions_m'] == 'unknown'),
                                            5, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'] == '1×1',
                                            0.5, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['1 radius', '1×7', '1×8', '1×10', '1×12', '2×2', '2×5', '2×7', '2×10', '2×12', '2×20',
     '3×6', '3×7', '3×8', '3×10', '3×12', '3×15', '3×20', '3×25']),
    1, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['2 radius', '4×4', '4×8', '4×25', '5×5', '5×8', '5×10', '5×15', '5×20', '5×30',
     '5×15', '5×20', '5×30']),
    2, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['3 radius', '4 radius', '6×6', '6×10', '6×12', '7×8', '7×10', '8×8', '8×10', '8×12']),
    3, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['5 radius', '10×10', '10×12', '10×20', '10×30', '10×40']),
    4, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['6 radius', '12×12']),
    5, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['7 radius']),
    6, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['8 radius', '15×15', '15×18', '15×30', '15×100']),
    7, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['10 radius', '11.6 radius', '18×18', '20×20', '20×40', '20×80', '20×100']),
    8, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['12.5 radius', '25×100', '25×25']),
    10, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['15 radius', '30×80', '30×30']),
    12, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['20 radius']),
    15, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['23 radius', '25 radius', '50×50']),
    20, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['30 radius']),
    25, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'].isin(
    ['34.7 radius']),
    30, site_visit_data['plot_radius_m'])
site_visit_data['plot_radius_m'] = np.where(site_visit_data['plot_dimensions_m'] == '55 radius',
                                            50, site_visit_data['plot_radius_m'])

# Check that no plot dimensions remain unassigned
missing_dimensions = site_visit_data[site_visit_data['plot_radius_m'] == 0]['plot_dimensions_m'].unique()
if len(missing_dimensions) > 0:
    sys.exit(f'Warning: missing dimensions for: {missing_dimensions}')

# Define list of selected site visits
site_visit_list = site_visit_data['site_visit_code'].unique()

# Read vegetation data from AKVEG Database
print('\tQuerying vegetation data...')
with open(vegetation_file, 'r') as vegetation_read:
    vegetation_query = vegetation_read.read()
vegetation_data = query_to_dataframe(database_connection, vegetation_query)
vegetation_data = vegetation_data[vegetation_data['site_visit_code'].isin(site_visit_list)]

# Read abiotic top cover data from AKVEG Database
print('\tQuerying abiotic top cover data...')
with open(abiotic_file, 'r') as abiotic_read:
    abiotic_query = abiotic_read.read()
abiotic_data = query_to_dataframe(database_connection, abiotic_query)
abiotic_data = abiotic_data[abiotic_data['site_visit_code'].isin(site_visit_list)]

# Create list of unique site visits
print('\tChecking data completeness...')
vegetation_site_visits = vegetation_data['site_visit_code']
abiotic_site_visits = abiotic_data['site_visit_code']
veg_site_visits = pd.concat([vegetation_site_visits, abiotic_site_visits], axis=0).to_frame()
veg_site_list = veg_site_visits['site_visit_code'].unique()

# Check that all site visits in the site visit data have corresponding data in either vegetation or abiotic cover
missing_cover_sites = site_visit_data[~site_visit_data['site_visit_code'].isin(veg_site_list)]
missing_cover_sites = missing_cover_sites[missing_cover_sites['project_code'] != 'akveg_absences']
#### REMOVE IN FUTURE VERSION ####
missing_site_list = missing_cover_sites['site_visit_code'].unique()
site_visit_data = site_visit_data[~site_visit_data['site_visit_code'].isin(missing_site_list)]
missing_cover_sites = site_visit_data[~site_visit_data['site_visit_code'].isin(veg_site_list)]
missing_cover_sites = missing_cover_sites[missing_cover_sites['project_code'] != 'akveg_absences']
#### END REMOVE SECTION ####
if len(missing_cover_sites) > 0:
    sys.exit(f'Warning: {len(missing_cover_sites)} site visits missing from site_visit_data.')
if len(site_visit_data) != len(veg_site_list):
    sys.exit(f'Warning: site visits in site_visit_data and cover data do not match.')

# Create cover type per site visit
cover_type = vegetation_data[['site_visit_code', 'cover_type']].drop_duplicates()

# Join cover type to site visit data
print('\tJoining cover type to site visit data...')
site_visit_data = pd.merge(site_visit_data, cover_type, on='site_visit_code', how='outer')
site_visit_data['cover_type'] = site_visit_data['cover_type'].fillna('top foliar cover')

# Select columns
site_visit_data = site_visit_data[[
    'site_visit_code', 'project_code', 'site_code', 'data_tier',
    'observe_date', 'observe_year', 'perspective', 'cover_method', 'cover_type',
    'scope_vascular', 'scope_bryophyte', 'scope_lichen',
    'structural_class', 'homogeneous', 'plot_dimensions_m', 'plot_radius_m',
    'bioclim_zone', 'region', 'fire_year', 'esa_type', 'coast', 'valid',
    'latitude_dd', 'longitude_dd', 'cent_x', 'cent_y'
]]

# Create geometries for the export points
print('\tExporting site visit data...')
export_point_data = gpd.GeoDataFrame(
    site_visit_data,
    geometry=gpd.points_from_xy(site_visit_data.cent_x,
                                site_visit_data.cent_y),
    crs='EPSG:3338')

# Export site visit points to geopackage
export_point_data.to_file(output_geopackage, layer='site_visits_all_20261116')
end_timing(start_time)

#### QUERY AKVEG COVER DATA AND CHECK SITES
####------------------------------
print('Processing vegetation data...')
start_time = time.time()

# Read taxonomy standard from AKVEG Database
print('\tQuerying taxonomy data...')
with open(taxa_file, 'r') as taxa_read:
    taxa_query = taxa_read.read()
taxa_data = query_to_dataframe(database_connection, taxa_query)

#### QUERY OTHER AKVEG DATA
####------------------------------
print('Processing metadata and environmental data...')
start_time = time.time()

# Read project data from AKVEG Database
print('\tQuerying project data...')
with open(project_file, 'r') as project_read:
    project_query = project_read.read()
project_data = query_to_dataframe(database_connection, project_query).sort_values('project_code')

# Read whole tussock cover data from AKVEG Database
print('\tQuerying whole tussock data...')
with open(tussock_file, 'r') as tussock_read:
    tussock_query = tussock_read.read()
tussock_data = query_to_dataframe(database_connection, tussock_query)
tussock_data = tussock_data[tussock_data['site_visit_code'].isin(site_visit_list)]

# Read ground cover data from AKVEG Database
print('\tQuerying ground cover data...')
with open(ground_file, 'r') as ground_read:
    ground_query = ground_read.read()
ground_data = query_to_dataframe(database_connection, ground_query)
ground_data = ground_data[ground_data['site_visit_code'].isin(site_visit_list)]

# Read structural group cover data from AKVEG Database
print('\tQuerying structural group cover data...')
with open(structural_file, 'r') as structural_read:
    structural_query = structural_read.read()
structural_data = query_to_dataframe(database_connection, structural_query)
structural_data = structural_data[structural_data['site_visit_code'].isin(site_visit_list)]

# Read shrub structure data from AKVEG Database
print('\tQuerying shrub structure data...')
with open(shrub_file, 'r') as shrub_read:
    shrub_query = shrub_read.read()
shrub_data = query_to_dataframe(database_connection, shrub_query)
shrub_data = shrub_data[shrub_data['site_visit_code'].isin(site_visit_list)]

# Read environment data from AKVEG Database
print('\tQuerying environment data...')
with open(environment_file, 'r') as environment_read:
    environment_query = environment_read.read()
environment_data = query_to_dataframe(database_connection, environment_query)
environment_data = environment_data[environment_data['site_visit_code'].isin(site_visit_list)]

# Read soil metrics data from AKVEG Database
print('\tQuerying soil metrics data...')
with open(soilmetrics_file, 'r') as soilmetrics_read:
    soilmetrics_query = soilmetrics_read.read()
soilmetrics_data = query_to_dataframe(database_connection, soilmetrics_query)
soilmetrics_data = soilmetrics_data[soilmetrics_data['site_visit_code'].isin(site_visit_list)]

# Read soil horizons data from AKVEG Database
print('\tQuerying soil horizons data...')
with open(soilhorizons_file, 'r') as soilhorizons_read:
    soilhorizons_query = soilhorizons_read.read()
soilhorizons_data = query_to_dataframe(database_connection, soilhorizons_query)
soilhorizons_data = soilhorizons_data[soilhorizons_data['site_visit_code'].isin(site_visit_list)]

# Export data to csv files
print('\tExporting data to csv...')
taxa_data.to_csv(taxa_output, header=True, index=False, sep=',', encoding='utf-8')
project_data.to_csv(project_output, header=True, index=False, sep=',', encoding='utf-8')
site_visit_data.to_csv(site_visit_output, header=True, index=False, sep=',', encoding='utf-8')
vegetation_data.to_csv(vegetation_output, header=True, index=False, sep=',', encoding='utf-8')
abiotic_data.to_csv(abiotic_output, header=True, index=False, sep=',', encoding='utf-8')
tussock_data.to_csv(tussock_output, header=True, index=False, sep=',', encoding='utf-8')
ground_data.to_csv(ground_output, header=True, index=False, sep=',', encoding='utf-8')
structural_data.to_csv(structural_output, header=True, index=False, sep=',', encoding='utf-8')
shrub_data.to_csv(shrub_output, header=True, index=False, sep=',', encoding='utf-8')
environment_data.to_csv(environment_output, header=True, index=False, sep=',', encoding='utf-8')
soilmetrics_data.to_csv(soilmetrics_output, header=True, index=False, sep=',', encoding='utf-8')
soilhorizons_data.to_csv(soilhorizons_output, header=True, index=False, sep=',', encoding='utf-8')
end_timing(start_time)
