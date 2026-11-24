# ---------------------------------------------------------------------------
# Parse html type guides
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2026-11-23
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Parse html type guides" combines custom text from markdown documents with automated plots and summaries to produce html type guides in a standardized format.
# ---------------------------------------------------------------------------

# Import libraries
import os
import re
import glob
import time
import string
import html
from bs4 import BeautifulSoup
import markdown
import pandas as pd
from akutils import *

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Define base URL
base_url = 'https://accs.uaa.alaska.edu/files/akveg-types/'

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work'

# Define folder structure
repository_folder = os.path.join(drive, root_folder, 'Repositories/class-descriptions')
entry_folder = os.path.join(repository_folder, '00_data_entry')
summary_folder = os.path.join(repository_folder, '03_summary_data')
output_folder = os.path.join(repository_folder, '04_description_html')

# Define input files
schema_input = os.path.join(repository_folder, 'AKVEG_MapClass_Schema.csv')
input_files = [
    f for f in glob.glob(os.path.join(entry_folder, '*.md'))
    if os.path.basename(f) != '00_DataEntryTemplate.md'
]

# Define output files
table_output = os.path.join(output_folder, 'index.html')

# Define missing data message
missing_data_html = '<p><em>Too few site visits to generate data.</em></p>'

#### DEFINE FUNCTIONS
####------------------------------

# Define a function to parse text from a markdown file
def parse_markdown(text_input, label):
    # Match label whether colon is inside or outside bold markers
    pattern = r'\*\*' + re.escape(label) + r':?\*\*:?\s*(.*)'
    text_output = None

    try:
        with open(text_input, 'r', encoding='utf-8') as input_file:
            content = input_file.read()
        match = re.search(pattern, content)
        if match:
            text_output = match.group(1).strip()
    except FileNotFoundError:
        print(f"Error: The file {text_input} was not found.")

    return text_output


