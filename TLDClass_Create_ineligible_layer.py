##[LV] TLD-Classification=group
##growthfactor_inputs=multiple raster
##mandatory_growthfactor_inputs=multiple raster
##parcels_input=vector
##parcels_input_columns=string code_obj, gwscod_h, gwsnam_h
##growthfactor_ineligible_threshold=number 50
##inelligible_poly_out=output vector

# Niet-subs, gebouwen en braak: ("GESP_PM"  IS NULL OR "GESP_PM" not in ('SER', 'LOO', 'SGM', 'NPO', 'CON', 'CIV')) and ("GWSCOD_H" not in ('999', '1', '2', '6', '9536', '85', '9825', '895', '9573', '9574', '962', '9829', '9823', '3', '5', '6', '8', '9', '81','89','82'))
# Groenten: ('831','832','8409','8410','8411','8412',8456','8511','8512','8513','8514','8515','8517','8518','8519','8523','8524','8525','8526','8527','8528','8529','8530','8531','8532','8533','8534','8535','8537','8538','8539','8540','8541','8542','8543','8544','8545','8546','8548','8550','8551','8552','8553','8554','8555','8556','8557','8559','856','8563','8564','8586','859','860','8620','863','864','865','881','931','932','94','9409','9410','9456','951','9511','9512','9513','9514','9515','9517','9518','9519','9523','9524','9525','9526','9527','9528','9529','9530','9531','9532','9533','9534','9535','9537','9538','9539','954','9540','9541','9542','9543','9544','9545','9546','9547','9548','9550','9551','9552','9553','9554','9555','9556','9557','956','9561','9563','9564','957','9570','9571','9572','9573','9574','9575','9576','9577','9578','9580','9581','9582','9583','9584','9585','9586','9587','959','960','9602','9603','9604','961','962','9620','964','965','983','9412','8412',9811','9812','52', '9811','9812')
# Bessen, aardbeien, boomkweek, en zo:
#    ('9724', '9723', '9717', '9718','9811','9812','9721', '9722', '9516','9560','9569','921')

# Correctie tov laatste resultaat : gwscod_h in ('9724', '9723', '9717', '9718', '81','9412','8412','9721','9722','9516','9560','52','89','82','9811','9812','9569','921')

#-------------------------------------
# Import/init needed modules
#-------------------------------------
import sys
import os
import datetime
import qgis
from qgis.core import *
from qgis.analysis import QgsZonalStatistics

# Make sure the lib dir will be known by python...
sys.path.append('C:\\Projects\\ANG_GIS\\GISScripts\\QGIS_tools')
import Lib_LVHelper as lvhelper

OTB_BIN = 'X:\\GIS\\Software\\_Progs\\OTB-6.0.0-win64\\bin'

#-------------------------------------
# Check/init variables
#-------------------------------------
output_folder = os.path.split(inelligible_poly_out)[0]
tmp_folder = "{folder}\\Tmp".format(folder=output_folder)
if not os.path.exists(tmp_folder):
    os.makedirs(tmp_folder)
    
now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
logfile = "{folder}\\Log\\create_ineligible_layer_{datetime_str}.txt".format(folder=output_folder , datetime_str=now_str)
lvhelper.init_log(logfile, progress)

#-------------------------------------
# The real processing starts here
#-------------------------------------

lvhelper.log("START TOOL - CREATE INELIGIBLE LAYER")
growthfactor_list = growthfactor_inputs.split(';')

# Print the input parameters
#-------------------------------------
lvhelper.log("Parameters provided:")

lvhelper.log("  - growthfactor_inputs:")
# Loop over all growthfactor layers...
for i, growthfactor_file in enumerate(growthfactor_list):
    lvhelper.log("    - growthfactor_input({index}): {file}".format(index=i, file=growthfactor_file))  
    
lvhelper.log("  - parcels_input: {0}".format(parcels_input))
lvhelper.log("  - growthfactor_ineligible_threshold: {0:d}".format(growthfactor_ineligible_threshold))
lvhelper.log("  - inelligible_poly_out: {0}".format(inelligible_poly_out))

# Combine all input raster bands to one vrt file
#-------------------------------------   
lvhelper.log('Combine all input growth index files to one vrt')
growthfactor_inputs_merged = "{folder}\\growthfactor_merged.vrt".format(folder=tmp_folder)
if not os.path.exists(growthfactor_inputs_merged):
    command = 'gdalbuildvrt -resolution highest -separate "{output_file}"'.format(output_file=growthfactor_inputs_merged)
    for i, growthfactor_file in enumerate(growthfactor_list):
        command += ' "{file}"'.format(file=growthfactor_file)
    lvhelper.run_command(command)
