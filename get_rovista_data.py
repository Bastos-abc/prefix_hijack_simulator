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
    files = list()
    print('Getting information from RoVista (https://rovista.netsecurelab.org/):')
    bar = progressbar.ProgressBar(max_value=len(ases), redirect_stdout=True)
    i = 0
    for asn in ases:
        i += 1
        bar.update(i)
        file_name = '{}/{}.json'.format(folder,asn) # need to change to .json file
        files.append(file_name)
        if os.path.isfile(file_name) and not override:
            continue
        url = 'https://api.rovista.netsecurelab.org/rovista/api/AS-rov-scores/{}'.format(asn)
        try:
            urllib.request.urlretrieve(url, file_name)
        except:
            print('\nERROR to get {}, try again in 10 seconds'.format(url))
            sleep(10)
            urllib.request.urlretrieve(url, file_name)
        #sleep(randint(1, 3))
        sleep(1)
    bar.finish()
    return files


def rov_enabled(files:list, date_target:str, min_ratio:float=0.5):
    '''
    Select which ASes have ROV enabled based on the minimum ratio
    :param files: a list of json files with RoVista information
    :param date_target: which date to analyze ROV status
    :param min_protection: minimum ratio to consider ROV enabled
    :return: a list of ASes with ROV enabled
    '''
    ases = set()
    date_target = datetime.strptime(date_target, "%y-%m-%d")
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
            r_date = datetime.strptime(r_date, "%y-%m-%d")
            if r_date >= date_target:
                ratio = asnd['ratio']
                if ratio >= min_ratio:
                    ases.add(asn)
                break
    bar.finish()
    print('{} ASes found with ROV enabled.'.format(len(ases)))
    return ases


if __name__ == '__main__':
    input_file = 'input/20241001.as-rel2.txt.bz2'
    data_target = '2024-10-01'
    outfile = './data/ASes_with_ROV_{}.pk'.format(data_target)
    folder = './data'
    if not os.path.isdir(folder):
        os.mkdir(folder)
    folder = './data/RoVista'
    if not os.path.isdir(folder):
        os.mkdir(folder)
    ases = load_ases(input_file)
    files = get_rovista(ases, folder, override=False)
    ases = rov_enabled(files, data_target, min_ratio=0.5)
    with open(outfile,'w') as of:
        pk.dump(ases, of)
    print('All done!')
