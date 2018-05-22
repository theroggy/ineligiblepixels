Description
---------------------
This is a QGIS 2.X tool to search for ineligible pixels in agricultural parcels.

The script doesn't search for all kinds of ineligible pixels, it searches for pixels that don't show any growth through the entire growing season.

The more images during the growing season, the better the result.

Remarks:
- vegetable parcels in Flanders gave too many false positives, so they were excluded.


Installation
---------------------
This procedure hasn't been properly tested, so might contain errors. Ask help if it goes wrong...

1) Install QGIS 2.X, eg. using https://trac.osgeo.org/osgeo4w/
2) Install Orfeo Toolbox from https://www.orfeo-toolbox.org
3) Copy Lib_LVHelper.py, TLDClass_Create_ineligible_layer.py and TLDClass_Create_ineligible_layer.py.help to the folder used by QGIS to put the custom tools. 
   You can check where this location is by going to "Processing"/"Options..."/"Scripts"/"Script folder"
4) When you restart QGIS, the tool "TLDClass Create ineligible layer" should be available in the toolbox in the section "Scripts".
5) Right-click the tool, choose edit, and update the following lines:
    - sys.path.append('C:\\Projects\\ANG_GIS\\GISScripts\\QGIS_tools') 
		-> the path should be the path to where the QGIS scripts are located now.
	- OTB_BIN = 'X:\\GIS\\Software\\_Progs\\OTB-6.0.0-win64\\bin' 
		-> the path should be the location where you installed Orfeo Toolbox.