else:
    lvhelper.log('    -> SKIP, tmp output file exists already: {0}'.format(growthfactor_inputs_merged)) 
        
# Get some info of the input layers
#-------------------------------------
# Raster layer projection...
growthfactor_inputs_merged_layer = processing.getObject(growthfactor_inputs_merged)
growthfactor_proj = growthfactor_inputs_merged_layer.crs().authid().lower()
lvhelper.log("Raster layer has projection authid {0}".format(growthfactor_proj))
xMin = growthfactor_inputs_merged_layer.extent().xMinimum()
yMin = growthfactor_inputs_merged_layer.extent().yMinimum()
xMax = growthfactor_inputs_merged_layer.extent().xMaximum()
yMax = growthfactor_inputs_merged_layer.extent().yMaximum()
rasterUnitsPerPixelX = growthfactor_inputs_merged_layer.rasterUnitsPerPixelX()
rasterUnitsPerPixelY = growthfactor_inputs_merged_layer.rasterUnitsPerPixelY()
growthfactor_nodata_value = growthfactor_inputs_merged_layer.dataProvider().block(1, growthfactor_inputs_merged_layer.extent(), rasterUnitsPerPixelY, rasterUnitsPerPixelX).noDataValue()
del growthfactor_inputs_merged_layer

# Input layer projection
parcels_input_proj = 'epsg:31370'.lower()

# Convert input parcels to sqlite and make sure the parcels are in the same projcetion as the growth raster files...
#-------------------------------------
parcels_input_reproj = "{folder}\\parcels_reproj.sqlite".format(folder=tmp_folder)
parcels_input_reproj_layername = os.path.splitext(os.path.split(parcels_input_reproj)[1])[0].replace('-', '_').replace(' ', '_')
lvhelper.log("Parcel projection is different of growth indexes -> reproject parcels")
if not os.path.exists(parcels_input_reproj):
    command = 'ogr2ogr -f SQLite -dsco SPATIALITE=YES -gt 200000 -s_srs {in_proj} -t_srs {out_proj} "{out_file}" "{in_file}" -nln {out_layername}'.format(in_proj=parcels_input_proj, out_proj=growthfactor_proj, out_file=parcels_input_reproj, in_file=parcels_input, out_layername=parcels_input_reproj_layername)
    lvhelper.run_command(command)
else:
    lvhelper.log('    -> SKIP, tmp output file exists already: {0}'.format(parcels_input_reproj)) 

# Calculate the smallest extent of raster input versus parcels... this speeds the rest of the processing up...
#-------------------------------------
parcels_input_reproj_layer = processing.getObject(parcels_input_reproj)
xMin_parcels = parcels_input_reproj_layer.extent().xMinimum()
if xMin < xMin_parcels:
    xMin = xMin_parcels-((xMin_parcels-xMin)%rasterUnitsPerPixelX)
yMin_parcels = parcels_input_reproj_layer.extent().yMinimum()
if yMin < yMin_parcels:
    yMin = yMin_parcels-((yMin_parcels-yMin)%rasterUnitsPerPixelY)
xMax_parcels = parcels_input_reproj_layer.extent().xMaximum()
if xMax > xMax_parcels:
    xMax = xMax_parcels+((xMax-xMax_parcels)%rasterUnitsPerPixelX)
yMax_parcels = parcels_input_reproj_layer.extent().yMaximum()
if yMax > yMax_parcels:
    yMax = yMax_parcels+((yMax-yMax_parcels)%rasterUnitsPerPixelY)
del parcels_input_reproj_layer

# Remark: we need enough decimal character because the translation otherwise can become big using lat/lon projections
output_resolution_str = '{0:.16f} {1:.16f}'.format(rasterUnitsPerPixelX, rasterUnitsPerPixelY)
output_layer_extent = "{0:.16f} {1:.16f} {2:.16f} {3:.16f}".format(xMin, yMin, xMax, yMax)

