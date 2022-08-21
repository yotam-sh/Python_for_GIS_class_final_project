"""
This script was written by Yotam Shavit

The script was requested by a friend of mine for repetitive data conversion tasks.
The data input is always the same - municipal data that includes the following layers;
roads-polyline # buildings-point # blocks-polygon

What the script essentially does is as follows:
1. Evaluates the data for incompleteness, meaning that any feature without complete attributes will not be valid
2. Adding geometry attributes
3. Creating a database with templates from the existing layers
4. Append valid data to it, combining data from different folders into one workspace
5. Renaming featureclass layers according to their containing folder and original name
6. Spatial-joinig buildings and blocks layers to populate a newly created field - 'new_number' """


""" imports """
import arcpy
from time import process_time


# Document start time in-order to calculate Run Time
time1 = process_time()


""" stage 1 - getting user parameters and setting the script's environment """

arcpy.env.overwriteOutput = True

# Get user parameter for parent-folder
path = arcpy.GetParameterAsText(0)

# Set user defined path as workspace
parent_dir = arcpy.env.workspace = path
parent_desc = arcpy.Describe(parent_dir)


""" stage 2 - create work gdb, start analyzing the data """

# Create a new geodatabase with the name of the parent folder
try:
    new_gdb = arcpy.management.CreateFileGDB(path, parent_desc.name)
except Exception as e:
    arcpy.AddError(f'An error has occured while trying to create a GDB. Error code: {e}')
else:
    arcpy.AddMessage('Created GDB successfully')

# Dictionary to hold every layer's name and path
layer_dict = dict()

# iterate over child dirs in parent dir
for child_dir in arcpy.ListFiles():
    
    # set new path for a new file list per child dir
    new_path = rf'{path}\{child_dir}'
    arcpy.env.workspace = new_path
    
    # Find .shp files and add them to a list
    child_files = list()
    try:
        child_walk = arcpy.da.Walk(new_path, datatype="FeatureClass", type=("Polygon", "Polyline", "Point"))
        for dirpath, dirnames, filenames in child_walk:
            for filename in filenames:
                if filename.endswith(".shp"):
                    child_files.append(rf'{dirpath}\{filename}')
    except Exception as e:
        arcpy.AddError(
            """An error has occured during the search for shapefiles in the parent folder.
            please check the input path for the parent folder. Error code: {e}"""
            )
        break
    else:
        arcpy.AddMessage('Successfully found shapefile(s)')
            
    for file in child_files:
        # Loop through all .shp files and find polyline layers to add geometry values to
        child_fdesc = arcpy.Describe(file)
        f_shape = child_fdesc.shapeType
        f_name = child_fdesc.name
        
        # Add geometry attributes and round all values
        if f_shape == 'Polyline':
            try:
                arcpy.management.AddGeometryAttributes(file, 'LENGTH', 'METERS')
                with arcpy.da.UpdateCursor(file, ['LENGTH']) as cursor:
                    for feature in cursor:
                        rounded_length = int(feature[0])
                        feature[0] = rounded_length
                        cursor.updateRow(feature)
            except Exception as e:
                arcpy.AddError(f'An error has occured in adding geometry values to {f_name}. Error code: {e}')
            else:
                arcpy.AddMessage(f'Succcessfully added geometry values to {f_name}')
        elif f_shape == 'Point':
            try:
                arcpy.management.AddGeometryAttributes(file, 'POINT_X_Y_Z_M')
                arcpy.management.AddField(file, 'new_number', 'TEXT')
                with arcpy.da.UpdateCursor(file, ['POINT_X', 'POINT_Y']) as cursor:
                    for feature in cursor:
                        rounded_x = int(feature[0])
                        rounded_y = int(feature[1])
                        feature[0] = rounded_x
                        feature[1] = rounded_y
                        cursor.updateRow(feature)
            except Exception as e:
                arcpy.AddMError(f'An error has occured in adding geometry values to {f_name}. Error code: {e}')
            else:
                arcpy.AddMessage(f'Succcessfully added geometry values to {f_name}')
                arcpy.AddMessage(f'Succcessfully added "new_number" field to {f_name}')
        elif f_shape == 'Polygon':
            try:
                arcpy.management.AddGeometryAttributes(file, 'AREA', Area_Unit='SQUARE_METERS')
                with arcpy.da.UpdateCursor(file, ['POLY_AREA']) as cursor:
                    for feature in cursor:
                        rounded_area = int(feature[0])
                        feature[0] = rounded_area
                        cursor.updateRow(feature)
            except Exception as e:
                arcpy.AddError(f'An error has occured in adding geometry values to {f_name}. Error code: {e}')
            else:
                arcpy.AddMessage(f'Succcessfully added geometry values to {f_name}')
        
        # Get shapefile path parameter and create a new FC from the current file template
        sys_path = child_fdesc.path
        
        # Add path and layer names to dict
        if sys_path in layer_dict:
            layer_dict[sys_path].append(child_fdesc.name)
        else:
            layer_dict[sys_path] = [child_fdesc.name]
            
        split_dir_name = sys_path.split('\\')
        new_fname = f'{split_dir_name[-1]}_{child_fdesc.name[:-4]}'
        try:
            new_fc = arcpy.management.CreateFeatureclass(new_gdb, new_fname, f_shape, template=file, spatial_reference=file)
        except Exception as e:
            arcpy.AddError(
                f"""The following error has occured during the creation of {new_fname} featureclass: {e}
                Please try rerunning the process after checking for possible error causes."""
                )


""" stage 3 - append features from .shp files to featureclasses """

# reset workspace to initial workspace
parent_dir = arcpy.env.workspace = path

