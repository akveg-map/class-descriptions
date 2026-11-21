# ---------------------------------------------------------------------------
# Parse summary data
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-11-19
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Parse summary data" creates summary tables and plots for the type descriptions.
# ---------------------------------------------------------------------------

# Import libraries
import os
import time
import string
import numpy as np
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
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
output_folder = os.path.join(repository_folder, '03_summary_data')
site_geopackage = os.path.join(archive_folder, '03_site_visit_3338.gpkg')

# Define input data
schema_input = os.path.join(repository_folder, 'AKVEG_MapClass_Schema.csv')
diagnostic_input = os.path.join(drive, root_folder, 'Repositories/foliar-cover/AKVEG_Schema_FoliarCover.csv')
taxonomy_input = os.path.join(archive_folder, '00_taxonomy.csv')
site_visit_layer = 'site_visits_all_types_20261116'
vegetation_input = os.path.join(archive_folder, '05_vegetation_cover.csv')
abiotic_input = os.path.join(archive_folder, '06_abiotic_cover.csv')
tussock_input = os.path.join(archive_folder, '07_whole_tussock_cover.csv')
ground_input = os.path.join(archive_folder, '08_ground_cover.csv')
shrub_input = os.path.join(archive_folder, '11_shrub_structure.csv')
environment_input = os.path.join(archive_folder, '12_environment.csv')
soil_input = os.path.join(archive_folder, '13_soil_metrics.csv')

# Define output data
site_visit_output = os.path.join(output_folder, '000_site_visit_summary.xlsx')

#### DEFINE FUNCTIONS
####------------------------------

# Define 10th percentile
def percentile_10(x):
    return x.quantile(0.10)

# Define 25th percentile
def percentile_25(x):
    return x.quantile(0.25)

# Define 75th percentile
def percentile_75(x):
    return x.quantile(0.75)

# Define 90th percentile
def percentile_90(x):
    return x.quantile(0.90)

#### PREPARE SITE VISIT DATA
####____________________________________________________
print('Preparing site visit data...')
start_time = time.time()

# Read schema data
schema_data = pd.read_csv(schema_input)

# Read site visit data with type assignments
site_visit_data = gpd.read_file(site_geopackage, layer=site_visit_layer)

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

#### READ AKVEG DATA
####------------------------------
print('Reading AKVEG data tables...')
start_time = time.time()

# Read taxa data
taxa_data = pd.read_csv(taxonomy_input)

# Read abiotic top cover data
abiotic_data = pd.read_csv(abiotic_input)
abiotic_data = abiotic_data[abiotic_data['site_visit_code'].isin(site_visit_list)]
abiotic_data['abiotic_top_cover_percent'] = pd.to_numeric(abiotic_data['abiotic_top_cover_percent'])

# Read tussock data
tussock_data = pd.read_csv(tussock_input)
tussock_data = tussock_data[tussock_data['site_visit_code'].isin(site_visit_list)]
tussock_data = tussock_data[tussock_data['cover_percent'] != -999]

# Read ground cover data
ground_data = pd.read_csv(ground_input)
ground_data = ground_data[ground_data['site_visit_code'].isin(site_visit_list)]

# Read shrub structure data
shrub_data = pd.read_csv(shrub_input)
shrub_data = shrub_data[shrub_data['site_visit_code'].isin(site_visit_list)]
shrub_data = shrub_data[shrub_data['height_cm'] != -999]

# Read environment data
environment_data = pd.read_csv(environment_input)
environment_data = environment_data[environment_data['site_visit_code'].isin(site_visit_list)]

# Read soil metrics data
soil_data = pd.read_csv(soil_input)
soil_data = soil_data[soil_data['site_visit_code'].isin(site_visit_list)]
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

# Select vegetation data fields
vegetation_data = vegetation_data[[
    'site_visit_code', 'name_accepted', 'cover_percent',
    'taxon_genus', 'taxon_level', 'taxon_category', 'taxon_habit'
]]

# Correct ambiguous taxon habits
vegetation_data = (vegetation_data
                   .replace('dwarf shrub, shrub', 'shrub')
                   .replace('dwarf shrub, shrub, tree', 'shrub')
                   .replace('shrub, deciduous tree', 'shrub')
                   .replace('forb, dwarf shrub, shrub', 'forb')
                   .replace('forb, shrub', 'forb'))
taxon_habits = vegetation_data['taxon_habit'].unique()

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
bryophyte_data = bryophyte_data[(bryophyte_data['taxon_category'] != 'functional group')
                                | ((bryophyte_data['taxon_category'] != 'functional group')
                                   & (bryophyte_data['name_accepted'].isin([
            'non-thalloid liverwort', 'thalloid liverwort', 'feathermoss (other)',
            'feathermoss (N-fixing)', 'Sphagnum moss', 'turf moss'
        ])))
                                | ((bryophyte_data['taxon_category'] != 'unknown')
                                   & (bryophyte_data['name_accepted'].isin([
            'liverwort', 'moss'
        ])))]

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
bryophyte_data = bryophyte_data[[
    'site_visit_code', 'name_accepted', 'cover_percent',
    'taxon_genus', 'taxon_level', 'taxon_category', 'taxon_habit'
]]