# Rasterize parcel input to be use them as mask on the raster files. Otherwise the vector files become large and processing is slow...
#-------------------------------------
parcels_mask = "{folder}\\parcels_mask.tif".format(folder=tmp_folder)
lvhelper.log("Rasterize PercelenInput")
# The layer should have the same extent and resolution as the image, so the pixels match as good as possible...
# -at: all_touched: all pixels that are touched by the cutline are burned as well instead of only the ones inside the cutline
# -burn 255: always use 255 as value for raster 
if not os.path.exists(parcels_mask):
    command = 'gdal_rasterize -at -ot byte -init 0 -burn 255 -te {target_extent} -tr {target_res} "{in_file}" "{out_file}"'.format(target_extent=output_layer_extent, target_res=output_resolution_str,  in_file=parcels_input_reproj, out_file=parcels_mask)
    lvhelper.run_command(command)
else:
    lvhelper.log('    -> SKIP, tmp output file exists already: {0}'.format(parcels_mask)) 

# Combine all input raster bands + the parcel mask band in one vrt file
#-------------------------------------
lvhelper.log('Combine all input growth index files + the parcel mask to one vrt')
# Divide the resolution by 2 to evade inaccuracies if the input growth inderx layes aren't aligned perfectly...
rasterUnitsPerPixelX = rasterUnitsPerPixelX/2
rasterUnitsPerPixelY = rasterUnitsPerPixelY/2
output_resolution_str = '{0:.16f} {1:.16f}'.format(rasterUnitsPerPixelX, rasterUnitsPerPixelY)
growthfactor_inputs_parcelmask_merged = "{folder}\\growthfactor_inputs_parcelmask_merged.vrt".format(folder=tmp_folder)
# Remarks:
#    - Using bilinear resampling helps to reduce the impact of nodata pixels... but increases chance of false positives at the side of parcels... -> not used (-r bilinear -srcnodata None)
#    - We use -srcnodata None so nodatavalues can be treated specifically in the raster calculator
if not os.path.exists(growthfactor_inputs_parcelmask_merged):
    command = 'gdalbuildvrt -srcnodata None -te {target_extent} -tr {target_res} -separate "{out_file}" "{mask}"'.format(target_extent=output_layer_extent, target_res=output_resolution_str, out_file=growthfactor_inputs_parcelmask_merged, mask=parcels_mask)
    for i, growthfactor_file in enumerate(growthfactor_list):
        command += ' "{file}"'.format(file=growthfactor_file)
    lvhelper.run_command(command)
else:
    lvhelper.log('    -> SKIP, tmp output file exists already: {0}'.format(growthfactor_inputs_parcelmask_merged)) 