# Define a function to extract body contents from a standalone Plotly HTML file
def load_plot_html(plot_path, missing_data_html):
    if os.path.exists(plot_path):
        with open(plot_path, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
        body_html = soup.body.decode_contents() if soup.body else str(soup)
        if body_html.strip():
            return f'<div class="plot-container" style="margin: 20px 0;">{body_html}</div>'
    return missing_data_html


# Define a function to convert a summary CSV file to an HTML table
def load_table_html(csv_path, missing_data_html):
    if os.path.exists(csv_path):
        input_data = pd.read_csv(csv_path)
        if not input_data.empty:
            return input_data.to_html(classes='table table-bordered', index=False, border=0)
    return missing_data_html


#### PARSE HTML DOCUMENTS
####------------------------------

# Read map class schema
schema_data = pd.read_csv(schema_input)
schema_data['code'] = schema_data['code'].astype(int)

# Create a translation table that maps punctuation and whitespace to none for removal
remove_chars = string.punctuation + string.whitespace
translator = str.maketrans('', '', remove_chars)

# Initialize list to store URL table records
url_records = []

# Produce type guide for each data entry form
for markdown_input in input_files:
    start_time = time.time()

    # Identify type code and name
    type_code = int(os.path.split(markdown_input)[1][:3])
    type_name = schema_data.loc[schema_data['code'] == type_code, 'map_class'].item()
    type_prefix = f'{type_code:03d}_{type_name.translate(translator)}'

    # Define input files
    structure_plot_input = os.path.join(summary_folder, type_prefix + '_Structure.html')
    diagnostic_plot_input = os.path.join(summary_folder, type_prefix + '_DiagnosticSets.html')
    composition_plot_input = os.path.join(summary_folder, type_prefix + '_SpeciesComposition.html')
    structure_table_input = os.path.join(summary_folder, type_prefix + '_Structure.csv')
    composition_table_input = os.path.join(summary_folder, type_prefix + '_SpeciesComposition.csv')
    env_text_input = os.path.join(summary_folder, type_prefix + '_Env_Text.csv')
    env_summary_input = os.path.join(summary_folder, type_prefix + '_Env_Summary.csv')

    # Define output file
    html_output = os.path.join(output_folder, type_prefix + '.html')

    # Read plots and tables (substituting italic note if missing or empty)
    structure_plot_html = load_plot_html(structure_plot_input, missing_data_html)
    diagnostic_plot_html = load_plot_html(diagnostic_plot_input, missing_data_html)
    composition_plot_html = load_plot_html(composition_plot_input, missing_data_html)
    structure_table_html = load_table_html(structure_table_input, missing_data_html)
    composition_table_html = load_table_html(composition_table_input, missing_data_html)
    env_text_html = load_table_html(env_text_input, missing_data_html)
    env_summary_html = load_table_html(env_summary_input, missing_data_html)

    #### COMPILE HTML OUTPUT
    ####____________________________________________________

    # Parse level and photos from markdown
    level_text = parse_markdown(markdown_input, 'Level')
    level_lower = level_text.lower() if level_text else ''
    photo_text = parse_markdown(markdown_input, 'Photos')

    # Format photo html if URLs or local file paths are present
    if photo_text and photo_text.strip().lower() not in ('', 'na', 'none'):
        raw_items = [item.strip() for item in photo_text.split(',') if item.strip()]
        web_urls = []
        local_files = []

        for item in raw_items:
            # Unwrap Markdown link syntax [label](target) if present
            md_link_match = re.match(r'^\[.*?\]\((.+)\)$', item)
            target = md_link_match.group(1).strip() if md_link_match else item
            target = target.strip('\'"')

            if target.lower().startswith(('http://', 'https://')):
                web_urls.append(target)
            else:
                # Retain only the file name for local drive paths
                file_name = os.path.basename(target.replace('\\', '/'))
                if file_name:
                    local_files.append(file_name)

        photo_parts = []
        if web_urls:
            photo_links = ''.join([
                f'<a href="{url}" target="_blank"><img src="{url}" width="200" alt="{html.escape(type_name)}" style="margin: 5px; display: inline-block; vertical-align: top;"></a>'
                for url in web_urls
            ])
            photo_parts.append('<p><b>Photos (Click Images to Enlarge):</b></p>' + photo_links)
        if local_files:
            escaped_files = ', '.join(html.escape(f) for f in local_files)
            photo_parts.append(f'<p><b>Photos:</b> {escaped_files}</p>')

        photo_html = '\n'.join(photo_parts)
    else:
        photo_html = ''

    # Read markdown file
    with open(markdown_input, 'r', encoding='utf-8') as input_file:
        md_content = input_file.read()

    # Replace title, unit name line, and photos line
    md_content = re.sub(r'^#(?!#)\s*.*', lambda m: f'# {type_name}', md_content, count=1, flags=re.MULTILINE)
    md_content = re.sub(r'\*\*Unit Name:?\*\*:?.*\n*', '', md_content)
    md_content = re.sub(r'\*\*Photos:?\*\*:?.*', lambda m: photo_html, md_content)

    # Substitute env_text table for Physiography through Surface Water Present block
    env_text_pattern = (
        r'\*\*Physiography:?\*\*:?\s*\[physiography_text\].*?'
        r'\*\*Percentage of Sites with Surface Water Present:?\*\*:?\s*\[surfacewater_frequency\]'
    )
    md_content = re.sub(env_text_pattern, lambda m: env_text_html, md_content, flags=re.DOTALL)

    # Replace inline text and CSV table placeholders
    replacements = {
        '[unit_name]': type_name,
        '[type_name]': type_name,
        '[level]': level_lower,
        '[table_structure]': structure_table_html,
        '[table_composition]': composition_table_html,
        '[table_environment]': env_summary_html
    }
    for key, value in replacements.items():
        md_content = md_content.replace(key, str(value))

    # Render markdown (including all descriptive sections, metadata, and references) to HTML
    html_content = markdown.markdown(md_content, extensions=['tables', 'toc'])

    # Insert inline Plotly HTML directly after markdown rendering so JS bundles are untouched
    plot_replacements = {
        '[structure_plot]': structure_plot_html,
        '[diagnostic_plot]': diagnostic_plot_html,
        '[composition_plot]': composition_plot_html
    }
    for placeholder, plot_html in plot_replacements.items():
        html_content = html_content.replace(f'<p>{placeholder}</p>', plot_html)
        html_content = html_content.replace(placeholder, plot_html)

    # Define styles
    rmarkdown_style = """
    <style>
        body {
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 16px;
            line-height: 1.6;
            color: #333;
            background-color: #fff;
            margin: 0;
            padding: 0;
        }

        /* Layout Wrapper */
        .wrapper {
            display: flex;
            max-width: 1200px;
            margin: 0 auto;
        }

        /* Sidebar Navigation (TOC) */
        #TOC {
            width: 250px;
            position: fixed;
            top: 0;
            left: 0;
            bottom: 0;
            overflow-y: auto;
            padding: 40px 20px;
            background-color: #f8f8f8;
            border-right: 1px solid #e7e7e7;
            font-size: 0.9em;
        }
        #TOC ul {
            list-style: none;
            padding-left: 0;
            margin: 0;
        }
        #TOC ul ul {
            padding-left: 20px; /* Indent nested levels */
        }
        #TOC li {
            margin-bottom: 8px;
        }
        #TOC a {
            color: #333;
            text-decoration: none;
            display: block;
            padding: 6px 10px;
            border-radius: 4px;
            transition: background-color 0.1s;
        }
        #TOC a:hover {
            color: #337ab7;
            background-color: #eee;
        }

        /* Main Content */
        .main-content {
            margin-left: 270px; /* Sidebar width + gap */
            padding: 40px 40px;
            max-width: 850px;
            flex: 1;
        }

        /* Typography */
        h1, h2, h3 {
            color: #333;
            font-weight: 600;
            margin-bottom: 0.5em;
            scroll-margin-top: 20px; /* Offset for anchor links */
        }
        h1 { font-size: 2.2em; border-bottom: 1px solid #eee; padding-bottom: 10px; }
        h2 { font-size: 1.6em; border-bottom: 1px solid #eee; padding-bottom: 5px; }
        h3 { font-size: 1.3em; }

        /* Tables */
        table {
            width: 100%;
            margin-bottom: 20px;
            border-collapse: collapse;
            font-size: 0.9em;
        }
        th, td { padding: 8px 12px; text-align: left; border-top: 1px solid #ddd; }
        th { font-weight: bold; border-bottom: 2px solid #ddd; }
        tr:hover {
            background-color: #e6f7ff;
        }

        /* Images */
        img {
            max-width: 100%;
            display: block; /* Default block, inline-block handled inline */
            margin: 20px auto;
            box-shadow: 0 0 5px rgba(0,0,0,0.1);
        }

        /* Links */
        .main-content a { color: #337ab7; text-decoration: none; }
        .main-content a:hover { text-decoration: underline; }

        /* Mobile Responsive */
        @media (max-width: 768px) {
            #TOC {
                position: relative;
                width: 100%;
                height: auto;
                border-right: none;
                border-bottom: 1px solid #e7e7e7;
            }
            .main-content {
                margin-left: 0;
                padding: 20px;
            }
            .wrapper { display: block; }
        }
    </style>
    """

    # JavaScript to auto-generate TOC
    toc_script = """
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        var toc = document.getElementById('TOC');
        var content = document.querySelector('.main-content');

        // Select h2 and h3
        var headers = content.querySelectorAll('h2, h3');
        var tocList = document.createElement('ul');

        if (headers.length > 0) {
            var currentLevel = 1; 
            var currentList = tocList;
            var listStack = [tocList]; 

            headers.forEach(function(header, index) {
                if (!header.id) {
                    header.id = 'header-' + index;
                }

                // Normalize levels: h2 -> 1, h3 -> 2
                var level = parseInt(header.tagName.substring(1)) - 1;

                if (level > currentLevel) {
                    while (level > currentLevel) {
                        var newList = document.createElement('ul');
                        if (currentList.lastElementChild) {
                            currentList.lastElementChild.appendChild(newList);
                        } else {
                            var li = document.createElement('li');
                            currentList.appendChild(li);
                            li.appendChild(newList);
                        }
                        currentList = newList;
                        listStack.push(currentList);
                        currentLevel++;
                    }
                } else if (level < currentLevel) {
                    while (level < currentLevel) {
                        listStack.pop();
                        currentList = listStack[listStack.length - 1];
                        currentLevel--;
                    }
                }

                var li = document.createElement('li');
                var a = document.createElement('a');
                a.href = '#' + header.id;
                a.textContent = header.textContent;
                li.appendChild(a);
                currentList.appendChild(li);
            });

            toc.appendChild(tocList);
        }
    });
    </script>
    """

    # Create final html string
    final_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{type_name}</title>
    {rmarkdown_style}
</head>
<body>
    <div class="wrapper">
        <div id="TOC"></div>
        <div class="main-content">
            {html_content}
        </div>
    </div>
    {toc_script}
</body>
</html>
"""

    # Export html file
    with open(html_output, 'w', encoding='utf-8') as output_file:
        output_file.write(final_html)

    # Append record to HTML table list
    doc_url = base_url + os.path.split(html_output)[1]
    url_records.append({
        'code': type_code,
        'type_name': f'<a href="{doc_url}">{html.escape(type_name)}</a>'
    })

# Create and export HTML lookup table
url_data = (
    pd.DataFrame(url_records)
    .sort_values('code')
    .rename(columns={'code': 'Code', 'type_name': 'Type Name'})
)
table_html = url_data.to_html(classes='table table-bordered', index=False, border=0, escape=False)

index_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AKVEG Map Class Descriptions</title>
    <style>
        body {{
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 16px;
            line-height: 1.6;
            color: #333;
            background-color: #fff;
            margin: 40px auto;
            padding: 0 20px;
            max-width: 850px;
        }}
        .search-container {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }}
        #searchInput {{
            flex: 1;
            min-width: 240px;
            padding: 8px 12px;
            font-size: 0.95em;
            border: 1px solid #ccc;
            border-radius: 4px;
            outline: none;
        }}
        #searchInput:focus {{
            border-color: #337ab7;
            box-shadow: 0 0 4px rgba(51, 122, 183, 0.3);
        }}
        #matchCount {{
            font-size: 0.85em;
            color: #666;
        }}
        table {{
            width: 100%;
            margin-bottom: 20px;
            border-collapse: collapse;
            font-size: 0.9em;
        }}
        th, td {{ padding: 8px 12px; text-align: left; border-top: 1px solid #ddd; }}
        th {{ font-weight: bold; border-bottom: 2px solid #ddd; }}
        tbody tr:hover {{ background-color: #e6f7ff; }}
        a {{ color: #337ab7; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        #noResults {{
            display: none;
            color: #666;
            font-style: italic;
            padding: 12px 0;
        }}
    </style>
</head>
<body>
    <div class="search-container">
        <input type="search" id="searchInput" placeholder="Search by code or type name..." aria-label="Search map classes">
        <span id="matchCount"></span>
    </div>
    {table_html}
    <p id="noResults">No matching map classes found.</p>

    <script>
    document.addEventListener("DOMContentLoaded", function() {{
        var searchInput = document.getElementById('searchInput');
        var rows = Array.from(document.querySelectorAll('table tbody tr'));
        var matchCount = document.getElementById('matchCount');
        var noResults = document.getElementById('noResults');
        var totalRows = rows.length;

        function filterTable() {{
            var query = searchInput.value.trim().toLowerCase();
            var terms = query ? query.split(/\\s+/) : [];
            var visibleCount = 0;

            rows.forEach(function(row) {{
                var text = row.textContent.toLowerCase();
                var isMatch = terms.every(function(term) {{
                    return text.includes(term);
                }});
                row.style.display = isMatch ? '' : 'none';
                if (isMatch) {{
                    visibleCount++;
                }}
            }});

            matchCount.textContent = 'Showing ' + visibleCount + ' of ' + totalRows + ' types';
            noResults.style.display = visibleCount === 0 ? 'block' : 'none';
        }}

        searchInput.addEventListener('input', filterTable);
        filterTable();
    }});
    </script>
</body>
</html>
"""

with open(table_output, 'w', encoding='utf-8') as output_file:
    output_file.write(index_html)
