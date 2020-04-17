import os
import re
from itertools import product
import json

import numpy as np
from PyQt5 import QtCore, QtWidgets


class ProjectIO:
    """
    IO class for anduryl project
    """
    def __init__(self, project):
        """
        Constructor
        
        Parameters
        ----------
        project : anduryl.main.Project
            Project class
        """
        self.project = project

    def to_file(self, path):
        """
        Saves project to file, calls the save function dependend
        on the path extension
        
        Parameters
        ----------
        path : str
            Path to save file
        """
        if path.lower().endswith('.dtt'):
            self.to_excalibur(path)
        elif path.lower().endswith('.json'):
            self.to_json(path)
        else:
            OSError(f'Extension ".{os.path.splitext(path)[-1]}" not recognized. Expected ".dtt" or ".json".')

    def to_excalibur(self, dttfile):
        """
        Save to Excalibur format
        
        Parameters
        ----------
        dttfile : str
            .dtt file for excalibur. .rls file is derived from the name by replacing the extension
        """
        # Get rls filename
        rlsfile = dttfile.replace('.dtt', '.rls')
        # Save
        write_excalibur(self.project, dttfile, rlsfile)

    def to_json(self, path):
        """
        Save project to json
        
        Parameters
        ----------
        path : str
            Path to json file
        """
        if not path.endswith('.json'):
            raise ValueError('Filename should end with .json')
        # Save
        write_json(self.project, path)

    def load_file(self, path):
        """
        Loads file given a file name. The load function of
        excalbur or json is called based on the extension.
        
        Parameters
        ----------
        path : str
            Path to file
        """

        if path.lower().endswith('.dtt'):
            # Load project
            rlsfile = path.lower().replace('.dtt', '.rls')
            if os.path.exists(rlsfile):
                self.load_excalibur(path, rlsfile)
            else:
                raise ValueError(f'Could not find the matching .rls file for the opened .dtt file ({path}).')

        elif path.lower().endswith('.rls'):
            # If rls file is tried to be opened, replace extension
            dttfile = path.lower().replace('.rls', '.dtt')
            if os.path.exists(dttfile):
                self.load_excalibur(dttfile, path)
            else:
                raise ValueError(f'Could not find the matching .dtt file for the opened .rls file ({path}).')

        elif path.lower().endswith('.json'):
            self.load_json(path)

        else:
            OSError(f'Extension ".{os.path.splitext(path)[-1]}" not recognized. Expected ".dtt" or ".json".')

    def load_excalibur(self, dttfile, rlsfile):
        """
        Load Excalibur file format
        
        Parameters
        ----------
        dttfile : str
            Path to.dtt file
        rlsfile : str
            Path to .rls file
        """
        outdict = read_excalibur(dttfile, rlsfile)
        self.add_data(outdict)
    
    def load_json(self, path):
        """
        Load json file format
        
        Parameters
        ----------
        path : str
            Path to .json file
        """
        outdict = read_json(path)
        self.add_data(outdict)

    def add_data(self, outdict):
        """
        Adds data to project from loaded dictionary
        
        Parameters
        ----------
        outdict : dictionary
            Dictionary with loaded input data
        """

        # Get data for determining shape
        seed = np.array([~np.isnan(rls) for rls in outdict['items']['realization']], dtype=bool)
        arr = outdict['assessments']
        
        self.project.initialize(
            nexperts=arr.shape[0],
            nseed=sum(seed),
            ntarget=arr.shape[2] - sum(seed),
            nquantiles=arr.shape[1]
        )
        
        # Get experts
        self.project.experts.index = outdict['experts']['ids']
        self.project.experts.ids[:] = outdict['experts']['ids']
        self.project.experts.names[:] = outdict['experts']['name']
        self.project.experts.actual_experts[:] = list(range(len(self.project.experts.ids)))
        
        # Add questions
        self.project.items.ids[:] = outdict['items']['ids']
        self.project.items.realizations[:] = outdict['items']['realization']
        self.project.items.scale[:] = outdict['items']['scale']
        self.project.items.questions[:] = outdict['items']['question']
        
        # Add assessments
        self.project.assessments.array[:, :, :] = arr
        
        # Add quantiles and probabilies per bin
        del self.project.assessments.quantiles[:]
        quants = sorted(outdict['quantiles'])
        self.project.assessments.quantiles.extend(quants)
        self.project.assessments.calculate_binprobs()

        # Add results
        for key, settings in outdict['results'].items():
            self.project.add_results_from_settings(settings)

