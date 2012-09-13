'''
Created on Aug 28, 2012

@author: nicksantos
'''
import os
import traceback

import arcpy

import code_library
from code_library.common import log
from code_library.common.geospatial import core as geospatial

def centroid_distance(features = [],spatial_reference = None,max_distance=None):
	
	'''takes multiple input feature classes, retrieves the centroids of every polygon as points, and writes those points to a file, before running
		PointDistance_analysis() on the data. It returns the out_table given by Point Distance. This is most predictable when two feature classes with a single feature
		are provided. all features must be in the same spatial reference
	'''
	
	if not code_library.isiterable(features):
		raise ValueError("'features' must be an iterable in centroid_distance")
	
	if len(features) == 0:
		raise ValueError("No features to run centroid distance on")
		
	if spatial_reference is None:
		raise ValueError("Spatial Reference cannot be None")
	
	all_centroids = []
	for feature in features:
		try:
			all_centroids += get_centroids(feature) # merge, don't append
		except:
			continue 
	
	point_file = write_features_from_list(all_centroids, "POINT",spatial_reference = spatial_reference)
	log.write("Point File located at %s" % point_file)
	out_table = geospatial.generate_gdb_filename(return_full=True)
	log.write("Output Table will be located at %s" % out_table)
	
	try:
		arcpy.PointDistance_analysis(point_file,point_file,out_table,max_distance)
	except:
		log.error("Couldn't run PointDistance - %s" % traceback.format_exc())
	
	return out_table

def simple_centroid_distance(feature1,feature2,spatial_reference):
	'''wraps centroid_distance and requires that each feature only has 1 polygon in it. Returns the distance value instead of the table. Doesn't check
		whether or not each file has only one polygon, so it will return the FIRST distance value in the out_table, regardless of what it actually is. Don't use this unless you
		are sure you can pass in the correct data'''

	if not feature1 or not feature2:
		raise ValueError("feature1 or feature2 is not defined")
	
	out_table = centroid_distance((feature1,feature2),spatial_reference)
	
	reader = arcpy.SearchCursor(out_table)
	
	distance = None
	for row in reader:
		distance = row.getValue("DISTANCE")
	
	del reader
	
	log.write("Centroid Distance is %s" % distance)
	return distance
	

def write_features_from_list(data = None, data_type="POINT",filename = None,spatial_reference = None):
	'''takes an iterable of feature OBJECTS and writes them out to a new feature class, returning the filename'''	
	
	if not spatial_reference:
		log.error("No spatial reference to write features out to in write_features_from_list")
		return False
	
	if not data:
		log.error("Input data to write_features_from_list does not exist")
		return False
	
	if not code_library.isiterable(data): # check if exists and that it's Iterable
		log.error("Input data to write_features_from_list is not an Iterable. If you have a single item, pass it in as part of an iterable (tuple or list) please")
	
	filename = geospatial.check_spatial_filename(filename,create_filename = True,allow_fast=False)
	
	if not filename:
		log.error("Error in filename passed to write_features_from_list")
		return False
	
	data_types = ("POINT","MULTIPOINT","POLYGON","POLYLINE")
	if not data_type in data_types:
		log.error("data_type passed into write_features from list is not in data_types")
		return False
	
	path_parts = os.path.split(filename)
	log.write(str(path_parts))
	arcpy.CreateFeatureclass_management(path_parts[0],path_parts[1],data_type,'','','',spatial_reference)
	
	valid_datatypes = (arcpy.Point,arcpy.Polygon,arcpy.Polyline,arcpy.Multipoint)
	
	log.write("writing shapes to %s" % filename)
	inserter = arcpy.InsertCursor(filename)
	primary_datatype = None
	
	log.write("writing %s shapes" % len(data))
	#i=0
	for feature_shape in data:
		cont_flag = True # skip this by default if it's not a valid datatype
		if primary_datatype:
			if isinstance(feature_shape,primary_datatype):
				cont_flag = False
		else:
			for dt in valid_datatypes:
				if isinstance(feature_shape,dt):
					cont_flag = False # check the object against all of the valid datatypes and make sure it's a class instance. If so, set this to false so we don't skip this feature
					primary_datatype = dt # save what the datatype for this file is
		if cont_flag:
			log.warning("Skipping a feature - mixed or unknown datatypes passed to write_features_from_list")
			continue
		try:
			in_feature = inserter.newRow()
			in_feature.shape = feature_shape
			#i+=1
			#in_feature.rowid = i
			inserter.insertRow(in_feature)
		except:
			log.error("Couldn't insert a feature into new dataset")
			continue
		
	del feature_shape
	del inserter
	
	return filename
	
def get_centroids(feature = None,method="FEATURE_TO_POINT"):
	
	methods = ("FEATURE_TO_POINT","ATTRIBUTE",) #"MEAN_CENTER","MEDIAN_CENTER")
	
	if not method in methods:
		log.warning("Centroid determination method is not in the set %s" % methods)
		return []
	
	if not feature:
		raise NameError("get_centroids requires a feature as input")
	
	if not check_type(feature,"Polygon"):
		log.warning("Type of feature in get_centroids is not Polygon")
		return []

	if method == "ATTRIBUTE":
		points = centroid_attribute(feature)
	elif method == "FEATURE_TO_POINT":
		try:
			points = centroid_feature_to_point(feature)
		except:
			err_str = traceback.format_exc()
			log.warning("failed to obtain centroids using feature_to_point method. traceback follows:\n %s" % err_str)
				
	return points

def centroid_attribute(feature = None):
	'''for internal use only - gets the centroid using the polygon attribute method - if you want to determine centroids, use get_centroids()'''
	
	curs = arcpy.SearchCursor(feature)
	
	points = []
	for record in curs:
		points.append(record.shape.centroid)
	
	return points

def centroid_feature_to_point(feature):
	t_name = geospatial.generate_fast_filename()
	
	arcpy.FeatureToPoint_management(feature, t_name,"CENTROID")
		
	curs = arcpy.SearchCursor(t_name) # open up the output
	
	points = []
	for record in curs:
		points.append(record.shape.getPart()) # get the shape's point
		
	return points

def get_centroids_as_file(feature=None,filename = None,spatial_reference = None):
	'''shortcut function to get the centroids as a file - called functions do error checking'''
	
	try:
		cens = get_centroids(feature)
		if (len(cens) > 0):
			return write_features_from_list(cens,data_type="POINT",filename=filename,spatial_reference=spatial_reference)
		else:
			return None
	except:
		err_str = traceback.format_exc()
		log.error("Couldn't get centroids into file - traceback follows:\n %s" % err_str)
	
def check_type(feature = None ,feature_type = None,return_type = False):

	if not feature:
		log.warning("no features in check_type")
		return False
	
	if not feature_type:
		log.warning("no data_type(s) to check against in ")
		return False
	
	desc = arcpy.Describe(feature)
	
	if desc.dataType == "FeatureClass" or desc.dataType =="FeatureLayer":
		read_feature_type = desc.shapeType
	else:
		log.error("feature parameter supplied to 'check_type' is not a FeatureClass")
		del desc
		return False
	
	del desc
	
	if return_type:
		return read_feature_type
	
	if code_library.isiterable(feature): # if it's an iterable and we have multiple values for the feature_type, then check the whole list
		if read_feature_type in feature_type:
			return True
	elif read_feature_type == feature_type: # if it's a single feature, just check them
		return True	
	
	return False # return False now
	