# Now create a raster that can be used to create a polygon layer with all pixels that are lower than the threshold and are inside or on the edge of the parcels...
#-------------------------------------
# Result = - all pixels in 3 input images> the thresshold OR outside the parcels get value 0
#              - the other pixels get the average growth index of the 3 input images
# Remarks:
#     - OTB raster calculator seems to be fastest and doesn't crash typically! SAGA seems OK as well.
#     - Formula to get a unique number per pixel instead of the value: ((im1b4>0) and (im1b1<%d) and (im1b2<%d) and (im1b3<%d)) ? (idxX-(9*(int)(idxX/9))) + (idxY-(9*(int)(idxY/9))) : 0
#     - mod operator doesn't exist in OTB raster calculator
# TODO: possible small optimization: if a pixel value = nodata, replace it by eg. the thresshold value not to loose parcels that have eg. one picture that is nodata and 2 having pixels that indicate problems...
lvhelper.log("Create raster image with ineligible pixels")
ineligible_pixels_raster = '{folder}\\ineligible_pixels_raster.tif'.format(folder=tmp_folder)
if not os.path.exists(ineligible_pixels_raster):
    
    # First band: the actual values...
    # First build the rastercalc expression to use dynamically based on the number of input growtfactor files...
    # IF if parcel mask > 0
    rastercalc_expression = '((im1b1>0)'
    # AND each growthfactor pixel should be within the thresshold OR == nodata value
    for i, growthfactor_file in enumerate(growthfactor_list):
        expression_index = i+2
        rastercalc_expression += ' and (im1b{index}<={threshold} or im1b{index}=={nodata_value})'.format(index=expression_index, threshold=growthfactor_ineligible_threshold, nodata_value=growthfactor_nodata_value)
        
    # THEN -> average pixel value of all valid (non-nodata) growthfactor pixels
    rastercalc_expression += ') ? ('
    
    # First the nominator...
    rastercalc_expression += ' (0'
    for i, growthfactor_file in enumerate(growthfactor_list):
        expression_index = i+2
        rastercalc_expression += ' + (im1b{index}=={nodata_value} ? 0 : im1b{index})'.format(index=expression_index, nodata_value=growthfactor_nodata_value)   
    rastercalc_expression += ')'
    
    # Now the denominator...
    rastercalc_expression += ') / ((0'
    for i, growthfactor_file in enumerate(growthfactor_list):
        expression_index = i+2
        rastercalc_expression += ' + (im1b{index}=={nodata_value} ? 0 : 1)'.format(index=expression_index, nodata_value=growthfactor_nodata_value)   
    rastercalc_expression += ')'
    
    # ELSE: 0
    rastercalc_expression += ') : 0'
    
    # Full formula example...( (im1b6>0) and (im1b1<=55 or im1b1==255.0) and (im1b2<=55 or im1b2==255.0) and (im1b3<=55 or im1b3==255.0) and (im1b4<=55 or im1b4==255.0) and (im1b5<=55 or im1b5==255.0) ) ? ((im1b1==255.0 ? 0 : im1b1) + (im1b2==255.0 ? 0 : im1b2) + (im1b3==255.0 ? 0 : im1b3) + (im1b4==255.0 ? 0 : im1b4) + (im1b5==255.0 ? 0 : im1b5) ) / ( (im1b1==255.0 ? 0 : 1) + (im1b2==255.0 ? 0 : 1) + (im1b3==255.0 ? 0 : 1) + (im1b4==255.0 ? 0 : 1) + (im1b5==255.0 ? 0 : 1) ) : 0

    # Second band: all pixels that don't become 0 get the same value...
    rastercalc_expression += ' ; ' 
    # First build the rastercalc expression to use dynamically based on the number of input growtfactor files...
    # IF if parcel mask > 0
    rastercalc_expression += '((im1b1>0)'
    # AND each growthfactor pixel should be within the thresshold OR == nodata value
    for i, growthfactor_file in enumerate(growthfactor_list):
        expression_index = i+2
        rastercalc_expression += ' and (im1b{index}<={threshold} or im1b{index}=={nodata_value})'.format(index=expression_index, threshold=growthfactor_ineligible_threshold, nodata_value=growthfactor_nodata_value)
        
    # THEN -> 255 ELSE 0
    rastercalc_expression += ') ? 255: 0'
    
    command = '{bin}\\otbcli_BandMathX.bat -il "{in_file}" -out "{out_file}" uint8 -ram 512 -exp "{expression}"'.format(bin=OTB_BIN, in_file=growthfactor_inputs_parcelmask_merged, out_file=ineligible_pixels_raster, expression=rastercalc_expression)
    # IgnoreCrash=True: sometimes bandmathx crashes when ready, so ignore crashes...
    lvhelper.run_command(command, True)
else:
    lvhelper.log('    -> SKIP, tmp output file exists already: {0}'.format(ineligible_pixels_raster)) 
   
# Set nodata value
lvhelper.log('Set nodata value on the choosen layer to 0')
command = 'python gdal_edit.py -a_nodata 0 "{in_file}"'.format(in_file=ineligible_pixels_raster)
lvhelper.run_command(command)

