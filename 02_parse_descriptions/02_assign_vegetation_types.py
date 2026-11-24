# ---------------------------------------------------------------------------
# Assign vegetation types
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-11-21
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Assign vegetation types" creates a table of selected site visits that meet quality control criteria for each type.
# ---------------------------------------------------------------------------

# Import libraries
import os
import time
import numpy as np
import pandas as pd
import kaleido
from akutils import *

# Initialize kaleido
kaleido.get_chrome_sync()

# Define version date
version_date = '20261116'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
repository_folder = os.path.join(drive, root_folder, 'Repositories/class-descriptions')
project_folder = os.path.join(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map')
archive_folder = os.path.join(project_folder, f'data/data_input/database_archive/version_{version_date}')
class_folder = os.path.join(project_folder, f'data/data_input/class_descriptions/version_{version_date}')

# Define input data
schema_input = os.path.join(repository_folder, 'AKVEG_MapClass_Schema.csv')
diagnostic_input = os.path.join(drive, root_folder, 'Repositories/foliar-cover/AKVEG_Schema_FoliarCover.csv')
taxonomy_input = os.path.join(archive_folder, '00_taxonomy.csv')
site_visit_input = os.path.join(class_folder, 'site_visits_compiled.csv')
vegetation_input = os.path.join(archive_folder, '05_vegetation_cover.csv')
abiotic_input = os.path.join(archive_folder, '06_abiotic_cover.csv')
tussock_input = os.path.join(archive_folder, '07_whole_tussock_cover.csv')
ground_input = os.path.join(archive_folder, '08_ground_cover.csv')
shrub_input = os.path.join(archive_folder, '11_shrub_structure.csv')
environment_input = os.path.join(archive_folder, '12_environment.csv')
soil_input = os.path.join(archive_folder, '13_soil_metrics.csv')

# Define output data
site_visit_output = os.path.join(class_folder, 'site_visit_type_assignments.csv')
type_summary_output = os.path.join(class_folder, 'type_count_summary.csv')
vascular_output = os.path.join(class_folder, 'veg_vascular_compiled.csv')
bryophyte_output = os.path.join(class_folder, 'veg_bryophyte_compiled.csv')
lichen_output = os.path.join(class_folder, 'veg_lichen_compiled.csv')

#### PREPARE SITE VISIT DATA
####____________________________________________________
print('Preparing site visit data...')
start_time = time.time()

# Read schema data
schema_data = pd.read_csv(schema_input)

# Read taxa data
taxa_data = pd.read_csv(taxonomy_input)
taxa_data['taxon_habit'] = taxa_data['taxon_habit'].str.lower()
taxa_data['taxon_habit'] = (taxa_data['taxon_habit']
                            .replace('dwarf shrub, shrub', 'shrub')
                            .replace('dwarf shrub, shrub, tree', 'shrub')
                            .replace('shrub, deciduous tree', 'shrub')
                            .replace('forb, dwarf shrub, shrub', 'forb')
                            .replace('forb, shrub', 'forb')
                            .replace('coniferous tree', 'needleleaf tree')
                            .replace('deciduous tree', 'broadleaf tree'))
taxon_habits = taxa_data['taxon_habit'].unique()

# Read site visit data with type assignments
site_visit_data = pd.read_csv(site_visit_input)

# Set exclusion field
site_visit_data['exclude'] = 0

# Remove invalid types from the summary data
site_visit_data['exclude'] = np.where(
    np.isin(site_visit_data['coarse_class'], ['Permanent Snow / Ice', 'Persistent Water', 'Agricultural',
                                              'Disturbed Vegetation', 'Infrastructure', 'Omit',
                                              'Recently Burned (≤ 5 Years)']),
    1, site_visit_data['exclude'])

# Exclude top cover site visits
site_visit_data['exclude'] = np.where(
    np.isin(site_visit_data['cover_type'], ['top canopy cover', 'top foliar cover']),
    1, site_visit_data['exclude'])

# Filter by taxonomic scopes
site_visit_data['exclude'] = np.where(
    ~np.isin(site_visit_data['scope_vascular'], ['exhaustive', 'non-trace species']),
    1, site_visit_data['exclude'])

# Exclude site visits sampled before 2000
site_visit_data['exclude'] = np.where(site_visit_data['observe_year'] < 2000,
                                      1, site_visit_data['exclude'])

# Exclude site visits made before burn or within 10 years post-burn
site_visit_data['exclude'] = np.where(site_visit_data['observe_year'] <= (site_visit_data['fire_year'] + 10),
                                      1, site_visit_data['exclude'])

# Exclude burned areas from non-burned types
site_visit_data['exclude'] = np.where(
    (site_visit_data['fire_year'] >= 1983) & (site_visit_data['physiography_limit'] != 'burned'),
    1, site_visit_data['exclude'])

# Exclude site visits where the centroid overlaps persistent water
site_visit_data['exclude'] = np.where((site_visit_data['esa_type'] == 80)
                                      & (site_visit_data['project_code'] != 'akveg_absences'),
                                      1, site_visit_data['exclude'])

# Exclude site visits where the plot radius is below 4 m
site_visit_data['exclude'] = np.where(site_visit_data['plot_radius_m'] < 4,
                                      1, site_visit_data['exclude'])

# Exclude earlier revisits to the most recent site visit
revisit_data = site_visit_data[site_visit_data['exclude'] == 0].copy()
site_counts = revisit_data['site_code'].value_counts()
revisit_data['total_visits'] = revisit_data['site_code'].map(site_counts)
revisit_data['observe_datetime'] = pd.to_datetime(revisit_data['observe_date'], format='%Y-%m-%d')
revisit_data = revisit_data.sort_values(by='observe_datetime')
revisit_data = revisit_data.drop_duplicates(subset=['site_code'], keep='last')
revisit_data = revisit_data.drop(columns=['observe_datetime', 'total_visits']).copy()
site_visit_data['exclude'] = np.where(
    site_visit_data['site_visit_code'].isin(revisit_data['site_visit_code'].unique()),
    site_visit_data['exclude'], 1)

# Remove exclusion sites
site_visit_data = site_visit_data[site_visit_data['exclude'] == 0]

# Create site visit list
site_visit_list = site_visit_data['site_visit_code'].unique()

# Create list of unique type codes
code_list = site_visit_data['code'].unique()
end_timing(start_time)

#### PARSE VEGETATION DATA
####------------------------------
print('Parsing vegetation data...')
start_time = time.time()

# Read vegetation data
vegetation_data = pd.read_csv(vegetation_input)
vegetation_data = vegetation_data[vegetation_data['site_visit_code'].isin(site_visit_list)]

# Enforce numeric data type
vegetation_data['cover_percent'] = pd.to_numeric(vegetation_data['cover_percent']).replace(-999, 0)

# Enforce live vegetation
vegetation_data = vegetation_data[vegetation_data['dead_status'] == False]

# Join vegetation and taxa data
vegetation_data = pd.merge(left=vegetation_data,
                           right=taxa_data,
                           left_on='name_accepted',
                           right_on='taxon_name',
                           how='left')
vegetation_data = pd.merge(left=vegetation_data,
                           right=site_visit_data,
                           on='site_visit_code',
                           how='left')

# Select vegetation data fields
vegetation_data = vegetation_data[[
    'site_visit_code', 'name_accepted', 'cover_percent', 'taxon_genus',
    'taxon_family', 'taxon_level', 'taxon_category', 'taxon_habit', 'map_class'
]]

# Filter data appropriate for vascular plant analyses
vascular_data = vegetation_data[vegetation_data['taxon_category'].isin([
    'monocot', 'eudicot', 'fern', 'gymnosperm', 'horsetail', 'lycophyte'
])]

# Identify site visits appropriate for analyses of bryophytes
bryophyte_sites = site_visit_data[
    site_visit_data['scope_bryophyte'].isin(['exhaustive', 'non-trace species', 'common species'])
]

# Identify site visits appropriate for analyses of lichens
lichen_sites = site_visit_data[
    site_visit_data['scope_lichen'].isin(['exhaustive', 'non-trace species', 'common species'])
]

# Filter data appropriate for bryophyte analyses
bryophyte_data = vegetation_data[vegetation_data['site_visit_code'].isin(
    bryophyte_sites['site_visit_code'].tolist()
)]
bryophyte_data = bryophyte_data[bryophyte_data['taxon_category'].isin([
    'liverwort', 'moss', 'hornwort', 'functional group', 'unknown'
])]
bryophyte_data = bryophyte_data[
    (~bryophyte_data['taxon_category'].isin(['functional group', 'unknown']))
    | ((bryophyte_data['taxon_category'] == 'functional group')
       & (bryophyte_data['name_accepted'].isin([
           'non-thalloid liverwort', 'thalloid liverwort', 'feathermoss (other)',
           'feathermoss (N-fixing)', 'Sphagnum moss', 'turf moss'
       ])))
    | ((bryophyte_data['taxon_category'] == 'unknown')
       & (bryophyte_data['name_accepted'].isin(['liverwort', 'moss'])))
]

# Perform bryophyte aggregation (Dynamically apply taxon_genus if it exists)
bryophyte_data['name_accepted'] = np.where(
    bryophyte_data['taxon_genus'].notna() & (bryophyte_data['taxon_genus'] != ''),
    bryophyte_data['taxon_genus'],
    bryophyte_data['name_accepted']
)

# Calculate bryophyte sums
bryophyte_data = (bryophyte_data.groupby(['site_visit_code', 'name_accepted'])['cover_percent']
                  .sum()
                  .reset_index())
bryophyte_data = pd.merge(left=bryophyte_data,
                          right=taxa_data,
                          left_on='name_accepted',
                          right_on='taxon_name',
                          how='left')
bryophyte_data = pd.merge(left=bryophyte_data,
                           right=site_visit_data,
                           on='site_visit_code',
                           how='left')
bryophyte_data = bryophyte_data[[
    'site_visit_code', 'name_accepted', 'cover_percent',
    'taxon_genus', 'taxon_level', 'taxon_category', 'taxon_habit', 'map_class'
]]

# Filter data appropriate for lichen analyses
lichen_data = vegetation_data[vegetation_data['site_visit_code'].isin(
    lichen_sites['site_visit_code'].tolist()
)]
lichen_data = lichen_data[lichen_data['taxon_category'].isin(['lichen', 'functional group', 'unknown'])]
lichen_data = lichen_data[
    (lichen_data['taxon_category'] == 'lichen')
    | ((lichen_data['taxon_category'] == 'functional group')
       & (lichen_data['name_accepted'].isin([
           'arboreal lichen', 'crustose lichen (orange)', 'crustose lichen (non-orange)',
           'foliose lichen (other)', 'foliose lichen (N-fixing)', 'forage lichen',
           'fruticose lichen (N-fixing)', 'fruticose lichen (other)'
       ])))
    | ((lichen_data['taxon_category'] == 'unknown')
       & (lichen_data['name_accepted'].isin([
           'lichen', 'crustose lichen', 'fruticose lichen', 'foliose lichen'
       ])))
]

# Perform lichen aggregation (Dynamically apply taxon_genus if it exists)
lichen_data['name_accepted'] = np.where(
    lichen_data['taxon_genus'].notna() & (lichen_data['taxon_genus'] != ''),
    lichen_data['taxon_genus'],
    lichen_data['name_accepted']
)

# Calculate lichen sums
lichen_data = (lichen_data.groupby(['site_visit_code', 'name_accepted'])['cover_percent']
               .sum()
               .reset_index())
lichen_data = pd.merge(left=lichen_data,
                       right=taxa_data,
                       left_on='name_accepted',
                       right_on='taxon_name',
                       how='left')
lichen_data = pd.merge(left=lichen_data,
                       right=site_visit_data,
                       on='site_visit_code',
                       how='left')
lichen_data = lichen_data[[
    'site_visit_code', 'name_accepted', 'cover_percent',
    'taxon_genus', 'taxon_level', 'taxon_category', 'taxon_habit', 'map_class'
]]
end_timing(start_time)

#### QUALITY CONTROL VALID SITES
####------------------------------

# Read diagnostic schema data
schema_diagnostic = pd.read_csv(diagnostic_input)[
    ['target', 'constituents']].rename(columns={'target': 'diagnostic set'}).dropna()

# Create an empty list to store the valid sites
valid_site_list = []
start_time = time.time()

# Process site visits for each type
for type_code in code_list:
    # Identify type name and structural class
    type_name = schema_data.loc[schema_data['code'] == type_code, 'map_class'].item()
    struc_class = schema_data.loc[schema_data['code'] == type_code, 'structural_class'].item()

    # Isolate data for type
    type_data = site_visit_data[site_visit_data['code'] == type_code].copy()
    type_site_list = type_data['site_visit_code'].unique()

    # Subset data to type site visit list
    print(f'Summarizing data for {type_name} ({len(type_data)} site visits)...')
    vegetation_type = vegetation_data[vegetation_data['site_visit_code'].isin(type_site_list)]
    vascular_type = vascular_data[vascular_data['site_visit_code'].isin(type_site_list)]
    bryophyte_type = bryophyte_data[bryophyte_data['site_visit_code'].isin(type_site_list)]
    lichen_type = lichen_data[lichen_data['site_visit_code'].isin(type_site_list)]

    # Join diagnostic schema to vascular data
    diagnostic_vascular = pd.merge(left=vascular_type,
                                   right=schema_diagnostic,
                                   left_on='name_accepted',
                                   right_on='constituents',
                                   how='inner')
    diagnostic_vascular = (diagnostic_vascular
                           .groupby(['site_visit_code', 'diagnostic set'])['cover_percent']
                           .sum()
                           .to_frame()
                           .reset_index())

    # Join diagnostic schema to bryophyte data
    diagnostic_bryophyte = pd.merge(left=bryophyte_type,
                                    right=schema_diagnostic,
                                    left_on='name_accepted',
                                    right_on='constituents',
                                    how='inner')
    diagnostic_bryophyte = (diagnostic_bryophyte
                            .groupby(['site_visit_code', 'diagnostic set'])['cover_percent']
                            .sum()
                            .to_frame()
                            .reset_index())

    # Quality control for barren types
    if struc_class == 'Barren':
        total_veg_cover = vegetation_type.groupby('site_visit_code')['cover_percent'].sum()
        invalid_sites = set(total_veg_cover[total_veg_cover >= 30].index)
        type_site_list = [site for site in type_site_list if site not in invalid_sites]

    # Quality control for beach types
    if struc_class == 'Beach':
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Beach Herbaceous']
        valid_sites = qc_data[qc_data['cover_percent'] >= 3]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for broadleaf woodland
    if struc_class == 'Broadleaf Woodland':
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Broadleaf Trees']
        valid_sites = qc_data[qc_data['cover_percent'] >= 8]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for broadleaf forest
    if struc_class == 'Broadleaf Forest':
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Broadleaf Trees']
        valid_sites = qc_data[qc_data['cover_percent'] >= 25]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for freshwater marsh
    if struc_class == 'Freshwater Marsh':
        total_bryo_cover = bryophyte_type.groupby('site_visit_code')['cover_percent'].sum()
        invalid_sites = set(total_bryo_cover[total_bryo_cover >= 12].index)
        type_site_list = [site for site in type_site_list if site not in invalid_sites]

    # Quality control for graminoid wetland
    if struc_class == 'Graminoid Wetland':
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Graminoids']
        valid_sites = qc_data[qc_data['cover_percent'] >= 8]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for herbaceous
    if (struc_class == 'Herbaceous') | (struc_class == 'Graminoid Wetland'):
        woody_data = vegetation_type[vegetation_type['taxon_habit'].isin([
            'tree', 'needleleaf tree', 'broadleaf tree', 'shrub', 'dwarf shrub'
        ])]
        total_woody_cover = woody_data.groupby('site_visit_code')['cover_percent'].sum()
        invalid_sites = set(total_woody_cover[total_woody_cover >= 20].index)
        type_site_list = [site for site in type_site_list if site not in invalid_sites]

    # Quality control for mixed forest
    if struc_class == 'Mixed Forest':
        needleleaf_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Needleleaf Trees']
        broadleaf_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Broadleaf Trees']
        needleleaf_sites = needleleaf_data[needleleaf_data['cover_percent'] >= 12]['site_visit_code'].unique()
        broadleaf_sites = broadleaf_data[broadleaf_data['cover_percent'] >= 12]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if (site in needleleaf_sites) & (site in broadleaf_sites)]

    # Quality control for needleleaf woodland
    if struc_class == 'Needleleaf Woodland':
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Needleleaf Trees']
        valid_sites = qc_data[qc_data['cover_percent'] >= 5]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for needleleaf forest
    if struc_class == 'Needleleaf Forest':
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Needleleaf Trees']
        valid_sites = qc_data[qc_data['cover_percent'] >= 25]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for mixed spruce
    if 'Mixed Spruce' in type_name:
        picmar_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Black Spruce']
        picgla_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'White Spruce']
        picmar_sites = picmar_data[picmar_data['cover_percent'] >= 4]['site_visit_code'].unique()
        picgla_sites = picgla_data[picgla_data['cover_percent'] >= 4]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if (site in picmar_sites) & (site in picgla_sites)]

    # Quality control for salt marsh
    if struc_class == 'Salt Marsh':
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Halophytic Graminoids']
        valid_sites = qc_data[qc_data['cover_percent'] >= 4]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for sphagnum peatland
    if struc_class == 'Sphagnum Peatland':
        bryo_sites = set(diagnostic_bryophyte['site_visit_code'].unique())
        qc_data = diagnostic_bryophyte[diagnostic_bryophyte['diagnostic set'] == 'Sphagnum']
        valid_sites = set(qc_data[qc_data['cover_percent'] >= 8]['site_visit_code'].unique())
        type_site_list = [site for site in type_site_list if (site not in bryo_sites) or (site in valid_sites)]

    # Quality control for minerotrophic peatland
    if 'Minerotrophic' in type_name:
        qc_data = diagnostic_bryophyte[diagnostic_bryophyte['diagnostic set'] == 'Sphagnum']
        invalid_sites = set(qc_data[qc_data['cover_percent'] >= 8]['site_visit_code'].unique())
        type_site_list = [site for site in type_site_list if site not in invalid_sites]

    # Quality control for aspen
    if 'Aspen' in type_name:
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Aspen']
        valid_sites = qc_data[qc_data['cover_percent'] >= 4]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for birch forest
    if ('Birch' in type_name) & ('Forest' in type_name):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Birch Trees']
        valid_sites = qc_data[qc_data['cover_percent'] >= 4]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for poplar/cottonwood
    if ('Poplar' in type_name) | ('Cottonwood' in type_name):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Poplar and Cottonwood']
        valid_sites = qc_data[qc_data['cover_percent'] >= 4]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for shore pine
    if 'Shore Pine' in type_name:
        picsit_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Sitka Spruce']
        pincon_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Shore Pine']
        picsit_sites = picsit_data[picsit_data['cover_percent'] >= 3]['site_visit_code'].unique()
        pincon_sites = pincon_data[pincon_data['cover_percent'] >= 3]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if (site in picsit_sites) | (site in pincon_sites)]

    # Quality control for Sitka spruce
    if ('Sitka Spruce' in type_name) & ('(-Sitka Spruce)' not in type_name):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Sitka Spruce']
        valid_sites = qc_data[qc_data['cover_percent'] >= 3]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for white spruce
    if ('White Spruce' in type_name) & ('(-White Spruce)' not in type_name):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'White Spruce']
        valid_sites = qc_data[qc_data['cover_percent'] >= 3]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for black spruce
    if ('Black Spruce' in type_name) & ('(-Black Spruce)' not in type_name):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Black Spruce']
        valid_sites = qc_data[qc_data['cover_percent'] >= 3]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for western hemlock
    if (('Western Hemlock' in type_name)
            & ('(-Western Hemlock)' not in type_name)
            & ('(-Western Hemlock / Mountain Hemlock)' not in type_name)):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Western Hemlock']
        valid_sites = qc_data[qc_data['cover_percent'] >= 3]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for mountain hemlock
    if (('Mountain Hemlock' in type_name)
            & ('(-Mountain Hemlock)' not in type_name)
            & ('(-Western Hemlock / Mountain Hemlock)' not in type_name)):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Mountain Hemlock']
        valid_sites = qc_data[qc_data['cover_percent'] >= 3]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control Alaska Pacific Mountain Hemlock-Sitka/Lutz Spruce Forest Mesic
    if type_name == 'Alaska Pacific Mountain Hemlock-Sitka/Lutz Spruce Forest Mesic':
        picsit_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Sitka Spruce']
        picgla_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'White Spruce']
        picsit_sites = picsit_data[picsit_data['cover_percent'] >= 3]['site_visit_code'].unique()
        picgla_sites = picgla_data[picgla_data['cover_percent'] >= 3]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if (site in picsit_sites) | (site in picgla_sites)]

    # Quality control for fir trees
    if 'Fir' in type_name:
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Fir Trees']
        valid_sites = qc_data[qc_data['cover_percent'] >= 3]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for Alaska yellow cedar
    if 'Yellow Cedar' in type_name:
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Alaska Yellow Cedar']
        valid_sites = qc_data[qc_data['cover_percent'] >= 3]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for tamarack
    if 'Tamarack' in type_name:
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Tamarack']
        valid_sites = qc_data[qc_data['cover_percent'] >= 3]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for birch shrubs
    if (('Birch' in type_name)
            & ('(-Birch)' not in type_name)
            & ('Forest' not in type_name)
            & ('Woodland' not in type_name)
            & ('Post-burn' not in type_name)):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Birch Shrubs']
        valid_sites = qc_data[qc_data['cover_percent'] >= 5]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for willow shrubs
    if (('Willow' in type_name)
            & ('(-Willow)' not in type_name)
            & ('(-Willow-Ericaceous)' not in type_name)
            & ('Dwarf' not in type_name)
            & ('Dune' not in type_name)
            & ('Post-burn' not in type_name)):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Willow Shrubs']
        valid_sites = qc_data[qc_data['cover_percent'] >= 5]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for alder
    if ('Alder' in type_name) & ('(-Alder)' not in type_name):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Alder Shrubs']
        valid_sites = qc_data[qc_data['cover_percent'] >= 5]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for salmonberry
    if ('Salmonberry' in type_name) & ('(-Salmonberry)' not in type_name):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Salmonberry']
        valid_sites = qc_data[qc_data['cover_percent'] >= 5]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for ericaceous shrubs
    if (('Ericaceous' in type_name)
            & ('(-Ericaceous)' not in type_name)
            & ('Lichen' not in type_name)
            & ('(-Willow-Ericaceous)' not in type_name)):
        total_eric_data = vegetation_type[vegetation_type['taxon_family'] == 'Ericaceae']
        total_eric_cover = total_eric_data.groupby('site_visit_code')['cover_percent'].sum()
        valid_sites = total_eric_cover[total_eric_cover >= 5].index
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for Dryas dwarf shrubs
    if ('Dryas' in type_name) & ('(-Dryas)' not in type_name):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Dryas Dwarf Shrubs']
        valid_sites = qc_data[qc_data['cover_percent'] >= 5]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for willow dwarf shrubs
    if (('Willow' in type_name)
            & ('(-Willow)' not in type_name)
            & ('(-Willow-Ericaceous)' not in type_name)
            & ('Dwarf' in type_name)
            & ('Dune' not in type_name)):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Willow Dwarf Shrubs']
        valid_sites = qc_data[qc_data['cover_percent'] >= 5]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for tussock
    if ('Tussock' in type_name) & ('Non-Tussock' not in type_name):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Tussock Cottongrass']
        valid_sites = qc_data[qc_data['cover_percent'] >= 5]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for wetland sedges
    if (('Sedge' in type_name) & ('Wet' in type_name)):
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Wetland Sedges']
        valid_sites = qc_data[qc_data['cover_percent'] >= 5]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for Calamagrostis
    if 'Calamagrostis' in type_name:
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Mesic-wet Calamagrostis']
        valid_sites = qc_data[qc_data['cover_percent'] >= 5]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for forb
    if 'Forb' in type_name:
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Forbs']
        valid_sites = qc_data[qc_data['cover_percent'] >= 5]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Quality control for graminoid
    if 'Graminoid' in type_name:
        qc_data = diagnostic_vascular[diagnostic_vascular['diagnostic set'] == 'Graminoids']
        valid_sites = qc_data[qc_data['cover_percent'] >= 5]['site_visit_code'].unique()
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Append the valid sites to list
    valid_site_list.extend(type_site_list)