def write_excalibur(project, dttfile, rlsfile):
    """
    Function to write project experts, items and assessments
    to .dtt and .rls files.

    Results are not writen to the file. Expert names are also
    not saved.
    
    Parameters
    ----------
    project : Project instance
        Project with experts, items and assessments
    dttfile : str
        Path to .dtt file
    rlsfile : str
        Path to .rls file
    """

    # Check if paths exists
    for path in [dttfile, rlsfile]:
        if not os.path.exists(os.path.dirname(path)):
            raise OSError(f'Directory {os.path.dirname(path)} does not exist.')

    quantiles = project.assessments.quantiles
    _, nquantiles, nitems = project.assessments.array.shape
    nexperts = len(project.experts.actual_experts)

    # Get ID's with max string length
    expertids = [expid[:min(len(expid), 8)] for i, expid in enumerate(project.experts.ids) if i in project.experts.actual_experts]
    itemids = [itemid[:min(len(itemid), 14)] for itemid in project.items.ids]

    assessments = project.assessments.array[project.experts.actual_experts, :, :]
    assessments[np.isnan(assessments)] = -999.5

    # dtt
    quantiles_str = '  '.join([f'{int(round(100*quantile)):2d}' for quantile in quantiles])
    dtttext = f'* CLASS ASCII OUTPUT FILE. NQ= {len(quantiles):3d}   QU=  '+quantiles_str+'\n'

    # Construct format for line without and with question
    line = ' {:4d} {:>8s} {:4d} {:>14s} {:>3s} '+' '.join(['{}'] * len(quantiles)) + ' \n'
    questionline = ' {:4d} {:>8s} {:4d} {:>14s} {:>3s} '+' '.join(['{}'] * len(quantiles)) + ' {:>173s} \n'


    for iexp, expert in enumerate(expertids):
        for iit, (item, scale, question) in enumerate(zip(itemids, project.items.scale, project.items.questions)):
            # Collect values in correct scientific format
            values = [('' if val < 0 else ' ') + np.format_float_scientific(val, unique=False, exp_digits=4, precision=5)
                      for val in assessments[iexp, :, iit]]
            # Write question if they are specified and first expert or first item
            if question and (iexp == 0 or iit == 0):
                dtttext += questionline.format(iexp+1, expert, iit+1, item, scale, *values, question)
            # Else write a line without questions
            else:
                dtttext += line.format(iexp+1, expert, iit+1, item, scale, *values)

    # rls
    questionline = ' {:4d} {:>14s} {} {:>3s} {:>173s} \n'
    rlstext = ''
    realizations = project.items.realizations.copy()
    realizations[np.isnan(realizations)] = -999.5

    for iit, (item, scale, question, val) in enumerate(zip(itemids, project.items.scale, project.items.questions, realizations)):
        value = ('' if val < 0 else ' ') + np.format_float_scientific(val, unique=False, exp_digits=4, precision=5)
        rlstext += questionline.format(iit+1, item, value, scale, question)

    with open(dttfile, 'w') as f:
        f.write(dtttext)
    
    with open(rlsfile, 'w') as f:
        f.write(rlstext)

