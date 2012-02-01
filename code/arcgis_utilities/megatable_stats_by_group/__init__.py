'''	
	Written by Nick Santos - Jan 31, 2012
	
	Purpose: Given a set of tables and portions of column names, this script groups columns that have those portions in their name (so 'apr' puts 'pck_apr1980' into a group)
	Then, for each table we get the mean and standard deviation for each of those groups and add those as columns to the original table
	
	Note that I am incredibly tired as I write this and have a terrible feeling that I've made some poor design choices. If you're looking
	at something and thinking "that could have been done so much better if...That's why.

'''

import os
import sys

try:
	import arcpy
except:
	print "You must be on a computer with ArcGIS 10 installed and a license available"
	raise

try:
	import scipy
except:
	print "Your Python installation must have a version of scipy installed"
	raise

class table:
	def __init__(self):
		self.name = None
		self.table = None
		self.groups = []

class group:
	def __init__(self):
		self.name = None
		self.columns = []
		self.col_parts = []
		self.data = [] # doesn't actually need to be associated with the columns here
		self.col_name_base = None # assigned by the script - references the appropriate column in the data file after it's created - true col names include _mean or _std at the end
		
		
input_tables = arcpy.GetParameter(0)
input_groups = arcpy.GetParameter(1)
run_mean = arcpy.GetParameter(2)
run_std = arcpy.GetParameter(3)

if not run_mean and not run_std:
	arcpy.AddError("You haven't selected any stats to run. You're just trying to make me churn through data doing busywork - I get it. Please select at least one statistic in the parameters. Exiting")
	sys.exit()	

group_specs = []
all_groups = []

def input_tables_to_list(inputs):
	num_rows = inputs.rowCount
	cur_row = 0
	new_list = []
	
	while cur_row  < num_rows:
		new_list.append(inputs.getRow(cur_row))
	
	return new_list

		
def arc_groups_to_lists(arc_value_table):
	'''arcgis uses a custom format called a ValueTable - this function converts this valuetable input to a list of lists'''
	
	groups = []
	
	num_groups = arc_value_table.rowCount
	cur_row = 0
	
	while cur_row  < num_groups:
		temp_row = arc_value_table.getRow(cur_row)
		groups.append(temp_row.split(','))
		cur_row += 1
		
	return groups

def make_groups(tables,groups):
	all_tables = []
	for table in tables:
		l_table = table()
		l_table.table = table
		
		ids = 1
		for group in groups:
			l_group = group()
			l_group.col_parts = group # assign the input parts here
			l_group.name = ids
			ids += 1
			l_table.groups.append(l_group)
		
		all_tables.append(l_table)

	return all_tables

def assign_columns_to_groups(tables):
	for table in tables: # for every table
		table_fields = arcpy.ListFields(table.table) # get the columns for the table
		for field in table_fields: # for every field
			for group in table.groups: # look in the column parts for the group
				for item in group.col_parts:
					if field.find(item) > -1: # if that item is present in the field name
						group.columns.append(field) # then add that field to the group's info
						
def load_and_process_data(tables):						
	for table in tables:
		for group in table.groups: # add the columns
			group.col_name_base = "group_%s_%s" % (group.name,group.col_parts[0])
			arcpy.AddField_management(table.table,"%s_mean" % group.col_name_base,"DOUBLE")
			arcpy.AddField_management(table.table,"%s_std" % group.col_name_base,"DOUBLE")			
			
			l_curs = arcpy.UpdateCursor(table.table)
			for row in l_curs:
				t_row_data = []
				for col in group.columns:
					t_row_data.append(row.getValue(col))
				group.data.append(t_row_data)
				
				t_sci_array = scipy.array(t_row_data)
				row.setValue("%s_mean" % group.col_name_base,t_sci_array.mean)
				row.setValue("%s_std" % group.col_name_base,t_sci_array.std)
			
				row.updateRow()
			del row
			del l_curs


input_tables = input_tables_to_list(input_tables) # do some data conversion
input_groups = arc_groups_to_lists(input_groups) # do some data conversion
all_tables = make_groups(input_tables,input_groups) # make the group objects for the tables and columns
assign_columns_to_groups(all_tables) # load the columns from each table and assign columns to groups based upon names
load_and_process_data(all_tables)

arcpy.AddMessage("Complete - the columns were added to the existing tables")