# Subset the valid sites
qc_site_visit_data = site_visit_data[site_visit_data['site_visit_code'].isin(valid_site_list)]

# Summarize final site_visit_code counts for each map_class in schema_data
original_counts = (site_visit_data.groupby('code')['site_visit_code']
                   .nunique()
                   .reset_index(name='original_n'))
qc_counts = (qc_site_visit_data.groupby('code')['site_visit_code']
             .nunique()
             .reset_index(name='qc_n'))
type_summary = pd.merge(left=schema_data[['code', 'map_class']],
                        right=original_counts,
                        on='code',
                        how='left')
type_summary = pd.merge(left=type_summary,
                        right=qc_counts,
                        on='code',
                        how='left').sort_values(by='code')
type_summary['original_n'] = type_summary['original_n'].fillna(0).astype(int)
type_summary['qc_n'] = type_summary['qc_n'].fillna(0).astype(int)

# Export compiled data to csv
qc_site_visit_data.to_csv(site_visit_output, header=True, index=False, sep=',', encoding='utf-8')
type_summary.to_csv(type_summary_output, header=True, index=False, sep=',', encoding='utf-8')
vascular_data.to_csv(vascular_output, header=True, index=False, sep=',', encoding='utf-8')
bryophyte_data.to_csv(bryophyte_output, header=True, index=False, sep=',', encoding='utf-8')
lichen_data.to_csv(lichen_output, header=True, index=False, sep=',', encoding='utf-8')
end_timing(start_time)
