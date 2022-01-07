#!/usr/bin/env python3

import lkml
from lkml.visitors import BasicVisitor
from lkml.tree import BlockNode
import pandas as pd
import json

import glob, os

import argparse
import logging

do_not_process_list = [
        'manifest.lkml'
        ]

class AttributesExtractor(BasicVisitor):
    
    def __init__(self, filename):
        self.headers = ['label', 'description', 'type', 'sql']
        self.out = []
        self.filename = filename

    def visit_block(self, node: BlockNode):
        """For each block, check if it's a dimension and if it has a description."""
        if node.type.value in ['dimension', 'measure']:
            c = {'file' : self.filename, 'field_type' : node.type.value, 'name': node.name.value}
            c.update({n.type.value: n.value.value for n in node.container.children if n.type.value in self.headers}) 
            c.update({h : None for h in self.headers if h not in c.keys()})
            self.out.append(c)

        return self._visit(node)

def export(basepath, output_file):

    # root_dir needs a trailing slash (i.e. /root/dir/)
    basepath = '/Users/raziel.einhorn/WalkMeRepos/looker-templates/views/'

    df = pd.DataFrame()
    
    for filename in glob.iglob(os.path.join(basepath, '**/*.lkml'), recursive=True):
    
        suffix =  os.path.relpath(filename, basepath)
    
        if suffix in do_not_process_list:
            continue
        
        with open(filename) as f:
            file = f.read()
    
        tree = lkml.parse(file)
    
        #DV = AttributesExtractor(suffix)
        DV = Test(suffix)
        
        tree.accept(DV)
        
        d_df = pd.DataFrame(DV.out)
        df = df.append(d_df, ignore_index = True)
        
    
    df.to_csv(output_file, index = False)   
    return


def update_views(basepath, input_file, anchor):

    basepath = '/Users/raziel.einhorn/WalkMeRepos/looker-templates/views'
    proj = lookml.Project(path= basepath)

    df = pd.read_csv(input_file)
    
    for file in proj.view_files():
        
        df_this_file = df[df.file == file.name]

        with open(file.python_path, 'r') as f:
            parsed = lkml.load(f.read())
            try:
                view = lookml.View(parsed)
            except:
                print(file.python_path)
                print(parsed)
                raise Exception()


        parsed['views'][0] = view

        with open(file.python_path, 'w') as f:
            lkml.dump(parsed, f)

def validate_update_config(config):

    if 'basepath' not in config or not os.path.exists(config['basepath']):
        print("Basepath is missing or basepath doesn't exist")
        return False

    if 'update' not in config:
        print("Update configuration missing")
        return False
    
    update_keys = config['update'].keys()

    if 'source_filepath' not in update_keys or not os.path.exists(config['update']['source_filepath']):
        print("Source file path is missing or source file doesn't exist")
        return False

    if 'updated_files_basepath' not in update_keys or not os.path.exists(config['update']['updated_files_basepath']):
        print("updated_file_basepath is missing or path doesn't exist")
        return False

    return True


def update(config):
    
    
    # basepath needs to end with a trailing slash (i.e. /root/dir/)
    #parser.add_argument("-p", "--path", type = str, help="Base path to LookML view files including trailing slash (for example /path/to/repo/views/)")
    
    if not validate_update_config(config):
        return

    basepath = config['basepath']
    source_filename = config['update']['source_filepath']

    df = pd.read_csv(source_filename, keep_default_na=False)
    
    count_files = {'processed': 0, 'modified': 0}

    for filename in glob.iglob(os.path.join(basepath, '**/*.lkml'), recursive=True):
        
        count_files['processed'] = count_files['processed'] + 1 
        suffix =  os.path.relpath(filename, basepath)
        logging.info(suffix)
         
        if suffix in do_not_process_list:
            continue
        
        #TODO: match name in input file to filename based on regex.
        #partial code:
        #if 'use_regex' in self.config and self.config['use_regex']: 
        #    filepath_regex = re.compile(self.config['use_regex'])
        #    file = filepath_regex.match(infilepath).groups()[0]

        df_current_file = df[df.file == suffix]
        
        if df_current_file.size == 0:
            print(f"No update data found in input file for {suffix}, moving to next file")
            continue

        with open(filename) as f:
            lookml_object = lkml.load(f.read())
        
        if 'views' not in lookml_object:
            print("This file has no views") 
            continue

        defs = df_current_file.drop(columns = 'file')
        dim = defs[defs['field_type'] == 'dimension'].drop(columns = 'field_type')
        meas = defs[defs['field_type'] == 'measures'].drop(columns = 'field_type') 

        lookml_object['views'][0]['dimensions'] = list(dim.T.to_dict().values())
        lookml_object['views'][0]['measures'] = list(meas.T.to_dict().values())
         
        outfilepath = os.path.join(config['update']['updated_files_basepath'], suffix)
        with open(outfilepath, 'w') as f:
            lkml.dump(lookml_object, f)
        count_files['modified'] = count_files['modified'] + 1

    
    logging.info(f"Processed: {count_files['processed']} files. Modified: {count_files['modified']} files") 
    return

def load_config_file(path):

    try:
        with open(path, 'r') as f:
            config = json.load(f)
    except:
        raise IOError("Can't open config file")

    return config

def parse_arguments():
    """
    Command line arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--export", help="export attributes to a CSV file", action = 'store_true')
    parser.add_argument("-u", "--update", help="Update attributes in path from CSV file", action = 'store_true')   
    parser.add_argument("-c", "--config", type = str, help="Location of the configuration file", required = True)

    return parser.parse_args()

if __name__ == '__main__':

    logging.basicConfig(format='%(asctime)s %(levelname)s %(filename)s %(funcName)s: %(message)s', level=logging.INFO) 
    args = parse_arguments()

    if not args.config:
        print("Error - path to config file is required")
    else:
        config = load_config_file(args.config)

    if args.export:
        export(config)
    elif args.update:
        update(config)
    else:
        print("Error: no action provided. Please use --export or --update")

