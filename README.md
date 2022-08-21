# Python_for_GIS_class_final_project

The script was requested by a friend of mine for repetitive data conversion tasks.
The data input is always the same - municipal data that includes the following layers;
roads-polyline # buildings-point # blocks-polygon

What the script essentially does is as follows:
1. Evaluates the data for incompleteness, meaning that any feature without complete attributes will not be valid
2. Adding geometry attributes
3. Creating a database with templates from the existing layers
4. Append valid data to it, combining data from different folders into one workspace
5. Renaming featureclass layers according to their containing folder and original name
6. Spatial-joinig buildings and blocks layers to populate a newly created field - 'new_number'