# Polygonize the potential ineligible pixels raster
#-------------------------------------
ineligible_pixels_poly_layername  ='ineligible_pixels_poly'
ineligible_pixels_poly = '{folder}\\{layername}.shp'.format(folder=tmp_folder, layername=ineligible_pixels_poly_layername)
if not os.path.exists(ineligible_pixels_poly):
    # First polygonize to a shapefile, this is apparently a lot faster...
    lvhelper.log("Convert to polygons, aggregated on pixel value")
    command = 'python gdal_polygonize.py "{in_file}" -f "ESRI Shapefile" "{out_file}" "{out_layername}" "{out_columnname}"'.format(in_file=ineligible_pixels_raster, out_file=ineligible_pixels_poly, out_layername=ineligible_pixels_poly_layername, out_columnname='growth')
    lvhelper.run_command(command)
    
    # Add the number of pixels overlapping with the mandatory growthfactor layers...
    # Create QgsVectorLayer object
    polygonLayer = QgsVectorLayer(ineligible_pixels_poly, ineligible_pixels_poly_layername, "ogr") 
    polygonLayer.startEditing()

    # Loop over all raster layers to add zonal statistics to the vector layer...
    mandatory_growthfactor_list = mandatory_growthfactor_inputs.split(';')
    lvhelper.log("Loop through all raster layers to add statistics...")
    for i, input_raster in enumerate(mandatory_growthfactor_list):
        # usage - QgsZonalStatistics (QgsVectorLayer *polygonLayer, const QString &rasterFile, const QString &attributePrefix="", int rasterBand=1)
        lvhelper.log("    - Adding statistics from raster file " + input_raster + " ...")
        zoneStat = QgsZonalStatistics (polygonLayer, input_raster, ("m" + str(i+1) + "_"), 1, QgsZonalStatistics.Count | QgsZonalStatistics.Mean)
        zoneStat.calculateStatistics(None)
    
    polygonLayer.commitChanges()
    
    # Create the select statement needed to calculate the number of mandatory pixels...
    full_pixel_area = rasterUnitsPerPixelX*rasterUnitsPerPixelY*4        # the full pixel area needs a multiplication by 4 because we created smaller pixels compared to the native pixels to increase the accuracy!!!
    max_mandatory_pixels_area_formula = '0.25*{full_pixel_area}'.format(full_pixel_area=full_pixel_area)
    for i, input_raster in enumerate(mandatory_growthfactor_list):
        if i==0:
            max_mandatory_pixels_area_formula = 'MAX('
        max_mandatory_pixels_area_formula += ("IFNULL(m" + str(i+1) + "_count, 0)")
        if i<(len(mandatory_growthfactor_list)-1):
            max_mandatory_pixels_area_formula += ', '
        else:
            max_mandatory_pixels_area_formula += ')*{full_pixel_area}'.format(full_pixel_area=full_pixel_area)
        
    # Now add the polygonized pixels to the sqlite file with the original (reprojected)parcels: they need to be in the same file to do the interect later on... 
    lvhelper.log("Add polygonized polygones to sqlite file")
    # Remark: - Also add a column with the pixel area
    #              - Apply a buffer of 0 to fix self intersection errors...
    command = 'ogr2ogr --config OGR_SQLITE_SYNCHRONOUS OFF -f SQLite -update -overwrite -gt 200000 -s_srs {proj} -t_srs {proj} "{out_file}" "{in_file}" -nln {out_layername} -nlt MULTIPOLYGON -dialect sqlite -sql "SELECT ST_Buffer(geometry, 0.0) AS geometry, growth, ST_Area(geometry) AS area_pix, ({max_mandatory_pixels_area}) AS area_mpix, CASE WHEN ({max_mandatory_pixels_area}) >= ST_Area(geometry) THEN 1 ELSE 0 END AS mpix_ok FROM {in_layername}"'.format(proj=growthfactor_proj, out_file=parcels_input_reproj, in_file=ineligible_pixels_poly, out_layername=ineligible_pixels_poly_layername, max_mandatory_pixels_area=max_mandatory_pixels_area_formula, in_layername=ineligible_pixels_poly_layername)
    lvhelper.run_command(command)
else:
    lvhelper.log('    -> SKIP, tmp output file exists already: {0}'.format(ineligible_pixels_poly)) 

# Polygonize the potential ineligible pixels raster, with all adjacent pixels regardless of value in one object
#-------------------------------------
ineligible_pixels_poly_adj_layername = 'ineligible_pixels_poly_adj'
ineligible_pixels_poly_adj = '{folder}\\{layername}.shp'.format(folder=tmp_folder, layername=ineligible_pixels_poly_adj_layername)
lvhelper.log("Convert to polygons, aggregated only on being adjacent with 8 connectedness")
if not os.path.exists(ineligible_pixels_poly_adj):
    # First polygonize to a shapefile, this is apparently a lot faster...
    command = 'python gdal_polygonize.py "{in_file}" -b 2 -f "ESRI Shapefile" "{out_file}" -8 "{out_layername}" "{out_columnname}"'.format(in_file=ineligible_pixels_raster, out_file=ineligible_pixels_poly_adj, out_layername=ineligible_pixels_poly_adj_layername, out_columnname='na')
    lvhelper.run_command(command)
    
    # Now add the polygonized pixels to the sqlite file with the original (reprojected)parcels: they need to be in the same file to do the intersect later on... 
    lvhelper.log("Add polygonized polygones to sqlite file, now the aggregated adjacent pixels")
    command = 'ogr2ogr --config OGR_SQLITE_SYNCHRONOUS OFF -f SQLite -update -overwrite -gt 200000 -s_srs {proj} -t_srs {proj} "{out_file}" "{in_file}" -nln {out_layername} -nlt MULTIPOLYGON -dialect sqlite -sql "SELECT ST_Buffer(geometry, 0.0) AS geometry FROM {in_layername}"'.format(proj=growthfactor_proj, out_file=parcels_input_reproj, in_file=ineligible_pixels_poly_adj, out_layername=ineligible_pixels_poly_adj_layername, in_layername=ineligible_pixels_poly_adj_layername)
    lvhelper.run_command(command)
