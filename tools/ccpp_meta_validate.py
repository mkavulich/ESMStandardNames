#!/usr/bin/env python3

"""

This tool checks CCPP metadata files to validate that names, units, and other fields are correct
The tool can accept a path to a single metadata file, or a directory (which will be searched
recursively) containing one or more metadata files.

"""

######################################
#Import needed standard python modules
######################################

import argparse
import datetime
import os
import os.path
import re
import string
import sys
from collections import OrderedDict

################################################
# Add lib modules to python path
################################################

_CURR_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_CURR_DIR, "lib"))

#######################################
#Import needed framework python modules
#######################################

from xml_tools import read_xml_file

#################
#Helper functions
#################

#++++++++++++++++++++++++++++++
#Input Argument parser function
#++++++++++++++++++++++++++++++

def parse_arguments():

    """
    Parses command-line input arguments
    using the argparse python module and
    outputs the final argument object.
    """

    #Create description:
    desc = "Check if the metafile contains variable standard names\n"
    desc += "that are not in the provided standard names dictionary."

    #Create parser object:
    parser = argparse.ArgumentParser(description=desc)

    #Add input arguments to be parsed:
    parser.add_argument('-m', '--metafile-loc', required=True,
                        metavar='<path to directory or file>',
                        action='store', type=str,
                        help="Location of metadata file(s)")

    #Parse Argument inputs
    args = parser.parse_args()

    return args.metafile_loc

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#Function to extract standard names from element tree root
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def get_dict_stdnames(xml_tree, std_dict_names=set()):

    """
    Extract all elements with the "standard_name" tag,
    find the "name" attribute for that tag, and collect
    all of those "names" in a set.
    """

    # Recurse over subsections

    for section in  xml_tree.findall('./section'):
        std_dict_names.union(get_dict_stdnames(section,std_dict_names))
    # Loop over all standard_name tags"
    for stdname in xml_tree.findall('./standard_name'):
        #Add the "name" attribute to the set:
        std_dict_names.add(stdname.attrib['name'])
    #End for

    return std_dict_names

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#Function to parse a metadata file and return a dictionary
#of variables from that file
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def extract_metadata_dict(metafile):

    """
    Using the assumed standard format of CCPP metadata files, 
    parse the metadata file for all the defined variables,
    and return them as a dictionary of properties:

    dict[table][varname][propname]

    Where propname is one of:
    'standard_name'
    'long_name'
    'units'
    'dimensions'
    'type'

    """

    metadict={}
    table_name=''

    #Open metadata file:
    with open(metafile,'r', encoding='utf-8') as mfile:

        while line:=mfile.readline():
            # We first look for the start of a metadata table
            if line.strip() == "[ccpp-arg-table]":
                # Read the next line, which should be the name of the table
                line=mfile.readline()
                if line.lstrip().startswith("name"):
                    table_name=get_assignment(line).strip()
                    #print(f"{table_name=}")
                    # Start the next dictionary entry for this table
                    metadict[table_name] = {}
                    # Skip the next line, which should be the table type
                    mfile.readline()

            else:
                continue

            # Now that we are inside a table, loop until we find the end of the section, marked by
            # a line of octothorpe (#) characters

            local_name=''
            while line:=mfile.readline():

                if line.startswith("####"):
                    break
                #Check if line starts with "[": this indicates a table or variable definition
                if line.startswith("["):
                    # Use regex to extract string in brackets
                    local_name = re.search('\[(.*)\]', line).group(1)
#                    print(f"{local_name=}")
                    metadict[table_name][local_name]={}
                elif line.lstrip().startswith("standard_name"):
                    metadict[table_name][local_name]["standard_name"]=get_assignment(line).strip()
                elif line.lstrip().startswith("long_name"):
                    metadict[table_name][local_name]["long_name"]=get_assignment(line).strip()
                elif line.lstrip().startswith("units"):
                    metadict[table_name][local_name]["units"]=get_assignment(line).strip()
                elif line.lstrip().startswith("dimensions"):
                    metadict[table_name][local_name]["dimensions"]=get_assignment(line).strip()
                elif line.lstrip().startswith("type"):
                    metadict[table_name][local_name]["type"]=get_assignment(line).strip()

