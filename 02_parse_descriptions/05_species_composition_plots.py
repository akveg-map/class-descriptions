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
import numpy as np
import pandas as pd
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
class_folder = os.path.join(project_folder, f'data/data_input/class_descriptions/version_{version_date}')
output_folder = os.path.join(repository_folder, '03_summary_data')

# Define input data
schema_input = os.path.join(repository_folder, 'AKVEG_MapClass_Schema.csv')
diagnostic_input = os.path.join(drive, root_folder, 'Repositories/foliar-cover/AKVEG_Schema_FoliarCover.csv')
taxonomy_input = os.path.join(archive_folder, '00_taxonomy.csv')
site_visit_input = os.path.join(class_folder, 'site_visit_type_assignments.csv')
vascular_input = os.path.join(class_folder, 'veg_vascular_compiled.csv')
bryophyte_input = os.path.join(class_folder, 'veg_bryophyte_compiled.csv')
lichen_input = os.path.join(class_folder, 'veg_lichen_compiled.csv')

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
    'Litter (< 2mm)': '#CDAA66',
    'Dead Standing Woody Vegetation': '#897044',
    'Soil': '#828282',
    'Abiotic': '#828282',
    'Rock Fragments': '#828282'
}

#### DEFINE FUNCTIONS
####------------------------------

# Define 15th percentile
def percentile_15(x):
    return x.quantile(0.15)

# Define 85th percentile
def percentile_85(x):
    return x.quantile(0.85)

#### PARSE STRUCTURAL COVER PLOTS
####------------------------------

# Read data
schema_data = pd.read_csv(schema_input)
schema_diagnostic = pd.read_csv(diagnostic_input)[
    ['target', 'constituents']].rename(columns={'target': 'diagnostic set'}).dropna()
site_visit_data = pd.read_csv(site_visit_input)
vascular_data = pd.read_csv(vascular_input)
bryophyte_data = pd.read_csv(bryophyte_input)
lichen_data = pd.read_csv(lichen_input)

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

# Remove non-diagnostic sets
schema_diagnostic = schema_diagnostic[~schema_diagnostic['diagnostic set'].isin([
    'Broadleaf Trees', 'Needleleaf Trees', 'Bare Ground', 'Peak Growing Season Sub-canopy Surface Water'
])]

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

    #### PROCESS SPECIES COMPOSITION
    ####____________________________________________________

    # Calculate vascular constancy
    constancy_vascular = (vascular_type.groupby('name_accepted')['site_visit_code']
                          .nunique()
                          .to_frame(name='occurrences'))
    if len(vascular_type['site_visit_code'].unique()) > 0:
        constancy_vascular['constancy'] = (constancy_vascular['occurrences']
                                           / len(vascular_type['site_visit_code'].unique())) * 100
    else:
        constancy_vascular['constancy'] = 0

    # Calculate bryophyte constancy
    constancy_bryophyte = (bryophyte_type.groupby('name_accepted')['site_visit_code']
                           .nunique()
                           .to_frame(name='occurrences'))
    if len(bryophyte_type['site_visit_code'].unique()) > 0:
        constancy_bryophyte['constancy'] = (constancy_bryophyte['occurrences']
                                            / len(bryophyte_type['site_visit_code'].unique())) * 100
    else:
        constancy_bryophyte['constancy'] = 0

    # Calculate lichen constancy
    constancy_lichen = (lichen_type.groupby('name_accepted')['site_visit_code']
                        .nunique()
                        .to_frame(name='occurrences'))
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
                                percentile_15,
                                percentile_85])
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
                                 percentile_15,
                                 percentile_85])
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
                              percentile_15,
                              percentile_85])
                        .transpose()
                        )
    else:
        cover_lichen = pd.DataFrame()

    # Concatenate cover tables
    cover_composition = pd.concat([cover_vascular, cover_bryophyte, cover_lichen], axis=0).reset_index()
    cover_composition = cover_composition[~cover_composition['name_accepted'].isin([
        'moss', 'lichen', 'graminoid', 'forb'
    ])]

    if not cover_composition.empty and not constancy_composition.empty:
        # Join statistics for species composition
        stats_composition = (pd.merge(left=constancy_composition,
                                      right=cover_composition,
                                      on='name_accepted',
                                      how='inner')
                             .round(1)
                             .rename(columns={'percentile_15': '15th percentile',
                                              'percentile_85': '85th percentile'}))

        # Filter floristic data for constancy and mean cover limits
        stats_composition = stats_composition[(stats_composition['85th percentile'] >= 1)
                                              & (((stats_composition['constancy'] >= 25)
                                                  & (stats_composition['mean'] >= 2))
                                                 | ((stats_composition['constancy'] >= 50)
                                                    & (stats_composition['mean'] >= 1)))]
        stats_composition = stats_composition.sort_values(by='mean', ascending=True)

        # Calculate range
        stats_composition['range_width'] = stats_composition['85th percentile'] - stats_composition['15th percentile']

        # Append taxon habit
        stats_composition = pd.merge(left=stats_composition,
                                     right=taxa_data,
                                     left_on='name_accepted',
                                     right_on='taxon_name',
                                     how='left')
        stats_composition['taxon_habit'] = (stats_composition['taxon_habit']
                                            .str.title()
                                            .replace('Spore-Bearing', 'Spore-bearing')
                                            .replace('Coniferous Tree', 'Needleleaf Tree')
                                            .replace('Deciduous Tree', 'Broadleaf Tree'))

        # Assign bar colors
        bar_colors = stats_composition['taxon_habit'].map(structure_colors)

        # Create custom data array
        custom_data = np.stack([stats_composition['taxon_habit'], stats_composition['85th percentile']], axis=-1)

        # Calculate plot height
        height_composition = 50 * len(stats_composition) if len(stats_composition) > 0 else 300
        height_composition = 300 if height_composition < 300 else height_composition

        # Create floristic composition range plot
        composition_plot = go.Figure()

        if not stats_composition.empty:
            composition_plot.add_trace(go.Bar(
                y=stats_composition['name_accepted'],
                x=stats_composition['range_width'],
                base=stats_composition['15th percentile'],
                orientation='h',
                width=0.4,
                name='15th-85th Range',
                marker=dict(
                    color=bar_colors,
                    line=dict(width=0)
                ),
                customdata=custom_data,
                hovertemplate='%{y}<br>Habit: %{customdata[0]}<br>15th Percentile: %{base}%<br>85th Percentile: %{customdata[1]}%<extra></extra>',
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
            # title='Cover Range 15th to 85th Percentile',
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
        composition_plot.write_html(composition_output, include_plotlyjs='cdn', config={'responsive': True})

        # Create composition display table
        table_composition = (stats_composition[
                                 ['name_accepted', 'constancy', 'mean', 'std',
                                  '15th percentile', '85th percentile']
                             ].sort_values(by='mean', ascending=False)
                             .rename(columns={'name_accepted': 'Taxon (Accepted Name)',
                                              'constancy': 'Constancy (%)',
                                              'mean': 'Mean (Cover %)',
                                              'std': 'Std. Dev. (Cover %)',
                                              '15th percentile': '15th Percentile (Cover %)',
                                              '85th percentile': '85th Percentile (Cover %)'}))

        # Export composition table
        summary_output = os.path.join(output_folder, type_prefix + '_SpeciesComposition.csv')
        table_composition.to_csv(summary_output, header=True, index=False, sep=',', encoding='utf-8')
    end_timing(start_time)