else:
    lvhelper.log('    -> SKIP, tmp output file exists already: {0}'.format(ineligible_pixels_poly)) 

# Intersect ineligible pixel layers with input parcels
#-------------------------------------
inter_prc_ineligible_layername = 'inter_prc_ineligible'
inter_prc_ineligible_adj_layername = 'inter_prc_ineligible_adj'
inter_prc_ineligible = "{folder}\\{layername}.sqlite".format(folder=tmp_folder, layername=inter_prc_ineligible_layername)
inter_prc_ineligible_adj = inter_prc_ineligible
if not os.path.exists(inter_prc_ineligible):
    # Intersect with the detailed polygonized pixels with the actual growth values
    lvhelper.log("Calculate intersect between parcels and ineligible pixels...")
    command = 'ogr2ogr --config OGR_SQLITE_CACHE 200 --config OGR_SQLITE_SYNCHRONOUS OFF -f SQLite -dsco SPATIALITE=YES -gt 200000 "{out_file}" "{in_file}" -nln {out_layername} -nlt MULTIPOLYGON -dialect sqlite -sql "SELECT ST_Intersection(in_prc.geometry, in_ineli.geometry) AS geometry, in_prc.rowid AS prc_rowid, {in_parcel_columns}, in_ineli.growth, in_ineli.area_pix, in_ineli.area_mpix, in_ineli.mpix_ok FROM {in_parcel_layername} in_prc, {in_ineligible_poly_layername} in_ineli WHERE GeometryType(ST_Intersection(in_prc.geometry, in_ineli.geometry)) IN (\'POLYGON\', \'MULTIPOLYGON\') AND in_prc.rowid IN (SELECT rowid FROM SpatialIndex WHERE f_table_name = \'{in_parcel_layername}\' AND search_frame = in_ineli.geometry)"'.format(out_file=inter_prc_ineligible, in_file=parcels_input_reproj, out_layername=inter_prc_ineligible_layername, in_parcel_columns=parcels_input_columns, in_parcel_layername=parcels_input_reproj_layername, in_ineligible_poly_layername=ineligible_pixels_poly_layername)
    lvhelper.run_command(command)

    # Add columns with intersect area and risk
    lvhelper.log("Add columns area_int and risk_int to polygon file")
    command = 'ogrinfo "{in_file}" -sql "ALTER TABLE {layername} ADD COLUMN area_int REAL"'.format(in_file=inter_prc_ineligible, layername=inter_prc_ineligible_layername)
    lvhelper.run_command(command)
    command = 'ogrinfo "{in_file}" -sql "ALTER TABLE {layername} ADD COLUMN risk_int REAL"'.format(in_file=inter_prc_ineligible, layername=inter_prc_ineligible_layername)
    lvhelper.run_command(command)
    # Risk = area corrected with growth, area * 2 if growth = 0
    command = 'ogrinfo "{in_file}" -dialect SQLite -sql "UPDATE {layername} SET area_int = ST_Area(GEOMETRY), risk_int = (ST_Area(GEOMETRY)*(1+(({threshold:f}-growth)/{threshold:f})))"'.format(in_file=inter_prc_ineligible, layername=inter_prc_ineligible_layername, threshold=growthfactor_ineligible_threshold)
    lvhelper.run_command(command)
    
    # Intersect with polygonized pixels aggregated on 8-connectedness adjacent pixels
    lvhelper.log("Calculate intersect of parcels with polygonized pixels that were aggregated with 8-connectedness adjacent pixels")
    command = 'ogr2ogr --config OGR_SQLITE_CACHE 200 --config OGR_SQLITE_SYNCHRONOUS OFF -f SQLite -dsco SPATIALITE=YES -gt 200000 -update "{out_file}" "{in_file}" -nln {out_layername} -nlt MULTIPOLYGON -dialect sqlite -sql "SELECT ST_Intersection(in_prc.geometry, in_ineli.geometry) AS geometry, in_prc.rowid AS prc_rowid, {in_parcel_columns} FROM {in_parcel_layername} in_prc, {in_ineligible_poly_layername} in_ineli WHERE GeometryType(ST_Intersection(in_prc.geometry, in_ineli.geometry)) IN (\'POLYGON\', \'MULTIPOLYGON\') AND in_prc.rowid IN (SELECT rowid FROM SpatialIndex WHERE f_table_name = \'{in_parcel_layername}\' AND search_frame = in_ineli.geometry)"'.format(out_file=inter_prc_ineligible_adj, in_file=parcels_input_reproj, out_layername=inter_prc_ineligible_adj_layername, in_parcel_columns=parcels_input_columns, in_parcel_layername=parcels_input_reproj_layername, in_ineligible_poly_layername=ineligible_pixels_poly_adj_layername)
    lvhelper.run_command(command)
    
    # Add column to aggregated pixels with the average risk of the individual pixels based on the other intersections...
    #-------------------------------------
    # Remark: something similar should be possible with "zonal statistics", but this doesnt' work because zonal statistics doesnt use the center of the pixels but the bottom-left corner, which gives wrong results :-(... 
    lvhelper.log("Add columns to aggregated ineligible pixel polygon file: sum_risk, min_growth, max_growth, avg_growth, mpix_ok")
    command = 'ogrinfo "{in_file}" -sql "ALTER TABLE {layername} ADD COLUMN sum_risk REAL"'.format(in_file=inter_prc_ineligible_adj, layername=inter_prc_ineligible_adj_layername)
    lvhelper.run_command(command)
    command = 'ogrinfo "{in_file}" -sql "ALTER TABLE {layername} ADD COLUMN min_growth REAL"'.format(in_file=inter_prc_ineligible_adj, layername=inter_prc_ineligible_adj_layername)
    lvhelper.run_command(command)    
    command = 'ogrinfo "{in_file}" -sql "ALTER TABLE {layername} ADD COLUMN max_growth REAL"'.format(in_file=inter_prc_ineligible_adj, layername=inter_prc_ineligible_adj_layername)
    lvhelper.run_command(command)       
    command = 'ogrinfo "{in_file}" -sql "ALTER TABLE {layername} ADD COLUMN avg_growth REAL"'.format(in_file=inter_prc_ineligible_adj, layername=inter_prc_ineligible_adj_layername)
    lvhelper.run_command(command)           
    command = 'ogrinfo "{in_file}" -sql "ALTER TABLE {layername} ADD COLUMN mpix_ok REAL"'.format(in_file=inter_prc_ineligible_adj, layername=inter_prc_ineligible_adj_layername)
    lvhelper.run_command(command)           
    command = 'ogrinfo "{in_file}" -dialect SQLite -sql "UPDATE {layername_to_update} SET (sum_risk, min_growth, max_growth, avg_growth, mpix_ok) = (SELECT SUM(layer_details.risk_int) AS sum_risk, MIN(layer_details.growth) AS min_growth, MAX(layer_details.growth) AS max_growth, AVG(layer_details.growth) AS avg_growth, MIN(layer_details.mpix_ok) AS mpix_ok FROM {layername_details} layer_details WHERE {layername_to_update}.prc_rowid = layer_details.prc_rowid AND GeometryType(ST_Intersection({layername_to_update}.geometry, layer_details.geometry)) IN (\'POLYGON\', \'MULTIPOLYGON\') AND layer_details.rowid IN (SELECT rowid FROM SpatialIndex WHERE f_table_name = \'{layername_details}\' AND search_frame = {layername_to_update}.geometry))"'.format(in_file=inter_prc_ineligible_adj, layername_to_update=inter_prc_ineligible_adj_layername, layername_details=inter_prc_ineligible_layername)
    lvhelper.run_command(command)   
