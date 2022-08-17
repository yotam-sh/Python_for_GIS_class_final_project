##### This script was written by Yotam Shavit

### The script was written for repetitive data conversion tasks for a friend.
### The data input is always the same - municipal data that includes the following layers;
### roads-polyline # buildings-point # blocks-polygon
###
### What the script essentially does is as follows:
### 1. Evaluates the data for incompleteness, meaning that any feature without complete attributes will not be valid
### 2. Adding geometry attributes to the road layer, calculating road feature part lengths
### 3. Creating a database and transferring all data to it, combining data from different folders into one workspace
### 4. Renaming featureclass layers according to their containing folder and original name
### 5. Cutting all data outside of an AOI polygon supplied by the user

# imports
import arcpy
import os

###
### stage 1 - getting user parameters and setting the script's environment
###

arcpy.env.overwriteOutput = True

# Get all user parameteres
path = r'C:\Users\user\Desktop\PythonForUni\Final_project\testing_parent' #arcpy.GetParameterAsText(0) # get parent dir
# try:
#     work_area_parameter = arcpy.GetParameterAsText(1) # Polygonal layer 
#     p1_desc = arcpy.Describe(work_area_parameter)
#     if p1_desc.shapeType != "Polygon":
#         raise TypeError
# except TypeError:
#     arcpy.AddError('A polygonal layer must be used for the work area parameter!')

parent_dir = arcpy.env.workspace = path
parent_desc = arcpy.Describe(parent_dir)

###
### stage 2 - create work gdb, start analyzing the data
###

# Create a new geodatabase with the name of the parent folder
# new_gdb = arcpy.management.CreateFileGDB(path, parent_desc.name)

# Dictionary to hold every layer's name and path
layer_dict = dict()

# iterate over child dirs in parent dir
for child_dir in arcpy.ListFiles():
    
    # set new path for a new file list per child dir
    new_path = rf'{path}\{child_dir}'
    arcpy.env.workspace = new_path
    
    # Find .shp files and add them to a list
    child_files = list()
    child_walk = arcpy.da.Walk(new_path, datatype="FeatureClass", type=("Polygon", "Polyline", "Point"))
    for dirpath, dirnames, filenames in child_walk:
        for filename in filenames:
            if filename.endswith(".shp"):
                child_files.append(rf'{dirpath}\{filename}')
            
    for file in child_files:
        # Loop through all .shp files and find polyline layers to add geometry values to
        child_fdesc = arcpy.Describe(file)
        f_shape = child_fdesc.shapeType
        
        # Add geometry attributes and round all values
        if f_shape == 'Polyline':
            arcpy.management.AddGeometryAttributes(file, 'LENGTH', 'METERS')
            with arcpy.da.UpdateCursor(file, ['LENGTH']) as cursor:
                for feature in cursor:
                    rounded_length = int(feature[0])
                    feature[0] = rounded_length
                    cursor.updateRow(feature)
        elif f_shape == 'Point':
            arcpy.management.AddGeometryAttributes(file, 'POINT_X_Y_Z_M')
            arcpy.management.AddField(file, 'new_number', 'TEXT')
            with arcpy.da.UpdateCursor(file, ['POINT_X', 'POINT_Y']) as cursor:
                for feature in cursor:
                    rounded_x = int(feature[0])
                    rounded_y = int(feature[1])
                    feature[0] = rounded_x
                    feature[1] = rounded_y
                    cursor.updateRow(feature)
        elif f_shape == 'Polygon':
            arcpy.management.AddGeometryAttributes(file, 'AREA', Area_Unit='SQUARE_METERS')
            with arcpy.da.UpdateCursor(file, ['POLY_AREA']) as cursor:
                for feature in cursor:
                    rounded_area = int(feature[0])
                    feature[0] = rounded_area
                    cursor.updateRow(feature)
        
        # Get parameters and create a new FC from the current file template
        sys_path = os.path.dirname(file)
        
        # Add path and layer names to dict
        if sys_path in layer_dict:
            layer_dict[sys_path].append(child_fdesc.name)
        else:
            layer_dict[sys_path] = [child_fdesc.name]
            
        split_dir_name = sys_path.split('\\')
        new_fname = f'{split_dir_name[-1]}_{child_fdesc.name[:-4]}'
        # new_fc = arcpy.management.CreateFeatureclass(new_gdb, new_fname, f_shape, template=file, spatial_reference=file)

# # Show dict items sorted by "CITY: {} | LAYER NAME: {}"
# for k, v_list in layer_dict.items():
#     for v in v_list:
#         k_split = k.split('\\')
#         print(f'City: {k_split[-1]}\t| Layer name: {v}')
            
# reset workspace to initial workspace
parent_dir = arcpy.env.workspace = path

# Iterate over all featureclasses in the created gdb
for fc in arcpy.Describe(new_gdb).children:
    
    # Describe each featureclass in each iteration
    fc_path = f'{arcpy.Describe(new_gdb).name}\\{fc.name}'
    fc_desc = arcpy.Describe(fc_path)
    fc_shape = fc_desc.shapeType
    fc_name = fc_desc.name
    
    # Iterate over the created dictionary to match each fc with its counterpart .shp
    for k, v in layer_dict.items():
        for f in v: # f is feature
            key_split = k.split('\\')
            shp_name = f'{key_split[-1]}_{f[:-4]}'
            
            if shp_name == fc_name:
                shp_path = f'{k}\\{f}'
            
                # Append the .shp to the featureclass with a specific expression to each shape type
                if fc_shape == 'Point':
                    sql = 'number <> 0 And height <> 0 And apartments <> 0'
                elif fc_shape == 'Polyline':
                    sql = "(st_name IS NOT NULL And st_name <> ' ') And (LENGTH > 10 And LENGTH < 500)"
                elif fc_shape == 'Polygon':
                    sql = 'number <> 0'
                    
                arcpy.management.Append(shp_path, fc_path, schema_type='TEST_AND_SKIP', expression=sql)