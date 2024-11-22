import os
from time import time
import pickle as pk
import pandas as  pd
from multiprocessing import Pool
from copy import deepcopy
from graph import Graph
from tools import Hijackers
from get_rovista_data import ases_rov


# Where information about execution will be saved
if not os.path.isdir('./logs'):
    os.mkdir('./logs')
logs = open('./logs/execution.log','w')

def load_internet(input_file:str):
    '''
    Load information from the file and create a Graph object
    :param input_file: file (AS relationship from CAIDA)
    :return: Graph object
    '''
    internet = Graph(override=False)
    start = time()
    internet.add_connections(input_file=input_file)
    print("Load the connections took {:.4f} seconds".format(time() - start))
    print("Load the connections took {:.4f} seconds".format(time() - start), file=logs)
    return internet


def run_analise(internet:Graph, victim:int, prefix:str, hijackers:list, outfile:str, type0:bool=True, type1:bool=True, roa:bool=True):
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
    for i, asn_hjk in enumerate(hijackers):
        fakes_asp = list()
        if type0:
            fakes_asp.append([])
        if type1:
            fakes_asp.append([victim])
        print('####### Start AS{} - Hijacker AS{} ({}/{}) ########'.format(victim, asn_hjk, i+1, len(hijackers)))
        start = time()
        internet.add_prefix(victim, prefix, roa)
        prefixes_hjk = prefix
        internet.route_propagate(victim, hijack=False, ignore_model_sometimes=True)
        print("Route from AS{} propagated in {:.4f} seconds.".format(victim, time() - start))
        print("Route from AS{} propagated in {:.4f} seconds.".format(victim, time() - start), file=logs)
        for fake_asp in fakes_asp:
            inter2 = deepcopy(internet)
            print('####### Forged AS path:', fake_asp)
            # Make prefix hijack
            inter2.hijack(asn_hjk, prefixes_hjk, fake_asp)
            start = time()
            inter2.route_propagate(asn_hjk, hijack=True, ignore_model_sometimes=True)
            print("Hijack route from AS{} propagated in {:.4f} seconds".format(asn_hjk, time() - start,))
            print("Hijack route from AS{} propagated in {:.4f} seconds".format(asn_hjk, time() - start, ), file=logs)
            inter2.text_report(outfile, export_asp=True)
            del inter2
            #inter2.restart_graph()


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


def run_simulation(internet:Graph, hjks:list, analyse:list,outfile:str,n_threads:int=1, clear_tmp:bool=True, type0:bool=True, type1:bool=True, roa:bool=True):
    args = []
    files = []
    outfile_tmp = outfile.replace('.csv','_{}.tmp')
    for i, (asn, prefix) in enumerate(analyse):
        tmp_f = outfile_tmp.format(asn)
        files.append(tmp_f)
        args.append([internet, asn, prefix, hjks, tmp_f, type0, type1, roa])
    with Pool(processes=n_threads) as th_pool:
        th_pool.starmap(run_analise, args, )

    cmd = 'head -n 1 {} > {}'.format(files[0], outfile)
    os.system(cmd)
    for f in files:
        cmd = 'cat ' + f + ' | grep "^{" >> '+ outfile
        os.system(cmd)
        if clear_tmp:
            os.remove(f)


if __name__ == '__main__':
    # CSV file with at least two columns ('ASN','Prefix') separated by ';'
    input_file_prefix = 'input/ases_prefixes.csv'
    # File to load or save a list of hijackers
    input_hjks = 'input/hijackers.pk'
    # path and name of CAIDA's AS relationship file
    input_file = 'input/20241001.as-rel2.txt.bz2'
    date_file = '2024-10-01'
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


    # First simulation (ROV disable, Type-0 and Type-1 hijacks)
    internet1 = deepcopy(internet)
    print('Starting first simulation.')
    start = time()
    # File to save simulation data
    outfile = './logs/result_with_clusters.csv'
    hjks = load_hijackers(internet1, nb_hijackers, clusters, input_hjks)
    run_simulation(internet1,hjks, analyse, outfile, n_threads, roa=False)
    print("All execution took {:.4f} seconds".format(time() - start), file=logs)
    del internet1


    # Second simulation (ROV enable, Type-0)
    internet2 = deepcopy(internet)
    print('Starting first simulation.')
    start = time()
    # File to save simulation data
    outfile = './logs/result_with_clusters_and_rov.csv'
    hjks = load_hijackers(internet2, nb_hijackers, clusters, input_hjks)
    r_ases = ases_rov(ases=internet2.get_ases(), date_target=date_file, folder='./data', min_ratio=0.5)
    internet2.enable_rov(ases=r_ases)
    run_simulation(internet2,hjks, analyse, outfile, n_threads, type0=True, type1=False, roa=True)
    print("All execution took {:.4f} seconds".format(time() - start), file=logs)
    del internet2

    logs.close()