else:
    lvhelper.log('    -> SKIP, tmp output file exists already: {0}'.format(inter_prc_ineligible)) 

# Filter the interesting intersections and aggregate on parcel level...
#-------------------------------------
# For the rest of the temp files we use one sqlite file because we will need to to several joins, intersect,... between the different temp tables in the rest of the script...
inter_prc_ineligible_adj_filtered_layername = 'inter_prc_ineligible_adj_filtered'
inter_prc_ineligible_adj_filtered = "{folder}\\{layername}.sqlite".format(folder=tmp_folder, layername=inter_prc_ineligible_adj_filtered_layername)
inter_prc_ineligible_adj_filtered_aggr_layername = 'inter_prc_ineligible_filtered_aggr'
inter_prc_ineligible_adj_filtered_aggr = inter_prc_ineligible_adj_filtered
# Filter: normalised growth index in % + % intersect of pixel should be > 60%
#    -> this formula gives pixels with a growth index significantly smaller than the treshold a boost
#filter = "((a_mean-%d)/%d)+(area_int/a_area_pix)>0.8" %(growth_index_ineligible_threshold, growth_index_ineligible_threshold)
if not os.path.exists(inter_prc_ineligible_adj_filtered):
    filter = "(sum_risk>=25) AND (gwscod_h IN (\'60\') OR mpix_ok>0)" 
    lvhelper.log("Export potential ineligible surfaces that comply with this filter: {filter_expr}".format(filter_expr=filter))
    command = 'ogr2ogr -f SQLite -dsco SPATIALITE=YES -gt 200000 "{out_file}" "{in_file}" -sql "SELECT * FROM {in_layername} WHERE {filter_expr}" -nln "{out_layername}"'.format(out_file=inter_prc_ineligible_adj_filtered, in_file=inter_prc_ineligible, in_layername=inter_prc_ineligible_adj_layername, filter_expr=filter, out_layername=inter_prc_ineligible_adj_filtered_layername)
    lvhelper.run_command(command)

    # Aggregate polygons so we have a result on the parcel level...
    #-------------------------------------
    lvhelper.log("Aggregate on object code and crop")
    command = 'ogr2ogr --config OGR_SQLITE_CACHE 200 --config OGR_SQLITE_SYNCHRONOUS OFF -f SQLite -dsco SPATIALITE=YES -gt 200000 -update "{out_file}" "{in_file}" -nln {out_layername} -dialect sqlite -sql "SELECT ST_Union(geometry) AS geometry, {in_parcel_columns}, max(sum_risk) AS max_risk, sum(sum_risk) AS prc_risk, avg(avg_growth) AS avg_growth, min(min_growth) AS min_growth FROM {in_layername} GROUP BY {in_parcel_columns}"'.format(out_file=inter_prc_ineligible_adj_filtered_aggr, in_file=inter_prc_ineligible_adj_filtered, out_layername=inter_prc_ineligible_adj_filtered_aggr_layername, in_parcel_columns=parcels_input_columns, in_layername=inter_prc_ineligible_adj_filtered_layername)
    lvhelper.run_command(command)
