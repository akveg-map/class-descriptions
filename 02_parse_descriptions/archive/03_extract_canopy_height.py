# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Extract data to sites
# Author: Timm Nawrocki, Matt Macander
# Last Updated: 2026-04-12
# Usage: Must be executed in a Python 3.12+ installation with authentication to Google Earth Engine.
# Description: "Extract data to sites" reduces covariate image assets to buffered points on Google Earth Engine.
# ---------------------------------------------------------------------------

# Import packages
import ee

#### SET UP ENVIRONMENT
####____________________________________________________

# Define paths
ee_project = 'akveg-map'
storage_bucket = 'akveg-data'
storage_prefix = 'site_data'

# Authenticate with Earth Engine
print('Requesting information from server...')
ee.Authenticate()
ee.Initialize(project=ee_project)

# Define asset path
asset_path = f'projects/{ee_project}/assets'

# Define feature collections
buffer_feature = ee.FeatureCollection(f'{asset_path}/sites/akveg_site_visit_buffers')



#### PROCESS DATA EXTRACTION
####____________________________________________________

# Prepare chmv2 image
chmv2_image

# Add reducer output to the Features in the collection.
print('Creating GEE task...')
buffer_means = chmv2_image.reduceRegions(
    collection=buffer_feature,
    reducer=ee.Reducer.mean(),
    crs='EPSG:3338',
    crsTransform=[10, 0, 5, 0, -10, 5],
    tileScale=16
)
buffer_means = buffer_means.map(lambda f: f.setGeometry(None))

# Export results to cloud storage.
task = ee.batch.Export.table.toCloudStorage(
  collection=buffer_means,
  description='akveg-covariates',
  bucket=storage_bucket,
  fileNamePrefix=f'{storage_prefix}/akveg_site_visit_covariates',
  fileFormat='CSV'
)
task.start()
print('GEE task sent to server.')
print('----------')