#            print(f"{metadict=}")

    return metadict


def get_assignment(string):
    """Given a string with an assignment operator (=), returns all the text to the right of =

    For example, the string

        name = this name

    will return

        this name
    """

    output=''
    equals_index = string.find("=")

    if equals_index != -1:

        output = string[equals_index+1:]

        #Attempt to find the index for a comment delimiter:
        comment_index = output.find("#")

        #If comment exists, then remove it from output text
        if comment_index != -1:
            output = output[:comment_index]

    return output


#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#Function to find the paths to all metadata files within
#a given directory path
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def find_metadata_files(dir_path):

    """
    Walk through the provided directory
    and create a list of all found CCPP
    metadata files.
    """

    #Create new, empy list to store metadata file paths:
    metadata_files = []

    #Walk through provided directory:
    for root, _, files in os.walk(dir_path):
        #Ignore git directories:
        if '.git' not in root:

            #Find all metadata files in current root location:
            local_meta_files = [mfil for mfil in files if mfil[-5:] == '.meta']


            #Add all found metadata files to metadata list,
            #including their full path:
            for local_file in local_meta_files:
                metadata_files.append(os.path.join(root, local_file))
            #End for
        #End if
    #End for

    #Return list of metadata files:
    return metadata_files


############
#Main script
############

#Parse command-line arguments:
metafile_loc = parse_arguments()

#Create new meta file/missing names dictionary:
meta_miss_names_dict = OrderedDict()

#Check if user passed in single metadata file:
if os.path.isfile(metafile_loc):
    metafiles=[metafile_loc]
elif os.path.isdir(metafile_loc):
    metafiles=find_metadata_files(metafile_loc)
else:
    #This is a non-supported input, so raise an error:
    emsg = f"The metafile-loc arg input, '{metafile_loc}'\n"
    emsg += "is neither a file nor a directory,"
    emsg += " so script will end here."
    raise FileNotFoundError(emsg)

# Some helper test functions

def standardname_allowed(s):
    allowed = set(string.ascii_lowercase + string.digits + '_')
    return all(ch in allowed for ch in s)

def longname_allowed(s):
    allowed = set(string.ascii_letters + string.digits + string.punctuation + " \t\n")
    # This try block ensures that no weird whitespace characters slip through
    try:
        s.encode("ascii")
    except UnicodeEncodeError:
        return False
    return all(ch in allowed for ch in s)

badstuff = {}
questions = {}
for metafile in metafiles:
    metadict=extract_metadata_dict(metafile)
#    print(f"{metadict=}")
    badstuff[metafile]=[]
    questions[metafile]=[]
    for table in metadict:
#        print(f"{table=}")
        for var in metadict[table]:
#            print(f"{var=}")
            # check 1: see if standard_name and long_name contain invalid characters
