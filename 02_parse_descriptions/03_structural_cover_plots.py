# ---------------------------------------------------------------------------
# Prepare structural cover plots
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-11-21
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Prepare structural cover plots" summarizes vegetation and abiotic cover tables to structural classes and then produces a plot showing proportions of structural classes.
# ---------------------------------------------------------------------------

# Import libraries
import os
import time
import string
import pandas as pd
import plotly.express as px
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
output_folder = os.path.join(repository_folder, '03_summary_data')

# Define input data
schema_input = os.path.join(repository_folder, 'AKVEG_MapClass_Schema.csv')
site_visit_input = os.path.join(class_folder, 'site_visit_type_assignments.csv')
vascular_input = os.path.join(class_folder, 'veg_vascular_compiled.csv')
bryophyte_input = os.path.join(class_folder, 'veg_bryophyte_compiled.csv')
lichen_input = os.path.join(class_folder, 'veg_lichen_compiled.csv')
abiotic_input = os.path.join(archive_folder, '06_abiotic_cover.csv')
ground_input = os.path.join(archive_folder, '08_ground_cover.csv')

# Define output data
site_visit_output = os.path.join(output_folder, '000_site_visit_summary.xlsx')

# Define standard element colors
structure_colors = {
    'Needleleaf Tree': '#346429',
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
    'Litter (< 2 mm)': '#CDAA66',
    'Dead Standing Woody Vegetation': '#897044',
    'Soil': '#828282',
    'Abiotic': '#828282',
    'Rock Fragments': '#828282'
}

#### PARSE STRUCTURAL COVER PLOTS
####------------------------------

# Read data
schema_data = pd.read_csv(schema_input)
site_visit_data = pd.read_csv(site_visit_input)
vascular_data = pd.read_csv(vascular_input)
bryophyte_data = pd.read_csv(bryophyte_input)
lichen_data = pd.read_csv(lichen_input)
abiotic_data = pd.read_csv(abiotic_input)
ground_data = pd.read_csv(ground_input)

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
    vascular_type = vascular_data[vascular_data['site_visit_code'].isin(type_site_list)]
    bryophyte_type = bryophyte_data[bryophyte_data['site_visit_code'].isin(type_site_list)]
    lichen_type = lichen_data[lichen_data['site_visit_code'].isin(type_site_list)]
    abiotic_type = abiotic_data[abiotic_data['site_visit_code'].isin(type_site_list)]
    ground_type = ground_data[ground_data['site_visit_code'].isin(type_site_list)]

    #### PROCESS STRUCTURAL COVER
    ####____________________________________________________

    # Calculate sub-canopy water cover and convert to DataFrame
    if len(ground_type) >= 5:
        water_data = ground_type[ground_type['ground_element'] == 'water']
        water_mean = water_data['ground_cover_percent'].mean()
    else:
        water_mean = site_visit_type['water_cover_pct'].mean()
    structure_water = pd.DataFrame({'mean': [water_mean if pd.notna(water_mean) else 0]}, index=['Water'])

    # Calculate vascular structure
    if len(vascular_type) >= 5:
        structure_vascular = (vascular_type
                              .pivot_table(index='site_visit_code',
                                           columns='taxon_habit',
                                           values='cover_percent',
                                           aggfunc='sum',
                                           fill_value=0)
                              .mean()
                              .to_frame(name='mean'))
    else:
        # Fill table with -999 to represent no data
        structure_vascular = pd.DataFrame({'mean': [0]}, index=['Vascular'])

    # Calculate bryophyte structure
    if len(bryophyte_type) >= 5:
        structure_bryophyte = (bryophyte_type
                               .pivot_table(index='site_visit_code',
                                            columns='taxon_habit',
                                            values='cover_percent',
                                            aggfunc='sum',
                                            fill_value=0)
                               .mean()
                               .to_frame(name='mean'))
    else:
        structure_bryophyte = pd.DataFrame({'mean': [0]}, index=['Bryophyte'])

    # Calculate lichen structure
    if len(lichen_type) >= 5:
        structure_lichen = (lichen_type
                            .pivot_table(index='site_visit_code',
                                         columns='taxon_habit',
                                         values='cover_percent',
                                         aggfunc='sum',
                                         fill_value=0)
                            .mean()
                            .to_frame(name='mean'))
    else:
        structure_lichen = pd.DataFrame({'mean': [0]}, index=['Lichen'])

    # Concatenate biotic structure
    structure_biotic = pd.concat([structure_vascular, structure_bryophyte, structure_lichen, structure_water], axis=0)

    # Calculate abiotic top cover mean
    if len(abiotic_type) >= 5:
        abiotic_type = abiotic_type[abiotic_type['abiotic_element'] != 'water']
        structure_abiotic = (abiotic_type.groupby('abiotic_element')['abiotic_top_cover_percent']
                             .mean()
                             .to_frame(name='mean'))
    else:
        # Calculate abiotic remainder if there is insufficient abiotic data
        biotic_sum = structure_biotic['mean'].sum()
        abiotic_remainder = 100 - biotic_sum if biotic_sum < 100 else 0
        structure_abiotic = pd.DataFrame({'mean': [abiotic_remainder]}, index=['Abiotic'])

    # Concatenate all structure data
    structure_summary = pd.concat([structure_biotic, structure_abiotic], axis=0)

    # Relativize all structure classes to sum to 100%
    total_cover = structure_summary['mean'].sum()
    if total_cover > 0:
        structure_summary['mean'] = (structure_summary['mean'] / total_cover) * 100
    else:
        structure_summary['mean'] = 0

    # Round, reset index, and rename columns appropriately
    structure_summary = structure_summary.round(1).reset_index()
    structure_summary = structure_summary.rename(columns={'index': 'structure'})

    # Remove zero and low values (less than 1%)
    structure_summary = structure_summary[structure_summary['mean'] >= 1].copy()

    # Format structure names
    structure_summary['structure'] = (structure_summary['structure']
                                      .str.title()
                                      .replace('Spore-Bearing', 'Spore-bearing')
                                      .replace('Coniferous Tree', 'Needleleaf Tree')
                                      .replace('Deciduous Tree', 'Broadleaf Tree')
                                      .replace('Litter (< 2 Mm)', 'Litter (< 2 mm)'))

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
    structure_plot.write_html(structure_output, include_plotlyjs='cdn', config={'responsive': True})
    end_timing(start_time)
