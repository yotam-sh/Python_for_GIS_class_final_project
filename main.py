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