# Filter data appropriate for lichen analyses
lichen_data = vegetation_data[vegetation_data['site_visit_code'].isin(
    lichen_sites['site_visit_code'].tolist()
)]
lichen_data = lichen_data[lichen_data['taxon_category'] == 'lichen']
lichen_data = lichen_data[(lichen_data['taxon_category'] != 'functional group')
                          | ((lichen_data['taxon_category'] != 'functional group')
                             & (lichen_data['name_accepted'].isin([
            'arboreal lichen', 'crustose lichen (orange)', 'crustose lichen (non-orange)',
            'foliose lichen (other)', 'foliose lichen (N-fixing)', 'forage lichen',
            'fruticose lichen (N-fixing)', 'fruticose lichen (other)'
        ])))
                          | ((lichen_data['taxon_category'] != 'unknown')
                             & (lichen_data['name_accepted'].isin([
            'lichen', 'crustose lichen', 'fruticose lichen', 'foliose lichen'
        ])))]

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
lichen_data = lichen_data[[
    'site_visit_code', 'name_accepted', 'cover_percent',
    'taxon_genus', 'taxon_level', 'taxon_category', 'taxon_habit'
]]
end_timing(start_time)

#### SUMMARIZE DATA PER TYPE
####------------------------------

# Summarize unique site visits per type code
site_visit_summary = (site_visit_data.groupby('code')['site_visit_code']
                      .nunique()
                      .reset_index()
                      .rename(columns={'site_visit_code': 'count'}))

# Add the map_class to the summary dataframe
site_visit_summary = pd.merge(left=site_visit_summary,
                              right=schema_data[['code', 'map_class']],
                              on='code',
                              how='left')

# Export summary table
site_visit_summary = site_visit_summary.sort_values(by='count')
site_visit_summary.to_excel(site_visit_output, sheet_name='site_visit_count', index=False)


# Create a translation table that maps punctuation and whitespace to none for removal
remove_chars = string.punctuation + string.whitespace
translator = str.maketrans('', '', remove_chars)