else:
    lvhelper.log('    -> SKIP, tmp output file exists already: {0}'.format(inter_prc_ineligible_adj_filtered)) 

# Convert the ineligible pixel polygons to output file, and reproject if needed
#-------------------------------------
inelligible_poly_out_layername = os.path.splitext(os.path.split(inelligible_poly_out)[1])[0].replace('-', '_').replace(' ', '_')
if not os.path.exists(inelligible_poly_out):
    lvhelper.log("Convert to output file format and reproject if needed...")
    command = 'ogr2ogr -s_srs {in_proj} -t_srs {out_proj} "{out_file}" "{in_file}" -nln "{out_layername}" -sql "SELECT * FROM {in_layername}"'.format(in_proj=growthfactor_proj, out_proj=parcels_input_proj, out_file=inelligible_poly_out, in_file=inter_prc_ineligible_adj_filtered_aggr, out_layername=inelligible_poly_out_layername, in_layername=inter_prc_ineligible_adj_filtered_aggr_layername)
    lvhelper.run_command(command)

    # Add column with total area of potential ineligible elements
    lvhelper.log("Add column area_tot to polygon file")
    command = 'ogrinfo "{in_file}" -sql "ALTER TABLE {layername} ADD COLUMN area_tot REAL"'.format(in_file=inelligible_poly_out, layername=inelligible_poly_out_layername)
    lvhelper.run_command(command)
    command = 'ogrinfo "{in_file}" -dialect SQLite -sql "UPDATE {layername} SET area_tot = ST_Area(GEOMETRY) WHERE area_tot IS NULL"'.format(in_file=inelligible_poly_out, layername=inelligible_poly_out_layername)
    lvhelper.run_command(command)
else:
    lvhelper.log('    -> SKIP, output file exists already: {0}'.format(inelligible_poly_out)) 