def read_excalibur(dttfile, rlsfile):
    """
    Function to read assessment from Excalibur .ddt and .rls file
    
    Parameters
    ----------
    dttfile : str
        File with assessments
    rlsfile : str
        File with realisations
    """
    if not os.path.exists(dttfile):
        raise OSError(f'File does not exist: {dttfile}')

    if not os.path.exists(rlsfile):
        raise OSError(f'File does not exist: {rlsfile}')

    # Read dtt file
    with open(os.path.join(dttfile), 'r') as f:
        lines = [line for line in f.readlines() if line.strip()]

    # Get percentiles
    first = lines[0]
    percentiles = np.array([float(p) for p in first.split('QU=')[-1].split()]) / 100
    npercentiles = len(percentiles)

    # Get number of experts and questions
    nexperts = max([int(line.split()[0]) for line in lines[1:]])
    nquestions = max([int(line[14:20]) for line in lines[1:]])

    # Get background measure
    pos = [max(line.lower().find('uni'), line.lower().find('log')) for line in lines]
    u, c = np.unique(pos, return_counts=True)
    startchr = u[np.argmax(c)]
    background = np.array([line[startchr:startchr+3].lower() for line in lines[1:1+nquestions]])

    # Get question id's
    idstrs = np.array([line[:startchr] for line in lines[1:1+nquestions]])
    ids = []
    for line in idstrs:
        pattern = re.findall('([^\s]+\s+[^\s]+\s+[^\s]+)' , line.strip())[0]
        ids.append(line[line.find(pattern) + len(pattern):].strip())

    # Get expert ids
    experts = np.array([lines[i][5:14].strip() for i in range(1, len(lines), nquestions)])

    # Assessments
    assessments = np.zeros((nexperts, npercentiles, nquestions))
    for line in lines[1:]:
        iexpert = int(line[:5])
        iquestion = int(line[14:20])
        assessments[iexpert-1, :, iquestion-1] = line[startchr+3:].split()[:npercentiles]

    # Process 'no-data'
    assessments = assessments.astype(float)
    assessments[(assessments >= -1000) & (assessments <= -990)] = np.nan

    # Read realisations from rls file
    with open(rlsfile, 'r') as f:
        lines = [line for line in f.readlines() if line.strip()]
    
    # Get the position of 'uni' of 'log' in the file
    pos = [max(line.lower().find('uni'), line.lower().find('log')) for line in lines]
    u, c = np.unique(pos, return_counts=True)
    endchr = u[np.argmax(c)]

    realdict = {}
    questiondict = {}
    for i, line in enumerate(lines):
        value = line[:endchr].split()[-1]
        linepart = line[:line.find(value)].strip()
        qid = re.findall('[^\s]+(.+)', linepart)[0].strip()
        realdict[qid] = value
        questiondict[qid] = line[endchr+3:].strip()

    realizations = np.array([float(realdict[key]) if key in realdict else -995 for key in ids])
    questions = [questiondict[key] if key in questiondict else '' for key in ids]
    
    # Process 'no-data'
    idx = (realizations >= -1000) & (realizations <= -990)
    realizations = np.array([np.nan if idx[i] else val for i, val in enumerate(realizations)], dtype=object)

    outdict = {
        'quantiles': percentiles,
        'assessments': assessments,
        'items': {
            'ids': ids,       
            'realization': realizations,
            'scale': np.array(background).astype(object).T,
            'question': questions
        },
        'experts': {
            'ids': experts.tolist(),
            'name': experts.tolist()
        },
        'results': {}
    }
    
    return outdict

def write_json(project, path):
    """
    Function to write project experts, items and assessments
    to .json

    Results are not writen to the file. Expert names are also
    not saved.
    
    Parameters
    ----------
    project : Project instance
        Project with experts, items and assessments
    path : str
        Path to .json file
    """

    # Check if paths exists
    if not os.path.exists(os.path.dirname(path)):
        raise OSError(f'Directory {os.path.dirname(path)} does not exist.')

    expert_data_T = list(zip(*[
        project.experts.names,
        project.experts.user_weights
    ]))
    expert_data_T = [expert_data_T[i] for i in project.experts.actual_experts]

    # Create dictionary
    savedct = {
        'experts': elements_to_dict(
            expert_data_T,
            [project.experts.get_exp('actual'), ['name', 'user weight']]
        ),
        'items': elements_to_dict(
        list(zip(*[            
            project.items.realizations,
            project.items.scale,
            project.items.questions
        ])),
            [project.items.ids, ['realization', 'scale', 'question']]
        ),
        'assessments': elements_to_dict(
            np.swapaxes(project.assessments.array, 1, 2)[project.experts.actual_experts],
            [project.experts.get_exp('actual'), project.items.ids, project.assessments.quantiles]
        ),
        'results': {key: project.results[key].settings for key in project.results.keys()}
    }

    # Write to json
    with open(path, 'w') as f:
        f.write(json.dumps(savedct, indent=4))
    
def read_json(path):
    """
    Reads Anduryl project from json format
    
    Parameters
    ----------
    path : str
        Path to json file
    
    Returns
    -------
    dictionary
        Dictionary with loaded data
    """

    outdct = {}
    
    # Write to json
    with open(path, 'r') as f:
        dct = json.loads(f.read())

    # Read experts
    labels, values = dict_to_elements(dct['experts'])
    exp_dict = dct['experts']
    exp_ids = list(exp_dict.keys())
    outdct['experts'] = {
        'ids': exp_ids,
        'name': [exp_dict[exp]['name'] for exp in exp_ids]
    }

    # Read items
    labels, values = dict_to_elements(dct['items'])
    item_dict = dct['items']
    item_ids = list(item_dict.keys())
    outdct['items'] = {
        'ids': item_ids,
        'realization': [item_dict[item]['realization'] for item in item_ids],
        'scale': [item_dict[item]['scale'] for item in item_ids],
        'question': [item_dict[item]['question'] for item in item_ids],
    }
    
    # Read assessments
    labels, values = dict_to_elements(dct['assessments'])
    assessments = np.array(values)
    outdct['quantiles'] = sorted(float(i) for i in labels[-1])
    
    # Sort assessments
    # by experts
    assessments = np.array(values)[np.argsort([exp_ids.index(exp) for exp in labels[0]]), :, :]
    # by items
    assessments = assessments[:, np.argsort([item_ids.index(item) for item in labels[1]])]
    # by quantiles
    assessments = assessments[:, :, np.argsort(np.array(labels[2], dtype=float))]
    # Swap quantiles and items such that the quantiles are in second place
    outdct['assessments'] = np.swapaxes(assessments, 1, 2)

    # Add results
    outdct['results'] = {}#dct['results']

    return outdct

