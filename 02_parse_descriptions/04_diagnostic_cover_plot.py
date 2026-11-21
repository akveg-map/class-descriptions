# ---------------------------------------------------------------------------
# Prepare diagnostic cover plots
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-11-21
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Prepare diagnostic cover plots" summarizes vegetation cover tables to diagnostic species sets and then produces a plot showing constancy and cover ranges.
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
site_visit_input = os.path.join(class_folder, 'site_visit_type_assignments.csv')
vascular_input = os.path.join(class_folder, 'veg_vascular_compiled.csv')
bryophyte_input = os.path.join(class_folder, 'veg_bryophyte_compiled.csv')
lichen_input = os.path.join(class_folder, 'veg_lichen_compiled.csv')

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

# Remove non-diagnostic sets
schema_diagnostic = schema_diagnostic[~schema_diagnostic['diagnostic set'].isin([
    'Broadleaf Trees', 'Needleleaf Trees', 'Bare Ground', 'Peak Growing Season Sub-canopy Surface Water', 'Lichen'
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
    type_prefix = f'{str(type_code)}_{type_name.translate(translator)}'
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

    #### PROCESS DIAGNOSTIC SPECIES SETS
    ####____________________________________________________

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

    # Summarize lichen
    diagnostic_lichen = (lichen_type
                         .groupby(['site_visit_code'])['cover_percent']
                         .sum()
                         .to_frame()
                         .reset_index())
    diagnostic_lichen['diagnostic set'] = 'Lichen'

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

    # Calculate diagnostic constancy for lichens
    constancy_diagnostic_lichen = (diagnostic_lichen.groupby('diagnostic set')['site_visit_code']
                                   .nunique()
                                   .to_frame(name='occurrences'))
    if len(diagnostic_lichen['site_visit_code'].unique()) > 0:
        constancy_diagnostic_lichen['constancy'] = (constancy_diagnostic_lichen['occurrences']
                                                    / len(diagnostic_lichen['site_visit_code'].unique())) * 100
    else:
        constancy_diagnostic_lichen['constancy'] = 0

    # Concatenate constancy tables
    constancy_diagnostic = pd.concat([constancy_diagnostic_vasc.reset_index(),
                                      constancy_diagnostic_bryo.reset_index(),
                                      constancy_diagnostic_lichen.reset_index()], axis=0)

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

    # Summarize diagnostic sets for lichens
    if not diagnostic_lichen.empty:
        cover_diagnostic_lichen = (diagnostic_lichen
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
        cover_diagnostic_lichen = pd.DataFrame()

    # Concatenate cover tables
    cover_diagnostic = pd.concat([cover_diagnostic_vasc,
                                  cover_diagnostic_bryo,
                                  cover_diagnostic_lichen], axis=0)

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
        height_diagnostic = 50 * len(stats_diagnostic) if len(stats_diagnostic) > 0 else 250
        height_diagnostic = 200 if height_diagnostic < 250 else height_diagnostic

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
    end_timing(start_time)
