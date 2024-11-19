import os
from time import time
from graph import Graph
from tools import Hijackers
import pandas as  pd
from multiprocessing import Pool
from copy import deepcopy

# Where information abou execution will be saved
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


def run_analise(internet:Graph, victim:int, prefix:str, hijackers:list, outfile:str):
    '''
    Run the simulation and save the results in a file
    :param internet: Graph object used to base for the simulation
    :param victim: AS victim
    :param prefix: IPv4 prefix (legitimate and hijacked)
    :param hijackers: list of ASN hijackers
    :param outfile: path and name of the file to save simulation information
    :return:
    '''
    for i, asn_hjk in enumerate(hijackers):
        fakes_asp = [[],[victim]]
        print('####### Start AS{} - Hijacker AS{} ({}/{}) ########'.format(asn, asn_hjk, i+1, len(hijackers)))
        start = time()
        internet.add_prefix(victim, prefix)
        prefixes_hjk = prefix
        internet.route_propagate(victim, hijack=False, ignore_model_sometimes=True)
        print("Route from AS{} propagated in {:.4f} seconds.".format(victim, time() - start))
        print("Route from AS{} propagated in {:.4f} seconds.".format(victim, time() - start), file=logs)
        internet.enable_rov(rov_percentage)
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


if __name__ == '__main__':
    start = time()
    # CSV file with at least two columns ('ASN','Prefix') separated by ';'
    input_file_prefix = 'input/ases_prefixes.csv'
    # path and name of CAIDA's AS relationship file
    input_file = 'input/20241001.as-rel2.txt.bz2'
    # number of hijackers per cluster
    nb_hijackers = 150
    # how many processes will be executed simultaneous
    n_threads = 1
    df = pd.read_csv(input_file_prefix, sep=';')
    analyse = df[['ASN','Prefix']].values.tolist()
    asn_leg = df['ASN'].values.tolist()
    roa_enable = False  # True or False
    rov_percentage = 0  # Integer 0 - 100
    internet = load_internet(input_file)
    internet.get_vps()
    internet.get_country_ases()
    hijackers = Hijackers(internet)
    clusters = [[2, 2], [3, 3], [4, 10], [11, 0]]
    hijackers.create_clusters(clusters)
    hjks = hijackers.hijackers_by_clusters(nb_hijackers, asn_leg)
    print('Hijakers:', hjks, file=logs)
    print('Clusters:',clusters, file=logs)
    args = []
    files = []
    for i, (asn, prefix) in enumerate(analyse):
        #print('####### Start AS{} ({}/{}) ########'.format(asn, i+1, len(analyse)))
        outfile = './logs/report_with_clusters_{}.csv'.format(asn)
        files.append(outfile)
        args.append([internet, asn, prefix, hjks, outfile])
        #run_analise(internet= internet, victim=asn, prefix=prefix, hijackers=hjks, outfile=outfile)
    with Pool(processes=n_threads) as th_pool:
        th_pool.starmap(run_analise, args, )

    outfile = './logs/report_with_clusters.csv'
    cmd = 'head -n 1 {} > {}'.format(files[0], outfile)
    os.system(cmd)
    for f in files:
        cmd = 'cat ' + f + ' | grep "^{" >> '+ outfile
        os.system(cmd)

    print("All execution took {:.4f} seconds".format(time() - start), file=logs)
    logs.close()