# Iterate over all featureclasses in the created gdb
try:
    gdb_children = arcpy.Describe(new_gdb).children
    for fc in gdb_children:
        
        # Describe each featureclass in each iteration
        fc_path = f'{arcpy.Describe(new_gdb).name}\\{fc.name}'
        fc_desc = arcpy.Describe(fc_path)
        fc_shape = fc_desc.shapeType
        fc_name = fc_desc.name
        
        # Iterate over the created dictionary to match each fc with its counterpart .shp
        for k, v in layer_dict.items():
            for f in v: # f is feature
                
                # Describe the shapefile in order to compare it to the featureclass
                key_split = k.split('\\')
                shp_path = f'{k}\\{f}'
                shp_desc = arcpy.Describe(shp_path)
                shp_name = f'{key_split[-1]}_{f[:-4]}'
                shp_shape = shp_desc.shapeType
                
                if shp_name == fc_name and fc_shape == shp_shape:
                    
                    # Append the .shp to the featureclass with a specific expression to each shape type
                    if fc_shape == 'Point':
                        sql = 'bnumber <> 0 And height <> 0 And apartments <> 0'
                    elif fc_shape == 'Polyline':
                        sql = "(st_name IS NOT NULL And st_name <> ' ') And (LENGTH > 10 And LENGTH < 500)"
                    elif fc_shape == 'Polygon':
                        sql = 'number <> 0'
                        
                    arcpy.management.Append(shp_path, fc_path, schema_type='TEST_AND_SKIP', expression=sql)
except Exception as e:
    arcpy.AddError(
        f"""An error has occured during data transfer between the shapefile to the matching featureclass.
        Please check active data queries on layers.
        Error code: {e} | Shapefile: {shp_name} | Featureclass: {fc_name}"""
        )
else:
    arcpy.AddMessage('Successfully appended all data from shapefiles to featureclasses')
        

""" stage 4 - spatial join data prep """

# Loop through the featureclass list of the created gdb to remove the polyline layers
for fc_index in range(len(gdb_children), -1, -1):
    index = fc_index - 1
    if gdb_children[index].shapeType == 'Polyline':
        try:
            gdb_children.pop(index)
        except Exception as e:
            arcpy.AddError(e)


""" stage 5 - spatial join execution """

# Reset workspace to be the GDB
arcpy.env.workspace = fr'{arcpy.Describe(new_gdb).path}\\{arcpy.Describe(new_gdb).name}'

index = 0
for i in range(len(gdb_children) // 2):
    # Define index iterations --> always // 2
    if index == 0 :
        i = index
    else:
        index += 1
        i = index
    
    # Get first hit city name and layer name
    fc_name_split = gdb_children[i].name.split('_')
    if len(fc_name_split) > 2:
        layer_name = fc_name_split[-1]
        fc_name_split.pop(-1)
        city_name = '_'.join(fc_name_split)
    else:
        city_name = fc_name_split[0]
        layer_name = fc_name_split[1]
    
    # Get matching layer parameter
    for j in gdb_children:
        if city_name in j.name:
            if f'{city_name}_{layer_name}' == j.name:
                pass
            else:
                matching_layer = j.name
        
    
    for layer in [f'{city_name}_{layer_name}', matching_layer]:
        if 'buildings' in layer.lower():
            buildings = layer
        elif 'blocks' in layer.lower():
            blocks = layer
            
    # Execute spatial join
    with arcpy.da.SearchCursor(blocks, 'number') as cursor:
        for block in cursor:
            sql_clause = f'number = {block[0]}'
            arcpy.management.SelectLayerByAttribute(blocks, 'NEW_SELECTION', where_clause=sql_clause)
            
            try:
                sj = arcpy.analysis.SpatialJoin(buildings, blocks, f'in_memory/sj_{city_name}_block{block[0]}', match_option='INTERSECT')
            except Exception as e:
                arcpy.AddError(f'Error while trying to spatial-join [{buildings}, {blocks}] layers, error: {e}')
            else:
                arcpy.AddMessage(f'Successfully spatial-joined [{buildings}, {blocks}] layers')
            
            # Save building numbers of overlapping buildings with current block in selection
            sj_dict = dict()
            with arcpy.da.SearchCursor(sj, ['bnumber', 'new_number', 'number']) as sjcursor:
                for sjrow in sjcursor:
                    if sjrow[2] == block[0]:
                        if sjrow[2] in sj_dict:
                            sj_dict[sjrow[2]].append(sjrow[0])
                        else:
                            sj_dict[sjrow[2]] = [sjrow[0]]
            
            if sj_dict:
                with arcpy.da.UpdateCursor(buildings, ['bnumber', 'new_number']) as bcursor:
                    for k, v in sj_dict.items():
                        for brow in bcursor:
                            for subv in v:
                                if brow[0] == subv:
                                    try:
                                        # Populate 'new_number' field with building # and block #
                                        brow[1] = f'BL{k}#{brow[0]}'
                                        bcursor.updateRow(brow)
                                    except Exception as e:
                                        arcpy.AddError(f'Error while populating new field after spatial-join, error: {e}')
            
            # Clear selection
            arcpy.management.SelectLayerByAttribute(blocks, 'CLEAR_SELECTION')
            
            # Delete spatial-join memory layer
            try:
                sj_layer_name = arcpy.Describe(sj).name
                arcpy.Delete_management(sj)
            except Exception as e:
                arcpy.AddError(f'Error while deleting spatial-join layer {arcpy.Describe(sj).name}, error: {e}')
            else:
                arcpy.AddMessage(f'Successfully deleted {sj_layer_name} layer')
        
    index += 1    


""" stage 6 - end stage """

# End-time variable
time2 = process_time()

# Run-time in second
runtime = (time2-time1)

arcpy.AddMessage(f'The tool ran for {runtime} seconds')