import bz2
import os.path
import urllib.request
from random import randint
from time import sleep
import json
import progressbar
from datetime import datetime
import pickle as pk



def load_ases(input_file:str):
    '''
    Load ASes from CAIDA AS relationship file
    :param file: path for file
    :return: a set with ASes
    '''
    lines = bz2.open(input_file, 'rt')
    ases = set()
    for line in lines:
        if line.startswith('#'):
            continue
        tmp = line.strip('\n').split('|')
        if len(tmp) < 3:
            continue
        as1 = int(tmp[0])
        as2 = int(tmp[1])
        ases.add(as1)
        ases.add(as2)
    return ases


def get_rovista(ases:set,folder:str, override:bool=False):
    '''
    Download Json files from https://rovista.netsecurelab.org/ with ROV information from the ASes
    :param ases: a set of ASes to get ROV information
    :param folder: folder to save json files
    :param override: Override the files if they already exist
    :return: a list with files names
    '''
    print('Getting information from RoVista (https://rovista.netsecurelab.org/):')
    folder += '/RoVista'
    if not os.path.isdir(folder):
        os.mkdir(folder)
    files = list()
    bar = progressbar.ProgressBar(max_value=len(ases), redirect_stdout=True)
    i = 0
    for asn in ases:
        i += 1
        bar.update(i)
        file_name = '{}/{}.json'.format(folder,asn)
        files.append(file_name)
        if os.path.isfile(file_name) and not override:
            continue
        url = 'https://api.rovista.netsecurelab.org/rovista/api/AS-rov-scores/{}'.format(asn)
        attempts = 0
        while attempts < 3:
            try:
                urllib.request.urlretrieve(url, file_name)
                break
            except:
                t = randint(5, 20)
                print('\nERROR to get {}, try again in {} seconds'.format(url,t))
                sleep(t)
                attempts += 1
        if attempts == 3:
            print('ERROR to get data from RoVisa.')
            exit(1)
        sleep(1)
    bar.finish()
    return files


def rov_enabled(files:list, date_target:str, folder:str, min_ratio:float=0.5, override:bool=False):
    '''
    Select which ASes have ROV enabled based on the minimum ratio
    :param files: a list of json files with RoVista information
    :param date_target: which date to analyze ROV status
    :param min_protection: minimum ratio to consider ROV enabled
    :return: a list of ASes with ROV enabled
    '''
    ases = set()
    outfile = '{}/ASes_ROV_{}_{}.pk'.format(folder, date_target, min_ratio)
    calculate = True
    if os.path.isfile(outfile) and not override:
        try:
            with open(outfile,'rb') as f:
                ases = pk.load(f)
            calculate = False
        except:
            print('Fail to load file ({}). Recalculating ...'.format(outfile))
    if calculate:
        date_target = datetime.strptime(date_target, "%Y-%M-%d")
        print('Reading .json files and selecting ASes with ROV enabled:')
        bar = progressbar.ProgressBar(max_value=len(files), redirect_stdout=True)
        i=0
        for file in files:
            i += 1
            bar.update(i)
            with open(file,'r') as f:
                asndata = json.load(f)
            for asnd in asndata:
                asn = asnd['asnDateKey']['asn']
                r_date = asnd['asnDateKey']['recordDate']
                r_date = datetime.strptime(r_date, "%Y-%M-%d")
                if r_date >= date_target:
                    ratio = asnd['ratio']
                    if ratio >= min_ratio:
                        ases.add(asn)
                    break
        bar.finish()
        with open(outfile,'wb') as of:
            pk.dump(ases, of)
    print('{} ASes found with ROV enabled.'.format(len(ases)))
    return ases


def ases_rov(ases:list, date_target:str, folder:str, min_ratio:float=0.5, override:bool=False):
    '''
    Return ASes in the list that have ROV enabled based on RoVista information and the minimum ratio.
    :param ases: A list of ASes to check which have ROV enabled
    :param date_target: Date to check ROV status
    :param folder: Folder to save the ASes list to reuse the information
    :param min_ratio: a minimum score ratio to consider ROV enabled in the AS
    :param override: Recompute if it was previously computed (True/False)
    :return: A list of ROV-enabled ASes
    '''
    if folder.startswith('/'):
        path = '/'
    else:
        path = ''
    for f in folder.split('/'):
        path += f
        if not os.path.isdir(f):
            os.mkdir(f)
        f += '/'
    files = get_rovista(ases, folder, override=override)
    ases = rov_enabled(files, date_target, folder=folder, min_ratio=min_ratio, override=override)
    return ases


if __name__ == '__main__':
    '''
    Test execution
    '''
    input_file = 'input/20240401.as-rel2.txt.bz2'
    date_target = '2024-04-01'
    folder = './data'
    if not os.path.isdir(folder):
        os.mkdir(folder)
    ases = load_ases(input_file)
    ases_rov(ases=ases, date_target=date_target, folder=folder, min_ratio=0.5, override=False)
    print('All done!')