# Produce summary data for each type
for type_code in code_list:
    # Identify type name
    type_name = schema_data.loc[schema_data['code'] == type_code, 'map_class'].item()
    type_prefix = f'{str(type_code)}_{type_name.translate(translator)}'
    start_time = time.time()

    # Isolate data for type
    type_data = site_visit_data[site_visit_data['code'] == type_code].copy()
    type_site_list = type_data['site_visit_code'].unique()

    # Skip summary if less than 5 sites are registered to the type
    if len(type_data) < 5:
        print(f'Too few site visits to summarize for {type_name}.')
        output_file = os.path.join(output_folder, f'{type_prefix}_BelowMinimumSites.txt')
        with open(output_file, 'a'):
            pass
        end_timing(start_time)
        continue

    # Remove vegetated sites from barren types
    coarse_class = schema_data.loc[schema_data['code'] == type_code, 'coarse_class'].item()
    vegetation_type = vegetation_data[vegetation_data['site_visit_code'].isin(type_site_list)]
    if coarse_class == 'Barren':
        # Sum total vegetation cover across all taxa for each site visit
        site_cover_totals = vegetation_type.groupby('site_visit_code')['cover_percent'].sum()
        # Identify valid barren sites (total vegetation cover < 20)
        valid_sites = site_cover_totals[site_cover_totals < 20].index
        # Remove mislocated sites from type_site_list
        type_site_list = [site for site in type_site_list if site in valid_sites]

    # Subset data to type site visit list
    print(f'Summarizing data for {type_name} ({len(type_data)} site visits)...')
    vascular_type = vascular_data[vascular_data['site_visit_code'].isin(type_site_list)]
    bryophyte_type = bryophyte_data[bryophyte_data['site_visit_code'].isin(type_site_list)]
    lichen_type = lichen_data[lichen_data['site_visit_code'].isin(type_site_list)]
    abiotic_type = abiotic_data[abiotic_data['site_visit_code'].isin(type_site_list)]
    tussock_type = tussock_data[tussock_data['site_visit_code'].isin(type_site_list)]
    ground_type = ground_data[ground_data['site_visit_code'].isin(type_site_list)]
    shrub_type = shrub_data[shrub_data['site_visit_code'].isin(type_site_list)]
    environment_type = environment_data[environment_data['site_visit_code'].isin(type_site_list)]
    soil_type = soil_data[soil_data['site_visit_code'].isin(type_site_list)]
    
    #### PROCESS STRUCTURAL COVER
    ####____________________________________________________

    # Calculate vascular structure
    if len(vascular_type) >= 5:
        structure_vascular = (vascular_type
                              # Calculate pivot table to sum taxon habit cover while filling zeros
                              .pivot_table(index='site_visit_code',
                                           columns='taxon_habit',
                                           values='cover_percent',
                                           aggfunc='sum',
                                           fill_value=0)
                              # Calculate mean cover by taxon habit
                              .mean()
                              .to_frame(name='mean')
                              .rename(columns={'taxon_habit': 'structure'}))
    else:
        # Fill table with -999 to represent no data
        structure_vascular = pd.DataFrame({'mean': [-999]}, index=['Vascular'])

    # Calculate bryophyte structure
    if len(bryophyte_type) >= 5:
        structure_bryophyte = (bryophyte_type
                               # Calculate pivot table to sum taxon habit cover while filling zeros
                               .pivot_table(index='site_visit_code',
                                            columns='taxon_habit',
                                            values='cover_percent',
                                            aggfunc='sum',
                                            fill_value=0)
                               # Calculate mean cover by taxon habit
                               .mean()
                               .to_frame(name='mean')
                               .rename(columns={'taxon_habit': 'structure'}))
    else:
        # Fill table with -999 to represent no data
        structure_bryophyte = pd.DataFrame({'mean': [-999]}, index=['Bryophyte'])

    # Calculate lichen structure
    if len(lichen_type) >= 5:
        structure_lichen = (lichen_type
                            # Calculate pivot table to sum taxon habit cover while filling zeros
                            .pivot_table(index='site_visit_code',
                                         columns='taxon_habit',
                                         values='cover_percent',
                                         aggfunc='sum',
                                         fill_value=0)
                            # Calculate mean cover by taxon habit
                            .mean()
                            .to_frame(name='mean')
                            .rename(columns={'taxon_habit': 'structure'}))
    else:
        # Fill table with -999 to represent no data
        structure_lichen = pd.DataFrame({'mean': [-999]}, index=['Lichen'])

    # Concatenate biotic structure
    structure_biotic = pd.concat([structure_vascular, structure_bryophyte, structure_lichen], axis=0)

    # Calculate biotic sum
    biotic_sum = structure_biotic[structure_biotic['mean'] != -999]['mean'].sum()
    abiotic_remainder = 100 - biotic_sum if biotic_sum < 100 else 0

    # Calculate abiotic top cover mean
    structure_abiotic = (abiotic_type.groupby('abiotic_element')['abiotic_top_cover_percent']
                         .mean()
                         .to_frame(name='mean')
                         .rename(columns={'abiotic_element': 'structure'}))

    # Rescale abiotic top cover data
    abiotic_sum = structure_abiotic['mean'].sum()
    if abiotic_sum > 0:
        abiotic_adjustment = abiotic_remainder / abiotic_sum
        structure_abiotic['mean'] = structure_abiotic['mean'] * abiotic_adjustment
    else:
        structure_abiotic['mean'] = 0

    # Concatenate rows from structure and abiotic summary tables
    structure_summary = (pd.concat([structure_biotic, structure_abiotic], axis=0)
                         .round(1))

    # Remove zero and low values
    structure_summary = (structure_summary[structure_summary['mean'] >= 1]
                         .reset_index()
                         .rename(columns={'index': 'structure'}))
    structure_summary = structure_summary[['structure', 'mean']]
    structure_summary['structure'] = (structure_summary['structure']
                                  .str.title()
                                  .replace('Spore-Bearing', 'Spore-bearing'))

    # Define standard element colors
    structure_colors = {
        'Coniferous Tree': '#346429',
        'Broadleaf Tree': '#87C58F',
        'Shrub': '#6A1837',
        'Dwarf Shrub': '#466F81',
        'Graminoid': '#DF9E9E',
        'Forb': '#C5BCD5',
        'Spore-bearing': '#B6BF8C',
        'Moss': '#59C8A8',
        'Liverwort': '#C8F1E5',
        'Lichen': '#FFFFBE',
        'Water': '#BEE8FF',
        'Litter (< 2mm)': '#CDAA66',
        'Dead Standing Woody Vegetation': '#897044',
        'Soil': '#828282'
    }

    # Create structure treemap plot
    structure_plot = px.treemap(
        structure_summary,
        path=['structure'],
        values='mean',
        color='structure',
        color_discrete_map=structure_colors
    )

    # Update plot formatting
    structure_plot.update_traces(
        # Increase label font size
        textfont=dict(size=18),
        # Restrict hover to show only the label and the mean value (formatted)
        hovertemplate='<b>%{label}</b><br>Mean: %{value:.1f}%<extra></extra>'
    )

    # Update layout for margins and dimensions
    structure_plot.update_layout(
        margin=dict(t=0, l=0, r=0, b=0),
        autosize=True,
        width=None,
        height=400
    )

    # Export to HTML (interactive) and PNG (publication)
    structure_output = os.path.join(output_folder, type_prefix + '_Structure.html')
    structure_plot.write_html(structure_output, config={'responsive': True})

    #### PROCESS DIAGNOSTIC SPECIES SETS
    ####____________________________________________________

    # Read diagnostic schema data
    schema_diagnostic = pd.read_csv(diagnostic_input)[
        ['target', 'constituents']].rename(columns={'target': 'diagnostic set'}).dropna()

    # Remove non-diagnostic sets
    schema_diagnostic = schema_diagnostic[~schema_diagnostic['diagnostic set'].isin([
        'Broadleaf Trees', 'Needleleaf Trees', 'Bare Ground', 'Peak Growing Season Sub-canopy Surface Water'
    ])]

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

    # Calculate diagnostic constancy for vascular plants
    constancy_diagnostic_vasc = (diagnostic_vascular['diagnostic set']
                                 .value_counts()
                                 .to_frame()
                                 .rename(columns={'count': 'occurrences'}))
    if len(diagnostic_vascular['site_visit_code'].unique()) > 0:
        constancy_diagnostic_vasc['constancy'] = (constancy_diagnostic_vasc['occurrences']
                                              / len(diagnostic_vascular['site_visit_code'].unique())) * 100
    else:
        constancy_diagnostic_vasc['constancy'] = 0

    # Calculate diagnostic constancy for bryophytes
    constancy_diagnostic_bryo = (diagnostic_bryophyte['diagnostic set']
                                 .value_counts()
                                 .to_frame()
                                 .rename(columns={'count': 'occurrences'}))
    if len(diagnostic_bryophyte['site_visit_code'].unique()) > 0:
        constancy_diagnostic_bryo['constancy'] = (constancy_diagnostic_bryo['occurrences']
                                              / len(diagnostic_bryophyte['site_visit_code'].unique())) * 100
    else:
        constancy_diagnostic_bryo['constancy'] = 0

    # Concatenate constancy tables
    constancy_diagnostic = pd.concat([constancy_diagnostic_vasc.reset_index(),
                                      constancy_diagnostic_bryo.reset_index()], axis=0)

    # Summarize diagnostic sets for vascular plants
    if not diagnostic_vascular.empty:
        cover_diagnostic_vasc = (diagnostic_vascular
                                 # Calculate pivot table to sum cover while filling zeros
                                 .pivot_table(index='site_visit_code',
                                              columns='diagnostic set',
                                              values='cover_percent',
                                              aggfunc='sum',
                                              fill_value=0)
                                 .agg(['mean',
                                       'std',
                                       'median',
                                       'min',
                                       'max',
                                       percentile_10,
                                       percentile_25,
                                       percentile_75,
                                       percentile_90])
                                 .transpose())
    else:
        cover_diagnostic_vasc = pd.DataFrame()

    # Summarize diagnostic sets for bryophytes
    if not diagnostic_bryophyte.empty:
        cover_diagnostic_bryo = (diagnostic_bryophyte
                                 # Calculate pivot table to sum cover while filling zeros
                                 .pivot_table(index='site_visit_code',
                                              columns='diagnostic set',
                                              values='cover_percent',
                                              aggfunc='sum',
                                              fill_value=0)
                                 .agg(['mean',
                                       'std',
                                       'median',
                                       'min',
                                       'max',
                                       percentile_10,
                                       percentile_25,
                                       percentile_75,
                                       percentile_90])
                                 .transpose())
    else:
        cover_diagnostic_bryo = pd.DataFrame()

    # Concatenate cover tables
    cover_diagnostic = pd.concat([cover_diagnostic_vasc, cover_diagnostic_bryo], axis=0)

    # Join constancy and cover data
    if not cover_diagnostic.empty and not constancy_diagnostic.empty:
        # Join diagnostic data
        stats_diagnostic = (pd.merge(left=constancy_diagnostic.reset_index(drop=True),
                                     right=cover_diagnostic.reset_index(),
                                     on='diagnostic set',
                                     how='left')
                            .round(1)
                            .rename(columns={'percentile_10': '10th percentile',
                                             'percentile_25': '25th percentile',
                                             'percentile_75': '75th percentile',
                                             'percentile_90': '90th percentile'}))

        # Filter floristic data for constancy and mean cover limits
        stats_diagnostic = stats_diagnostic[(stats_diagnostic['75th percentile'] >= 1)
                                            & (((stats_diagnostic['constancy'] >= 25)
                                                & (stats_diagnostic['mean'] >= 2))
                                               | ((stats_diagnostic['constancy'] >= 50)
                                                  & (stats_diagnostic['mean'] >= 1)))]
        stats_diagnostic = stats_diagnostic.sort_values(by=['constancy', 'mean'], ascending=True)

        # Calculate range
        stats_diagnostic['range_width'] = stats_diagnostic['75th percentile'] - stats_diagnostic['25th percentile']

        # Create custom data array
        custom_diagnostic = np.stack([stats_diagnostic['constancy'], stats_diagnostic['75th percentile']], axis=-1)

        # Calculate plot height
        height_diagnostic = 50 * len(stats_diagnostic) if len(stats_diagnostic) > 0 else 100

        # Create diagnostic set constancy and cover plot
        diagnostic_plot = go.Figure()
        if not stats_diagnostic.empty:
            diagnostic_plot.add_trace(go.Bar(
                y=stats_diagnostic['diagnostic set'],
                x=stats_diagnostic['range_width'],
                base=stats_diagnostic['25th percentile'],
                orientation='h',
                width=0.4,
                name='25th-75th Range',
                marker=dict(
                    color=stats_diagnostic['constancy'],
                    colorscale='Viridis',
                    colorbar=dict(title='Constancy'),
                    line=dict(width=0)
                ),
                showlegend=True,
                customdata=custom_diagnostic,
                hovertemplate='%{y}<br>Constancy: %{customdata[0]}%<br>25th Percentile: %{base}%<br>75th Percentile: %{customdata[1]}%<extra></extra>'
            ))

            # Add scatterplot for means
            diagnostic_plot.add_trace(go.Scatter(
                y=stats_diagnostic['diagnostic set'],
                x=stats_diagnostic['mean'],
                mode='markers',
                name='Mean',
                marker=dict(
                    color='black',
                    size=20,
                    symbol='line-ns-open',
                    line=dict(width=2)
                ),
                hovertemplate='%{y}<br>Mean Cover: %{x}%<extra></extra>',
            ))

        # Update Layout
        diagnostic_plot.update_layout(
            # title='Cover Range 25th to 75th Percentile',
            xaxis_title='Cover Value (%)',
            yaxis_title='Taxon/Set',
            height=height_diagnostic,
            margin=dict(l=10, r=10, t=80, b=80),
            template='plotly_white',
            showlegend=False,
            font=dict(size=18),
            xaxis=dict(
                showline=True,
                linecolor='black',
                linewidth=1,
                ticks='outside',
                ticklen=6,
                showgrid=True,
                gridcolor='lightgrey'
            ),
            legend=dict(
                yanchor="bottom",
                y=0.02,
                xanchor="right",
                x=0.98,
                bgcolor="rgba(255,255,255,0.8)"
            )
        )

        # Update layout for margins and dimensions
        diagnostic_plot.update_layout(
            margin=dict(t=0, l=0, r=0, b=0),
            autosize=True,
            width=None,
            height=height_diagnostic
        )

        # Export to HTML (interactive) and PNG (publication)
        diagnostic_output = os.path.join(output_folder, type_prefix + '_DiagnosticSets.html')
        diagnostic_plot.write_html(diagnostic_output, config={'responsive': True})
    continue

    #### PROCESS SPECIES COMPOSITION
    ####____________________________________________________

    # Calculate vascular constancy
    constancy_vascular = (vascular_type['name_accepted']
                      .value_counts()
                      .to_frame()
                      .rename(columns={'count': 'occurrences'}))
    if len(vascular_type['site_visit_code'].unique()) > 0:
        constancy_vascular['constancy'] = (constancy_vascular['occurrences']
                                       / len(vascular_type['site_visit_code'].unique())) * 100
    else:
        constancy_vascular['constancy'] = 0

    # Calculate bryophyte constancy
    constancy_bryophyte = (bryophyte_type['name_accepted']
                       .value_counts()
                       .to_frame()
                       .rename(columns={'count': 'occurrences'}))
    if len(bryophyte_type['site_visit_code'].unique()) > 0:
        constancy_bryophyte['constancy'] = (constancy_bryophyte['occurrences']
                                        / len(bryophyte_type['site_visit_code'].unique())) * 100
    else:
        constancy_bryophyte['constancy'] = 0

    # Calculate lichen constancy
    constancy_lichen = (lichen_type['name_accepted']
                    .value_counts()
                    .to_frame()
                    .rename(columns={'count': 'occurrences'}))
    if len(lichen_type['site_visit_code'].unique()) > 0:
        constancy_lichen['constancy'] = (constancy_lichen['occurrences']
                                     / len(lichen_type['site_visit_code'].unique())) * 100
    else:
        constancy_lichen['constancy'] = 0

    # Concatenate constancy tables
    constancy_composition = pd.concat([constancy_vascular.reset_index(),
                                   constancy_bryophyte.reset_index(),
                                   constancy_lichen.reset_index()], axis=0)

    # Calculate vascular cover statistics
    if not vascular_type.empty:
        cover_vascular = (vascular_type
                      # Calculate pivot table to sum cover while filling zeros
                      .pivot_table(index='site_visit_code',
                                   columns='name_accepted',
                                   values='cover_percent',
                                   aggfunc='sum',
                                   fill_value=0)
                      .agg(['mean',
                            'std',
                            'median',
                            'min',
                            'max',
                            percentile_10,
                            percentile_25,
                            percentile_75,
                            percentile_90])
                      .transpose()
                      )
    else:
        cover_vascular = pd.DataFrame()

    # Calculate bryophyte cover statistics
    if not bryophyte_type.empty:
        cover_bryophyte = (bryophyte_type
                       # Calculate pivot table to sum cover while filling zeros
                       .pivot_table(index='site_visit_code',
                                    columns='name_accepted',
                                    values='cover_percent',
                                    aggfunc='sum',
                                    fill_value=0)
                       .agg(['mean',
                             'std',
                             'median',
                             'min',
                             'max',
                             percentile_10,
                             percentile_25,
                             percentile_75,
                             percentile_90])
                       .transpose()
                       )
    else:
        cover_bryophyte = pd.DataFrame()

    # Calculate lichen cover statistics
    if not lichen_type.empty:
        cover_lichen = (lichen_type
                    # Calculate pivot table to sum cover while filling zeros
                    .pivot_table(index='site_visit_code',
                                 columns='name_accepted',
                                 values='cover_percent',
                                 aggfunc='sum',
                                 fill_value=0)
                    .agg(['mean',
                          'std',
                          'median',
                          'min',
                          'max',
                          percentile_10,
                          percentile_25,
                          percentile_75,
                          percentile_90])
                    .transpose()
                    )
    else:
        cover_lichen = pd.DataFrame()

    # Concatenate cover tables
    cover_composition = pd.concat([cover_vascular, cover_bryophyte, cover_lichen], axis=0)

    if not cover_composition.empty and not constancy_composition.empty:
        # Join statistics for species composition
        stats_composition = (pd.merge(left=constancy_composition,
                                  right=cover_composition.reset_index(),
                                  left_on='name_accepted',
                                  right_on='index',
                                  how='inner')
                         .round(1)
                         .rename(columns={'percentile_10': '10th percentile',
                                          'percentile_25': '25th percentile',
                                          'percentile_75': '75th percentile',
                                          'percentile_90': '90th percentile'}))

        # Filter floristic data for constancy and mean cover limits
        stats_composition = stats_composition[(stats_composition['75th percentile'] >= 1)
                                          & (((stats_composition['constancy'] >= 25)
                                              & (stats_composition['mean'] >= 2))
                                             | ((stats_composition['constancy'] >= 50)
                                                & (stats_composition['mean'] >= 1)))]
        stats_composition = stats_composition.sort_values(by='mean', ascending=True)

        # Create composition display table
        table_composition = (stats_composition[
                             ['name_accepted', 'constancy', 'mean', 'std',
                              '10th percentile', '90th percentile']
                         ].sort_values(by='mean', ascending=False)
                         .rename(columns={'name_accepted': 'Taxon (Accepted Name)',
                                          'constancy': 'Constancy (%)',
                                          'mean': 'Mean (Cover %)',
                                          'std': 'Std. Dev. (Cover %)',
                                          '10th percentile': '10th Percentile (Cover %)',
                                          '90th percentile': '90th Percentile (Cover %)'}))

        # Calculate range
        stats_composition['range_width'] = stats_composition['75th percentile'] - stats_composition['25th percentile']

        # Append taxon habit
        stats_composition = pd.merge(left=stats_composition,
                                 right=taxa_data,
                                 left_on='name_accepted',
                                 right_on='taxon_name',
                                 how='left')
        stats_composition['taxon_habit'] = (stats_composition['taxon_habit']
                                        .str.title()
                                        .replace('Spore-Bearing', 'Spore-bearing'))
        stats_composition['taxon_habit'] = np.where(stats_composition['name_accepted'] == 'moss', 'Moss',
                                                stats_composition['taxon_habit'])

        # Assign bar colors
        bar_colors = stats_composition['taxon_habit'].map(structure_colors)

        # Create custom data array
        custom_data = np.stack([stats_composition['taxon_habit'], stats_composition['75th percentile']], axis=-1)

        # Calculate plot height
        height_composition = 50 * len(stats_composition) if len(stats_composition) > 0 else 100

        # Create floristic composition range plot
        composition_plot = go.Figure()
        
        if not stats_composition.empty:
            composition_plot.add_trace(go.Bar(
                y=stats_composition['name_accepted'],
                x=stats_composition['range_width'],
                base=stats_composition['25th percentile'],
                orientation='h',
                width=0.4,
                name='25th-75th Range',
                marker=dict(
                    color=bar_colors,
                    line=dict(width=0)
                ),
                customdata=custom_data,
                hovertemplate='%{y}<br>Habit: %{customdata[0]}<br>25th Percentile: %{base}%<br>75th Percentile: %{customdata[1]}%<extra></extra>',
                # Remove legend
                showlegend=False
            ))

            # Add scatterplot for means
            composition_plot.add_trace(go.Scatter(
                y=stats_composition['name_accepted'],
                x=stats_composition['mean'],
                mode='markers',
                name='Mean',
                marker=dict(
                    color='black',
                    size=20,
                    symbol='line-ns-open',
                    line=dict(width=2)
                ),
                hovertemplate='%{y}<br>Mean Cover: %{x}%<extra></extra>',
            ))

            # Identify taxon habits
            taxon_habits = stats_composition['taxon_habit'].unique()
            for habit in taxon_habits:
                color = structure_colors.get(habit)
                # Add an empty bar trace for each habit to generate a legend entry
                composition_plot.add_trace(go.Bar(
                    x=[None], y=[None],
                    name=habit,
                    marker_color=color,
                    marker_line_width=0
                ))

        # Update Layout
        composition_plot.update_layout(
            # title='Cover Range 25th to 75th Percentile',
            xaxis_title='Cover Value (%)',
            yaxis_title='Taxon',
            height=height_composition,
            margin=dict(l=10, r=10, t=80, b=80),
            template='plotly_white',
            showlegend=True,
            font=dict(size=18),
            xaxis=dict(
                showline=True,
                linecolor='black',
                linewidth=1,
                ticks='outside',
                ticklen=6,
                showgrid=True,
                gridcolor='lightgrey'
            ),
            legend=dict(
                yanchor="bottom",
                y=0.02,
                xanchor="right",
                x=0.98,
                bgcolor="rgba(255,255,255,0.8)"
            )
        )

        # Update layout for margins and dimensions
        composition_plot.update_layout(
            margin=dict(t=0, l=0, r=0, b=0),
            autosize=True,
            width=None,
            height=height_composition
        )

        # Export to HTML (interactive) and PNG (publication)
        composition_output = os.path.join(output_folder, type_prefix + '_SpeciesComposition.html')
        composition_plot.write_html(composition_output, config={'responsive': True})

    #### PROCESS SUMMARY DATA
    ####____________________________________________________

    # Calculate woody canopy height
    height_summary_df = pd.DataFrame({'mean': [-999], 'percentile_10': [-999], 'percentile_90': [-999]},
                                     index=['height_cm'])
    if schema_data.loc[schema_data['code'] == type_code, 'structure'].item() in ['shrub', 'dwarf shrub']:
        if len(shrub_type) >= 5:
            canopy_data = shrub_type[shrub_type['height_type'].isin(
                ['point-intercept mean', 'mean']
            )]['height_cm'].dropna().to_frame()
            canopy_data['height_cm'] = pd.to_numeric(canopy_data['height_cm'])
            if not canopy_data.empty:
                height_summary_df = (canopy_data['height_cm']
                                     .agg(['mean', percentile_10, percentile_90])
                                     .to_frame()
                                     .transpose())
                height_summary_df.index = ['height_cm']

    # Calculate whole tussock cover
    tussock_summary_df = pd.DataFrame({'mean': [-999], 'percentile_10': [-999], 'percentile_90': [-999]},
                                      index=['cover_percent'])
    if len(tussock_type) >= 5:
        tussock_data_subset = tussock_type[tussock_type['cover_type'].isin(
            ['absolute foliar cover', 'absolute canopy cover']
        )]['cover_percent'].dropna().to_frame()
        tussock_data_subset['cover_percent'] = pd.to_numeric(tussock_data_subset['cover_percent'])
        if not tussock_data_subset.empty:
            tussock_summary_df = (tussock_data_subset['cover_percent']
                                  .agg(['mean', percentile_10, percentile_90])
                                  .to_frame()
                                  .transpose())
            tussock_summary_df.index = ['cover_percent']

    # Create structure statistics
    table_structure = (pd.concat([height_summary_df, tussock_summary_df], axis=0)
                       .reset_index()
                       .rename(columns={'index': 'Characteristic',
                                        'mean': 'Mean',
                                        'percentile_10': '10th Percentile',
                                        'percentile_90': '90th Percentile'}))
    table_structure['Characteristic'] = np.where(table_structure['Characteristic'] == 'height_cm',
                                                 'Woody Canopy Height (cm)',
                                                 table_structure['Characteristic'])
    table_structure['Characteristic'] = np.where(table_structure['Characteristic'] == 'cover_percent',
                                                 'Whole Tussock Cover (%)',
                                                 table_structure['Characteristic'])
    table_structure = table_structure[['Characteristic', 'Mean', '10th Percentile', '90th Percentile']]
    table_structure = table_structure.round(1)

    # Calculate physiography
    physiography_data = environment_type['physiography'].dropna().to_frame()
    if not physiography_data.empty:
        physiography_frequency = physiography_data['physiography'].value_counts().to_frame().reset_index()
        physiography_frequency['frequency'] = (physiography_frequency['count'] / len(physiography_data)) * 100
        physiography_frequency = physiography_frequency[physiography_frequency['frequency'] >= 10]
        physiography_list = physiography_frequency['physiography'].unique()
        physiography_text = '; '.join(physiography_list)
    else:
        physiography_text = 'No Data'

    # Calculate geomorphology
    geomorph_data = environment_type['geomorphology'].dropna().to_frame()
    if not geomorph_data.empty:
        geomorph_frequency = geomorph_data['geomorphology'].value_counts().to_frame().reset_index()
        geomorph_frequency['frequency'] = (geomorph_frequency['count'] / len(geomorph_data)) * 100
        geomorph_frequency = geomorph_frequency[geomorph_frequency['frequency'] >= 10]
        geomorph_list = geomorph_frequency['geomorphology'].unique()
        geomorph_text = '; '.join(geomorph_list)
    else:
        geomorph_text = 'No Data'

    # Calculate macrotopography
    macrotopo_data = environment_type['macrotopography'].dropna().to_frame()
    if not macrotopo_data.empty:
        macrotopo_frequency = macrotopo_data['macrotopography'].value_counts().to_frame().reset_index()
        macrotopo_frequency['frequency'] = (macrotopo_frequency['count'] / len(macrotopo_data)) * 100
        macrotopo_frequency = macrotopo_frequency[macrotopo_frequency['frequency'] >= 10]
        macrotopo_list = macrotopo_frequency['macrotopography'].unique()
        macrotopo_text = '; '.join(macrotopo_list)
    else:
        macrotopo_text = 'No Data'

    # Calculate microtopography
    microtopo_data = environment_type['microtopography'].dropna().to_frame()
    if not microtopo_data.empty:
        microtopo_frequency = microtopo_data['microtopography'].value_counts().to_frame().reset_index()
        microtopo_frequency['frequency'] = (microtopo_frequency['count'] / len(microtopo_data)) * 100
        microtopo_frequency = microtopo_frequency[microtopo_frequency['frequency'] >= 10]
        microtopo_list = microtopo_frequency['microtopography'].unique()
        microtopo_text = '; '.join(microtopo_list)
    else:
        microtopo_text = 'No Data'

    # Calculate moisture regime
    moisture_data = environment_type['moisture_regime'].dropna().to_frame()
    if not moisture_data.empty:
        moisture_frequency = moisture_data['moisture_regime'].value_counts().to_frame().reset_index()
        moisture_frequency['frequency'] = (moisture_frequency['count'] / len(moisture_data)) * 100
        moisture_frequency = moisture_frequency[moisture_frequency['frequency'] >= 20]
        moisture_list = moisture_frequency['moisture_regime'].unique()
        moisture_text = '; '.join(moisture_list)
    else:
        moisture_text = 'No Data'

    # Calculate restrictive layer
    restrict_data = environment_type['restrictive_type'].dropna().to_frame()
    if not restrict_data.empty:
        restrict_frequency = restrict_data['restrictive_type'].value_counts().to_frame().reset_index()
        restrict_frequency['frequency'] = (restrict_frequency['count'] / len(restrict_data)) * 100
        restrict_frequency = restrict_frequency[restrict_frequency['frequency'] >= 20]
        restrict_list = restrict_frequency['restrictive_type'].unique()
        restrict_text = '; '.join(restrict_list)
    else:
        restrict_text = 'No Data'

    # Calculate surface water
    surfacewater_data = environment_type['surface_water'].dropna().to_frame()
    if not surfacewater_data.empty:
        surfacewater_frequency = surfacewater_data['surface_water'].value_counts().to_frame().reset_index()
        surfacewater_frequency['frequency'] = (surfacewater_frequency['count'] / len(surfacewater_data)) * 100
        surfacewater_frequency = surfacewater_frequency[surfacewater_frequency['frequency'] >= 20]
        if True in surfacewater_frequency['surface_water'].values:
            val = surfacewater_frequency.loc[surfacewater_frequency['surface_water']==True, 'frequency'].values[0]
            surfacewater_text = str(round(val, 1)) + '%'
        else:
            surfacewater_text = '0%'
    else:
        surfacewater_text = 'No Data'

    # Quantitative characteristics calculation helper function
    def calculate_quant_metric(df, column_name, exclude_val):
        df_clean = df.dropna(subset=[column_name]).copy()
        df_clean[column_name] = pd.to_numeric(df_clean[column_name])
        df_clean = df_clean[df_clean[column_name] != exclude_val]
        
        if len(df_clean) >= 5:
            summary = (df_clean[column_name]
                       .agg(['mean', 'std', 'median', 'min', 'max',
                             percentile_10, percentile_25, percentile_75, percentile_90])
                       .to_frame()
                       .transpose())
            summary.index = [column_name]
            return summary
        else:
            empty_summary = pd.DataFrame({
                'mean': [-999], 'std': [-999], 'median': [-999], 'min': [-999], 'max': [-999],
                'percentile_10': [-999], 'percentile_25': [-999], 'percentile_75': [-999], 'percentile_90': [-999]
            }, index=[column_name])
            return empty_summary

    # Calculate elevation
    elevation_data = calculate_quant_metric(type_data[['site_visit_code', 'elevation_m']], 'elevation_m', -32768)
    # Calculate slope
    slope_data_summary = calculate_quant_metric(type_data[['site_visit_code', 'slope_deg']], 'slope_deg', -32768)
    # Calculate water depth
    waterdepth_data = calculate_quant_metric(environment_type[['site_visit_code', 'depth_water_cm']], 'depth_water_cm', -999)
    # Calculate moss duff depth
    mossduff_data = calculate_quant_metric(environment_type[['site_visit_code', 'depth_moss_duff_cm']], 'depth_moss_duff_cm', -999)
    # Calculate restrictive layer depth
    restictdepth_data = calculate_quant_metric(environment_type[['site_visit_code', 'depth_restrictive_layer_cm']], 'depth_restrictive_layer_cm', -999)
    # Calculate pH
    pH_data = calculate_quant_metric(soil_type[['site_visit_code', 'ph']], 'ph', -999)
    # Calculate conductivity
    conductivity_data = calculate_quant_metric(soil_type[['site_visit_code', 'conductivity_mus']], 'conductivity_mus', -999)

    # Concatenate quantitative metrics
    stats_environment = (pd.concat([elevation_data,
                               slope_data_summary,
                               waterdepth_data,
                               mossduff_data,
                               restictdepth_data,
                               pH_data,
                               conductivity_data], axis=0)
                     .reset_index()
                     .rename(columns={'index': 'Characteristic',
                                      'mean': 'Mean',
                                      'percentile_10': '10th Percentile',
                                      'percentile_90': '90th Percentile'}))

    # Create environment display table
    environment_mapping = {
        'elevation_m': 'Elevation (m)',
        'slope_deg': 'Slope (°)',
        'depth_water_cm': 'Depth Water (cm)ǂ',
        'depth_moss_duff_cm': 'Depth Moss/Duff (cm)',
        'depth_restrictive_layer_cm': 'Depth Restrictive Layer (cm)',
        'ph': 'pH',
        'conductivity_mus': 'Conductivity (mus)'
    }
    table_environment = (stats_environment[
        ['Characteristic', 'Mean', '10th Percentile', '90th Percentile']
    ]
                     .copy()
                     .round(1))
    table_environment['Characteristic'] = table_environment['Characteristic'].replace(environment_mapping)
    
    #### CONSOLIDATE TABLES
    ####____________________________________________________
    
    # Combine tables into one comprehensive summary CSV
    consolidated_table = pd.concat([
        table_structure.assign(Category='Structure'),
        table_environment.assign(Category='Environment')
    ], ignore_index=True)
    
    # If floristic tables were generated, append them
    if 'table_composition' in locals() and not table_composition.empty:
        comp_data = table_composition.rename(columns={
            'Taxon (Accepted Name)': 'Characteristic'
        }).assign(Category='Species Composition')
        # Map matching columns where possible, drop the rest or let them fill with NaN
        consolidated_table = pd.concat([consolidated_table, comp_data], ignore_index=True)

    # Reorder columns to make Category first
    cols = ['Category', 'Characteristic', 'Mean', '10th Percentile', '90th Percentile']
    # Include other columns if they exist from the composition table
    other_cols = [c for c in consolidated_table.columns if c not in cols]
    consolidated_table = consolidated_table[cols + other_cols]
    
    # Fill any NaNs with -999 for numerical fields or empty string for text fields where applicable
    consolidated_table.fillna({'Mean': -999, '10th Percentile': -999, '90th Percentile': -999}, inplace=True)
    
    # Export comprehensive CSV
    consolidated_output = os.path.join(output_folder, f'{type_prefix}_Comprehensive_Summary.csv')
    consolidated_table.to_csv(consolidated_output, index=False)

    end_timing(start_time)

print('--- Script Finished ---')
