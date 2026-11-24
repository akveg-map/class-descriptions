# ---------------------------------------------------------------------------
# Prepare diagnostic species summary
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-11-21
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Prepare diagnostic species summary" summarizes vegetation cover tables to diagnostic species, produces a plot showing constancy and cover ranges, and exports a summary table.
# ---------------------------------------------------------------------------

# Import libraries
import os
import time
import string
import pandas as pd
from akutils import *

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
output_folder = os.path.join(repository_folder, '03_summary_data')

# Define input data
schema_input = os.path.join(repository_folder, 'AKVEG_MapClass_Schema.csv')
site_visit_input = os.path.join(class_folder, 'site_visit_type_assignments.csv')
tussock_input = os.path.join(archive_folder, '07_whole_tussock_cover.csv')
shrub_input = os.path.join(archive_folder, '11_shrub_structure.csv')
environment_input = os.path.join(archive_folder, '12_environment.csv')
soil_input = os.path.join(archive_folder, '13_soil_metrics.csv')

#### DEFINE FUNCTIONS
####------------------------------

# Define 15th percentile
def percentile_15(x):
    return x.quantile(0.15)

# Define 85th percentile
def percentile_85(x):
    return x.quantile(0.85)

# Summarize categorical environmental attributes
def summarize_categorical(df, column, min_freq):
    valid_series = df[column].dropna()
    if len(valid_series) == 0:
        return 'No data available.'
    freq_series = valid_series.value_counts(normalize=True) * 100
    valid_categories = freq_series[freq_series >= min_freq].index.tolist()
    return '; '.join(valid_categories) if valid_categories else 'No data available.'

#### PARSE STRUCTURAL COVER PLOTS
####------------------------------

# Read site visit data
schema_data = pd.read_csv(schema_input)
site_visit_data = pd.read_csv(site_visit_input)
site_visit_list = site_visit_data['site_visit_code'].unique()

# Read tussock data
tussock_data = pd.read_csv(tussock_input)
tussock_data = tussock_data[tussock_data['site_visit_code'].isin(site_visit_list)]
tussock_data = tussock_data[tussock_data['cover_percent'] != -999]

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

# Create list of unique type codes
code_list = site_visit_data['code'].unique()

# Create a translation table that maps punctuation and whitespace to none for removal
remove_chars = string.punctuation + string.whitespace
translator = str.maketrans('', '', remove_chars)

