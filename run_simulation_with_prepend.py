import os
from time import time
import pickle as pk
import pandas as  pd
from multiprocessing import Pool
from copy import deepcopy
from graph import Graph
from tools import Hijackers
from urllib.request import urlretrieve


# Where information about execution will be saved
if not os.path.isdir('./logs'):
    os.mkdir('./logs')
logs = open('./logs/execution_prepend.log','w')


def get_caida_file(date:str, folder:str):
    '''
    Get AS relationship file from CAIDA
    :param date: Date (YYYY-MM-DD)
    :param file: where it will be saved
    :return: file name
    '''
    date = date.replace('-', '')
    file = '{}/{}.as-rel2.txt.bz2'.format(folder, date)
    if not os.path.isfile(file):
        url = 'https://publicdata.caida.org/datasets/as-relationships/serial-2/{}.as-rel2.txt.bz2'.format(date)
        urlretrieve(url, file)
    return file


def load_internet(input_file:str):
    '''
    Load information from the file and create a Graph object
    :param input_file: file (AS relationship from CAIDA)
    :return: Graph object
    '''
    internet = Graph(override=False,debug=False)
    start = time()
    internet.add_connections(input_file=input_file)
    print("Load the connections took {:.4f} seconds".format(time() - start))
    print("Load the connections took {:.4f} seconds".format(time() - start), file=logs)
    return internet


def run_analise(internet:Graph, victim:int, prefix:str, hijackers:list, outfile:str, type0:bool=True,
                type1:bool=True, roa:bool=True, prepend:dict=dict()):
    '''
    Run the simulation and save the results in a file
    :param internet: Graph object used to base for the simulation
    :param victim: AS victim
    :param prefix: IPv4 prefix (legitimate and hijacked)
    :param hijackers: list of ASN hijackers
    :param outfile: path and name of the file to save simulation information
    :param type0: run Type-0 hijack simulations
    :param type1: run Type-1 hijack simulations
    :param roa: Enable ROA (Route Origin Authorization) from AS victim
    :return:
    '''
    added = internet.add_prefix(victim, prefix, roa)
    if added:
        start = time()
        internet.route_propagate(victim, hijack=False, ignore_model_sometimes=True, prepend_origin=prepend)
        print("[{}]Route from AS{} propagated in {:.4f} seconds.".format(victim, victim, time() - start))
        print("[{}]Route from AS{} propagated in {:.4f} seconds.".format(victim, victim, time() - start), file=logs)
        prefixes_hjk = prefix
        for i, asn_hjk in enumerate(hijackers):
            fakes_asp = list()
            if type0:
                fakes_asp.append([])
            if type1:
                fakes_asp.append([victim])
            print('[{}]####### Start AS{} - Hijacker AS{} ({}/{}) ########'.format(victim,victim, asn_hjk, i+1, len(hijackers)))
            for fake_asp in fakes_asp:
                start = time()
                inter2 = deepcopy(internet)
                print('[{}]####### Forged AS path: {}'.format(victim, fake_asp))
                # Make prefix hijack
                inter2.hijack(asn_hjk, prefixes_hjk, fake_asp)
                inter2.route_propagate(asn_hjk, hijack=True, ignore_model_sometimes=True, prepend_origin=prepend)
                print("[{}]Hijack route from AS{} propagated in {:.4f} seconds".format(victim, asn_hjk, time() - start,))
                print("[{}]Hijack route from AS{} propagated in {:.4f} seconds".format(victim, asn_hjk, time() - start, ), file=logs)
                #inter2.text_report(outfile, export_asp=True)
                del inter2
                #inter2.restart_graph()
    else:
        print('[{}]Fail to run the simulation with AS{} as victim.'.format(victim, victim))


def select_hijackers(internet:Graph, nb_hijackers:int, clusters:list):
    hijackers = Hijackers(internet)
    hijackers.create_clusters(clusters)
    return hijackers.hijackers_by_clusters(nb_hijackers, asn_leg)


def load_hijackers(internet:Graph, nb_hijackers:int, clusters:list, input_hjks:str=''):
    if os.path.isfile(input_hjks) and input_hjks!='':
        try:
            with open(input_hjks,'rb') as f:
                hjks = pk.load(f)
            print('Hijakers loaded from file {}:\n'.format(input_hjks), hjks, file=logs)
        except:
            print('Failed to load hijackers!!!')
            exit(1)
    else:
        hjks = select_hijackers(internet, nb_hijackers, clusters)
        if input_hjks!='':
            with open(input_hjks, 'wb') as f:
                pk.dump(hjks,f)
        print('Hijakers selected:', hjks, file=logs)
        print('Clusters:',clusters, file=logs)
    return hjks