#            print(f"{metadict[table][var]['standard_name']=}")
            if standardname_allowed(metadict[table][var]['standard_name']):
                if metadict[table][var]['standard_name'][0].isdigit() or metadict[table][var]['standard_name'][0].startswith("_"):
                    badstuff[metafile].append(f"Variable {var} has standard name {metadict[table][var]['standard_name']} with and invalid first character")
            else:
                badstuff[metafile].append(f"Variable {var} has standard name {metadict[table][var]['standard_name']} with invalid characters")

            if longname_allowed(metadict[table][var]['long_name']):
                pass
            else:
                badstuff[metafile].append(f"Variable {var} has long name {metadict[table][var]['long_name']} with invalid characters")

            realunits = [
                "1",
                "cm",
                "d", "days",
                "dBZ",
                "degree",
                "flag",
                "flashes min-1",
                "fraction",
                "g", "g mol-1", "g m-2",
                "h",
                "hPa",
                "J", "J cal-1", "J K-1", "J K-1 mol-1", "J kg-1", "J kg-1 K-1", "J m-2", "J s-1", "J s2 K-1 kg-1 m-1",
                "K", "K kg kg-1", "K m", "K m s-1", "K m-1", "K s-1", "K-1", "K2",
                "kg", "kg kg-1", "kg kg-1 m s-1", "kg kg-1 s-1", "kg m-1 s-2", "kg m-2", "kg m-2 s-1", "kg m-3", "kg-1", "kg-1 s-1", "kg2 kg-2",
                "km", "km-1", "km-2",
                "m", "m s-1", "m s-1 kg kg-1", "m s-2", "m K-1", "m-1", "m-2", "m-3", "m2", "m2 radian-2", "m2 s-1", "m2 s-2", "m2 s-2 K-1", "m2 s-3", "m3", "m3 kg-1", "m3 m-3", "m6 kg-1",
                "min",
                "mm", "mm h-1", "mm s-1",
                "mol", "mol mol-1", "mol-1",
                "MW",
                "Pa", "Pa s", "Pa s-1",
                "percent",
                "radian",
                "radian2 m-2",
                "s", "s m-1", "s-1", "s2 m-1",
                "ug", "ug m-2", "ug m-2 s-1",
                "um",
                "various",
                "W", "W m-2", "W m-2 K-1", "W m-2 K-4", "W m-2 s",
            ]
            intunits = [ "1",
                         "flag",
                         "index",
                         "count",
                       ]
            # check 2: ensure valid unit/type combination
            if metadict[table][var]['type'] == "character":
                if metadict[table][var]['units'] not in ["none"]:
                    badstuff[metafile].append(f"Variable {var} has invalid units {metadict[table][var]['units']} for character type")
            elif metadict[table][var]['type'] == "logical":
                if metadict[table][var]['units'] not in ["flag"]:
                    badstuff[metafile].append(f"Variable {var} has invalid units {metadict[table][var]['units']} for logical type")
            elif metadict[table][var]['type'] == "real":
                if metadict[table][var]['units'] not in realunits:
                    badstuff[metafile].append(f"Variable {var} has invalid units {metadict[table][var]['units']} for real type")
#                if "fraction" in metadict[table][var]['standard_name'] and metadict[table][var]['units'] != "fraction":
#                    questions[metafile].append(f"Variable {metadict[table][var]['standard_name']} has units {metadict[table][var]['units']}, should possibly be 'fraction'")
            elif metadict[table][var]['type'] == "integer":
                if metadict[table][var]['units'] not in intunits:
                    badstuff[metafile].append(f"Variable {var} has invalid units {metadict[table][var]['units']} for integer type")
#                if "index" in metadict[table][var]['standard_name'] and metadict[table][var]['units'] != "index":
#                    questions[metafile].append(f"Variable {metadict[table][var]['standard_name']} has units {metadict[table][var]['units']}, should possibly be 'index'")
#                if "count" in metadict[table][var]['standard_name'] and metadict[table][var]['units'] != "count":
#                    questions[metafile].append(f"Variable {metadict[table][var]['standard_name']} has units {metadict[table][var]['units']}, should possibly be 'count'")
            else:
                print("What type is this? " + metadict[table][var]['type'])

            # check 3: look for potential name/unit mismatches


            # Next: check that names with "fraction" in them have correct units
#for test_string in ["good", "BAD", "V.e,RY% B@D"]:
#    if standardname_allowed(test_string):
#        print(f"{test_string} is good!")
#    else:
#        print(f"{test_string} is bad!")

# Print error report
problems=False
for fn in badstuff:
    if badstuff[fn]:
        problems=True
        print(f"\nProblems found in file {fn}:")
        for item in badstuff[fn]:
            print("    " + item)
#    else:
#        print(f"\nNo problems found in file {fn}!")

qs=False
if not problems:
    print(f"\nAll files passed all checks!")
for fn in questions:
    if questions[fn]:
        qs=True

if qs:
    if problems:
        print(f"Also, some stuff should be double-checked:")
    else:
        print(f"But some stuff should be double-checked:")
    for fn in questions:
        if questions[fn]:
            problems=True
            print(f"\nQuestions in file {fn}:")
            for item in questions[fn]:
                print("    " + item)