def elements_to_dict(arr, labels, level=0):
    """
    Functionn to map array of list elements to dictionary
    
    Parameters
    ----------
    arr : np.ndarray or lists
        Elements to be ravelled to dict
    labels : list
        labels for each 'axis' of the arr
    level : int, optional
        Level of depth, used by the function itself when nesting, by default 0
    
    Returns
    -------
    dictionary
        array as ravelled dictionary
    """
    dct = {}
    for i, item in enumerate(arr):
        key = labels[level][i]
        if isinstance(item, (np.ndarray, list, tuple)):
            dct[key] = elements_to_dict(item, labels, level+1)
        else:
            dct[key] = item
                
    return dct

def dict_to_elements(dct):
    """
    Create a (nested) list from a dictionary
    
    Parameters
    ----------
    dct : dictionary
        Dictionary to reshape into lists
    
    Returns
    -------
    list, list
        Labels and elements
    """

    keys = []
    def get_keys(dct, level=0):
        # Verzamel keys
        for key, val in dct.items():
            if len(keys) < level+1:
                keys.append([])
            keys[level].append(key)
            if isinstance(val, dict):
                get_keys(val, level+1)

    # Get keys and select unique
    get_keys(dct)
    for i in range(len(keys)):
        keys[i] = list(set(keys[i]))

    def fill_lists_by_key(dct, level=0):
        lst = [None] * len(keys[level])
        for key, val in dct.items():
            idx = keys[level].index(key)
            if isinstance(val, dict):
                lst[idx] = fill_lists_by_key(val, level+1)
            else:

                lst[idx] = val
        return lst
    
    items = fill_lists_by_key(dct)

    return keys, items

def selection_to_text(selection, newline='\n', delimiter='\t'):
    """
    Get elements from model selection and convert to text
    
    Parameters
    ----------
    selection : Qt selection
        Selection from a table
    newline : str, optional
        character for newline, by default \n
    delimiter : str, optional
        character for delimiter, by default \t
    
    Returns
    -------
    str
        Text that can be exported or pasted
    """
    rows = [index.row() for index in selection]
    cols = [index.column() for index in selection]
    minrow, maxrow = min(rows), max(rows)
    mincol, maxcol = min(cols), max(cols)
    
    rowcount = maxrow - minrow + 1
    colcount = maxcol - mincol + 1
    table = [[''] * colcount for _ in range(rowcount)]
    
    for index in selection:
        row = index.row() - minrow
        column = index.column() - mincol
        item = index.data()
        table[row][column] = item if isinstance(item, str) else ''
    
    return newline.join([delimiter.join(row) for row in table])

def get_table_text(model, newline='\n', delimiter='\t'):
    """
    Get all elements from table model, including the header
    
    Parameters
    ----------
    selection : Qt selection
        Selection from a table
    newline : str, optional
        character for newline, by default \n
    delimiter : str, optional
        character for delimiter, by default \t
    
    Returns
    -------
    str
        Text that can be exported or pasted
    """
    # Get header
    header = [model.headerData(i, QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
              for i in range(model.columnCount(None))]
    if header[0] == 'ID':
        header[0] = 'Id'
    # Get data text
    selection = [model.createIndex(i, j) for i, j in product(range(model.rowCount(None)), range(model.columnCount(None)))]
    return delimiter.join(header) + newline + selection_to_text(selection, newline, delimiter) + newline

def table_to_csv(model, mainwindow, path=None):
    """
    Saves table to csv.
    
    Parameters
    ----------
    model : table model
        Table model from which the data is retrieved
    mainwindow : mainwindow
        Is used for retrieving save file name
    path : str, optional
        Path to save file, if None, the user is asked to provide the save file name
    """

    if path is None:
        options = QtWidgets.QFileDialog.Options() | QtWidgets.QFileDialog.DontUseNativeDialog
        # Set current dir
        currentdir = mainwindow.appsettings.value('currentdir', '.', type=str)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(mainwindow, 'Anduryl - Save as CSV', '.', "CSV (*.csv)", options=options)

    if not path:
        return None

    if not os.path.exists(os.path.dirname(path)):
        raise OSError(f'Save path "{os.path.dirname(path)}" does not exists.')

    if not path.endswith('.csv'):
        path += '.csv'

    with open(path, 'w') as f:
        f.write(get_table_text(model, newline='\n', delimiter=';'))