def run_simulation(internet:Graph, hjks:list, analyse:list,outfile:str,n_threads:int=1, clear_tmp:bool=True,
                   type0:bool=True, type1:bool=True, roa:bool=True, prepend:dict=dict()):
    args = []
    files = []
    outfile_tmp = outfile.replace('.csv','_{}.tmp')
    for i, (asn, prefix) in enumerate(analyse):
        tmp_f = outfile_tmp.format(asn)
        files.append(tmp_f)
        args.append([internet, asn, prefix, hjks, tmp_f, type0, type1, roa, prepend[asn]])
    with Pool(processes=n_threads) as th_pool:
        th_pool.starmap(run_analise, args, )
    first_line = True
    for f in files:
        if not os.path.isfile(f):
            continue
        if first_line:
            cmd = 'head -n 1 {} > {}'.format(f, outfile)
            os.system(cmd)
            first_line = False
        cmd = 'cat ' + f + ' | grep "^{" >> '+ outfile
        os.system(cmd)
        if clear_tmp:
            os.remove(f)


def print_neighbors_stats(internet:Graph, asn:int):
    neighbors = internet.get_neighbors_stats(asn)
    if neighbors is None:
        print('AS{} is not in the Internet Graph.'.format(asn))
    else:
        print('AS{} neighbors stats'.format(asn),)
        print('Total neighbors = {}, from {} different countries and from {} different continents'.format(
            neighbors['Neighbors']['Number'],neighbors['Neighbors']['Countries'],
            neighbors['Neighbors']['Continents']))
        print('Total customers = {}, from {} different countries and from {} different continents'.format(
            neighbors['Customers']['Number'], neighbors['Customers']['Countries'],
            neighbors['Customers']['Continents']))
        print('Total peers = {}, from {} different countries and from {} different continents'.format(
            neighbors['Peers']['Number'], neighbors['Peers']['Countries'],
            neighbors['Peers']['Continents']))
        print('Total providers = {}, from {} different countries and from {} different continents'.format(
            neighbors['Providers']['Number'], neighbors['Providers']['Countries'],
            neighbors['Providers']['Continents']))
        print('--------------------------------------------------------')


def print_neighbors_stats_line(internet:Graph, asn:int):
    neighbors = internet.get_neighbors_stats(asn)
    if neighbors is None:
        print('AS{} is not in the Internet Graph.'.format(asn))
    else:
        print('{};{};{};{};{};{};{};{};{};{};{};{};{}'.format(asn, neighbors['Neighbors']['Number'],neighbors['Neighbors']['Countries'],
            neighbors['Neighbors']['Continents'], neighbors['Customers']['Number'], neighbors['Customers']['Countries'],
            neighbors['Customers']['Continents'], neighbors['Peers']['Number'], neighbors['Peers']['Countries'],
            neighbors['Peers']['Continents'], neighbors['Providers']['Number'], neighbors['Providers']['Countries'],
            neighbors['Providers']['Continents']))


def load_prepends(prepend_file:str):
    result = dict()
    dfp = pd.read_csv(prepend_file,sep=';')
    ases = set(dfp['AS'].values.tolist())
    for asn in ases:
        result[asn]=dict()
        for n,p in dfp.loc[dfp['AS']==asn][['Neighbord','Prepend']].values.tolist():
            result[asn][n]=p
    return result

if __name__ == '__main__':
    # CSV file with at least two columns ('ASN','Prefix') separated by ';'
    input_file_prefix = 'input/ases_prefixes.csv'
    # path and name of CAIDA's AS relationship file
    date_file = '2024-04-01'
    input_file = get_caida_file(date_file, 'input')
    # File to load or save a list of hijackers
    # input_hjks = 'input/hijackers.pk'
    input_hjks = 'input/hijackers-{}.pk'.format(date_file)
    # File with prepend information
    prepend_file = 'input/asn_prepend_{}.csv'.format(date_file)
    # number of hijackers per cluster
    nb_hijackers = 150
    # range to create ASes cluster by degree
    clusters = [[2, 2], [3, 3], [4, 10], [11, 0]]
    # number of simultaneous processes will be executed
    n_threads = 25

    df = pd.read_csv(input_file_prefix, sep=';')
    analyse = df[['ASN','Prefix']].values.tolist()
    asn_leg = df['ASN'].values.tolist()
    internet = load_internet(input_file)
    internet.get_vps()
    internet.get_country_ases()
    hjks = load_hijackers(internet, nb_hijackers, clusters, input_hjks)

    # simulation (ROV disable, Type-0 and Type-1 hijacks)
    folder = './without_rov_prepend'
    if not os.path.isdir(folder):
        os.mkdir(folder)
    outfile = '{}/result_{}.csv'.format(folder,date_file)
    internet1 = deepcopy(internet)
    prepend = load_prepends(prepend_file)
    analyse_p = []
    for a,p in analyse:
        if a in prepend.keys():
            analyse_p.append([a,p])
    print('Starting simulation.')
    start = time()
    # File to save simulation data
    run_simulation(internet1, hjks, analyse_p, outfile, n_threads, roa=False, prepend=prepend)
    print("All execution took {:.4f} seconds".format(time() - start), file=logs)
    del internet1

    logs.close()