# Produce summary data for each type
for type_code in code_list:
    # Identify type name
    type_name = schema_data.loc[schema_data['code'] == type_code, 'map_class'].item()
    type_prefix = f'{type_code:03d}_{type_name.translate(translator)}'
    start_time = time.time()

    # Isolate data for type
    site_visit_type = site_visit_data[site_visit_data['code'] == type_code].copy()
    type_site_list = site_visit_type['site_visit_code'].unique()

    # Skip summary if less than 5 sites are registered to the type
    if len(site_visit_type) < 5:
        print(f'Too few site visits to summarize for {type_name}.')
        output_file = os.path.join(output_folder, f'{type_prefix}_BelowMinimumSites.txt')
        with open(output_file, 'a'):
            pass
        end_timing(start_time)
        continue

    # Subset data to type site visit list
    print(f'Summarizing data for {type_name} ({len(site_visit_type)} site visits)...')
    tussock_type = tussock_data[tussock_data['site_visit_code'].isin(type_site_list)]
    shrub_type = shrub_data[shrub_data['site_visit_code'].isin(type_site_list)]
    environment_type = environment_data[environment_data['site_visit_code'].isin(type_site_list)]
    soil_type = soil_data[soil_data['site_visit_code'].isin(type_site_list)]

    #### SUMMARIZE STRUCTURE
    ####____________________________________________________

    # Calculate woody canopy height
    struc_class = schema_data.loc[schema_data['code'] == type_code, 'structure'].item()
    if struc_class in ['shrub', 'dwarf shrub']:
        canopy_data = shrub_type[shrub_type['height_type'].isin(
            ['point-intercept mean', 'mean']
        )]['height_cm'].dropna().to_frame()
        if len(canopy_data) >= 5:
            canopy_data['height_cm'] = pd.to_numeric(canopy_data['height_cm'])
            height_summary = (canopy_data['height_cm']
                              .agg(['mean', percentile_15, percentile_85])
                              .to_frame()
                              .transpose())
        else:
            height_summary = pd.DataFrame(
                {'mean': [-999], 'percentile_15': [-999], 'percentile_85': [-999]},
                index=['height_cm']
            )
    else:
        height_summary = pd.DataFrame(
            {'mean': [-999], 'percentile_15': [-999], 'percentile_85': [-999]},
            index=['height_cm']
        )

    # Calculate whole tussock cover
    tussock_cover = tussock_type[tussock_type['cover_type'].isin(
        ['absolute foliar cover', 'absolute canopy cover']
    )]['cover_percent'].dropna().to_frame()
    if len(tussock_cover) >= 5:
        tussock_cover['cover_percent'] = pd.to_numeric(tussock_cover['cover_percent'])
        tussock_summary = (tussock_cover['cover_percent']
                           .agg(['mean', percentile_15, percentile_85])
                           .to_frame()
                           .transpose())
    else:
        tussock_summary = pd.DataFrame(
            {'mean': [-999], 'percentile_15': [-999], 'percentile_85': [-999]},
            index=['cover_percent']
        )

    # Create structure statistics
    table_structure = (pd.concat([height_summary, tussock_summary], axis=0)
                       .reset_index()
                       .rename(columns={'index': 'Characteristic',
                                        'mean': 'Mean',
                                        'percentile_15': '15th Percentile',
                                        'percentile_85': '85th Percentile'}))
    table_structure['Characteristic'] = table_structure['Characteristic'].replace({
        'height_cm': 'Woody Canopy Height (cm)',
        'cover_percent': 'Whole Tussock Cover (%)'
    })
    table_structure = table_structure[['Characteristic', 'Mean', '15th Percentile', '85th Percentile']].round(1)

    # Export structure table
    structure_output = os.path.join(output_folder, type_prefix + '_Structure.csv')
    table_structure.to_csv(structure_output, header=True, index=False, sep=',', encoding='utf-8')

    #### SUMMARIZE ENVIRONMENT
    ####____________________________________________________

    # Establish minimum frequency (%)
    min_freq = 25

    # Summarize categorical environmental attributes
    physiography_text = summarize_categorical(environment_type, 'physiography', min_freq)
    geomorph_text = summarize_categorical(environment_type, 'geomorphology', min_freq)
    macrotopo_text = summarize_categorical(environment_type, 'macrotopography', min_freq)
    microtopo_text = summarize_categorical(environment_type, 'microtopography', min_freq)
    moisture_text = summarize_categorical(environment_type, 'moisture_regime', min_freq)
    restrict_text = summarize_categorical(environment_type, 'restrictive_type', min_freq)

    # Calculate surface water percent
    water_valid = pd.to_numeric(site_visit_type['water_cover_pct'], errors='coerce').dropna()
    water_valid = water_valid[water_valid != -999]
    if len(water_valid) > 0:
        surf_water_pct = f"{round((water_valid >= 1).mean() * 100, 1)}%"
    else:
        surf_water_pct = 'No data available.'

    # Compile environmental text summary table
    env_text_table = pd.DataFrame({
        'Attribute': [
            'Physiography',
            'Geomorphology',
            'Macrotopography',
            'Microtopography',
            'Moisture Regime',
            'Restrictive Layer',
            'Surface Water Present (% of site visits)'
        ],
        'Summary': [
            physiography_text,
            geomorph_text,
            macrotopo_text,
            microtopo_text,
            moisture_text,
            restrict_text,
            str(surf_water_pct)
        ]
    })

    # Calculate elevation
    elevation_data = site_visit_type[['site_visit_code', 'elevation_m']].dropna()
    elevation_data['elevation_m'] = pd.to_numeric(elevation_data['elevation_m'])
    elevation_data = elevation_data[elevation_data['elevation_m'] != -32768]
    elevation_data = (elevation_data['elevation_m']
                      .agg(['mean', percentile_15, percentile_85])
                      .to_frame()
                      .transpose())

    # Calculate slope
    slope_data = site_visit_type[['site_visit_code', 'slope_deg']].dropna()
    slope_data['slope_deg'] = pd.to_numeric(slope_data['slope_deg'])
    slope_data = slope_data[slope_data['slope_deg'] != -32768]
    slope_data = (slope_data['slope_deg']
                  .agg(['mean', percentile_15, percentile_85])
                  .to_frame()
                  .transpose())

    # Calculate water depth
    waterdepth_data = environment_type[['site_visit_code', 'depth_water_cm']].dropna()
    waterdepth_data['depth_water_cm'] = pd.to_numeric(waterdepth_data['depth_water_cm'])
    waterdepth_data = waterdepth_data[waterdepth_data['depth_water_cm'] != -999]
    waterdepth_data = (waterdepth_data['depth_water_cm']
                       .agg(['mean', percentile_15, percentile_85])
                       .to_frame()
                       .transpose())

    # Calculate moss duff depth
    mossduff_data = environment_type['depth_moss_duff_cm'].dropna().to_frame()
    mossduff_data['depth_moss_duff_cm'] = pd.to_numeric(mossduff_data['depth_moss_duff_cm'])
    mossduff_data = mossduff_data[mossduff_data['depth_moss_duff_cm'] != -999]
    mossduff_data = (mossduff_data['depth_moss_duff_cm']
                     .agg(['mean', percentile_15, percentile_85])
                     .to_frame()
                     .transpose())

    # Calculate restrictive layer depth
    restrictdepth_data = environment_type['depth_restrictive_layer_cm'].dropna().to_frame()
    restrictdepth_data['depth_restrictive_layer_cm'] = pd.to_numeric(
        restrictdepth_data['depth_restrictive_layer_cm']
    )
    restrictdepth_data = restrictdepth_data[restrictdepth_data['depth_restrictive_layer_cm'] != -999]
    restrictdepth_data = (restrictdepth_data['depth_restrictive_layer_cm']
                          .agg(['mean', percentile_15, percentile_85])
                          .to_frame()
                          .transpose())

    # Calculate pH
    pH_data = soil_type['ph'].dropna().to_frame()
    pH_data['ph'] = pd.to_numeric(pH_data['ph'])
    pH_data = pH_data[pH_data['ph'] != -999]
    pH_data = (pH_data['ph']
               .agg(['mean', percentile_15, percentile_85])
               .to_frame()
               .transpose())

    # Calculate conductivity
    conductivity_data = soil_type['conductivity_mus'].dropna().to_frame()
    conductivity_data['conductivity_mus'] = pd.to_numeric(conductivity_data['conductivity_mus'])
    conductivity_data = conductivity_data[conductivity_data['conductivity_mus'] != -999]
    conductivity_data = (conductivity_data['conductivity_mus']
                         .agg(['mean', percentile_15, percentile_85])
                         .to_frame()
                         .transpose())

    # Concatenate quantitative metrics
    stats_environment = (pd.concat([elevation_data,
                                    slope_data,
                                    waterdepth_data,
                                    mossduff_data,
                                    restrictdepth_data,
                                    pH_data,
                                    conductivity_data], axis=0)
                         .reset_index()
                         .rename(columns={'index': 'Characteristic',
                                          'mean': 'Mean',
                                          'percentile_15': '15th Percentile',
                                          'percentile_85': '85th Percentile'}))

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
    env_summary_table = (stats_environment[
        ['Characteristic', 'Mean', '15th Percentile', '85th Percentile']
    ]
                         .copy()
                         .round(1))
    env_summary_table['Characteristic'] = env_summary_table['Characteristic'].replace(environment_mapping)

    # Export text table
    env_text_output = os.path.join(output_folder, type_prefix + '_Env_Text.csv')
    env_text_table.to_csv(env_text_output, header=True, index=False, sep=',', encoding='utf-8')

    # Export summary table
    env_summary_output = os.path.join(output_folder, type_prefix + '_Env_Summary.csv')
    env_summary_table.to_csv(env_summary_output, header=True, index=False, sep=',', encoding='utf-8')

    end_timing(start_time)