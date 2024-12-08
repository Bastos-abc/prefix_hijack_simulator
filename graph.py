import bz2
import os.path
from copy import copy
import random
import pickle as pk
import ssl
import urllib.request
#from logging import debug

from netcalc_ipv4 import Prefix


class AS(object):
    def __init__(self, asn:int, description:str=''):
        '''
        Create an object to represent an Autonomous System (AS)
        :param asn: Autonomous System Number(int),
        :param description: AS description (str)
        '''
        self.description = description
        self.asn = asn
        self.providers = set()
        self.peers = set()
        self.customers = set()
        self.siblings = set()
        self.routes = dict()
        self.prefixes = set()
        self.hijacks = set()
        self.fake_asp = list()
        self.rov_enabled = False
        self.vps_prefixes = 0
        self.country = ''
        self.continent = ''


    def set_vps(self, nb_pref:int):
        '''
        Set the number of prefixes that this AS export to collector if it's a Vantage Point
        :param nb_pref: Number of prefixes this AS export to a collector (int)
        :return: None
        '''
        self.vps_prefixes = nb_pref


    def get_fake_asp(self):
        '''
        Export Forged AS path used to hijack a prefix
        :return: Forged AS path (list)
        '''
        return copy(self.fake_asp)


    def get_prefixes(self):
        '''
        Export a list with prefixes announced from this AS
        :return: List of prefixes (set)
        '''
        return self.prefixes


    def get_hijacks(self):
        '''
        Export a list of prefixes hijacked by this AS
        :return: List of hijacked prefixes (set)
        '''
        return self.hijacks


    def is_rov_enabled(self):
        '''
        Check if the AS Route Origen Validation is enabled
        :return: True or False
        '''
        return self.rov_enabled


    def set_rov(self, enable:bool=False):
        '''
        Enable or disable Route Origen Validation
        :param enable: True or False
        :return: None
        '''
        self.rov_enabled = enable


    def add_provider(self, provider:int):
        '''
        Add a new provider
        :param provider:  ASN
        :return: None
        '''
        self.providers.add(provider)


    def add_route(self, prefixes:list, asp:list, hijack:bool=False, debug:bool=True):
        '''
        Add a route to the prefixes if they have best route
        :param prefixes: a list with Prefixes objects
        :param asp: AS path received with the prefixes
        :param hijack: This is a prefix hijacked (True or False)
        :return: announce (A list with ASes to announce the route), new_asp (AS path to announce the route) and
        new_prefixes (Prefixes that had the best route to announce to the other ASes)
        '''
        announce = set()
        new_asp = copy(asp)
        new_asp.insert(0,self.asn)
        new_prefixes = list()
        origen = asp[0]
        accept = False
        if not (origen in self.peers or origen in self.customers or origen in self.providers or origen in self.siblings):
            print('ERROR: This AS ({}) is not a neighbored.'.format(origen))
        elif self.asn in asp:
            if debug:
                print('Route ignored by BGP (loop). AS{} -> AS_path:{}'.format(self.asn, asp))
        else:
            for prefix in prefixes:
                accept = False
                if not prefix in self.routes.keys():
                    self.routes[prefix]= {'AS_path':asp, 'hijack':hijack}
                    new_prefixes.append(prefix)
                    accept = True
                else:
                    last_origen = self.routes[prefix]['AS_path'][0]
                    # Apply local pref based in Gao-Rexford model
                    if ((origen in self.customers and last_origen not in self.customers) or
                        ((origen in self.peers or origen in self.siblings) and last_origen in self.providers) or
                        (origen in self.peers and last_origen in self.siblings)):
                        self.routes[prefix]={'AS_path': asp, 'hijack': hijack}
                        new_prefixes.append(prefix)
                        accept = True
                    # Using the shortest AS path
                    elif ((origen in self.customers and last_origen in self.customers) or
                          (origen in self.peers and last_origen in self.peers) or
                          (origen in self.providers and last_origen in self.providers) or
                          (origen in self.siblings and last_origen in self.siblings)):
                        if len(self.routes[prefix]['AS_path']) > len(asp):
                            self.routes[prefix]= {'AS_path': asp, 'hijack': hijack}
                            new_prefixes.append(prefix)
                            accept = True
                    else:
                        accept = False

            if accept:
                if origen in self.customers:
                    announce = self.providers | self.customers | self.peers | self.siblings
                    announce.remove(origen)
                elif origen in self.providers or origen in self.peers:
                    announce = self.customers | self.siblings
                else:
                    print('ERROR: This AS ({}) is not a neighbored.'.format(origen))
        return announce, new_asp, new_prefixes


    def clear_routes(self):
        '''
        Clear all routes
        :return: None
        '''
        self.routes.clear()


    def clear_prefixes(self):
        '''
        Clear all prefixes, both legitimate and hijacked, and the forged AS path
        :return: None
        '''
        self.prefixes.clear()
        self.hijacks.clear()
        self.fake_asp.clear()


    def clear_all(self):
        '''
        Clear all routes and prefixes
        :return: None
        '''
        self.clear_prefixes()
        self.clear_routes()
        self.rov_enabled = False


    def add_customer(self, customer:int):
        '''
        Add a new customer
        :param customer:  ASN
        :return: None
        '''
        self.customers.add(customer)


    def add_peer(self, peer:int):
        '''
        Add a new peer connection
        :param peer: Peer ASN
        :return: None
        '''
        self.peers.add(peer)


    def add_sibling(self, sibling:int):
        '''
        Add a sibling AS (Not implemented yet)
        :param sibling: Sibling ASN
        :return: None
        '''
        self.siblings.add(sibling)


    def add_prefix(self, prefix:str):
        '''
        Add a new legitimate prefix to announce from this AS
        :param prefix: IPv4 prefix X.X.X.X/X (str)
        :return: None
        '''
        try:
            p = Prefix(prefix)
            if not p in self.prefixes:
                self.prefixes.add(p)
        except:
            print('Prefix invalid ({}). \nInclude fail, check the format (IPv4 only) X.X.X.X/X'.format(prefix))


    def hijack(self,prefix:str, fake_asp:list):
        '''
        Add a hijacked prefix to announce from this AS and to forged AS path
        :param prefix: IPv4 Prefix to hijack X.X.X.X/X (str)
        :param fake_asp: a list with ASNs to forged AS path
        :return: None
        '''
        try:
            p = Prefix(prefix)
            if not p in self.prefixes:
                self.hijacks.add(p)
                self.fake_asp = fake_asp
        except:
            print('Hijack fail ({}), check the format (IPv4 only) X.X.X.X/X'.format(p))


    def print_as(self):
        '''
        Print all information included in the AS
        :return: None
        '''
        print('ASN:', self.asn)
        print('Description:', self.description)
        print('Prefixes:', '{}'.format(self.prefixes))
        print('ROV: {}'.format(('Enabled' if self.rov_enabled else 'Disabled')))
        print('Hijacks:', '{}'.format(self.hijacks))
        print('Forged AS path:', self.fake_asp)
        print('Providers:',self.providers)
        print('Peers:', self.peers)
        print('Customers:', self.customers)
        print('Routes:')
        self.print_rib()


    def print_rib(self):
        '''
        Print all AS route information
        :return: None
        '''
        prefixes = sorted(list(self.routes.keys()))
        line = '{}\t{} --> {}'
        asp = ''
        r_type = 'leg'
        for prefix in prefixes:
            if self.routes[prefix]['hijack']:
                r_type = 'hjk'
            print(line.format(r_type, prefix, self.routes[prefix]['AS_path']))


    def has_hijack(self):
        '''
        Check if the AS has a route to prefix hijacked
        :return: a list with hijacked prefixes and AS path
        '''
        hijack = list()
        for prefix in self.routes.keys():
            if self.routes[prefix]['hijack']:
                asp = copy(self.routes[prefix]['AS_path'])
                hijack.append([prefix, asp])
        return hijack


class Graph:
    def __init__(self,root_folder:str='./data', override:bool=False, debug:bool=True):
        '''
        Create an object to represent AS connections.
        :param root_folder: Folder to save partial information (default = ./data)
        :param override: Set True to ignore and replace previous information if they exist
        '''
        self.ases = dict()
        self.roa = dict()
        self.hjk_announce = list()
        self.leg_announce = list()
        self.rov = list()
        self.tier1 = list()
        self.tier2 = list()
        self.ixp = list()
        self.vps = dict()
        self.vps_hjk = set()
        self.checked_hjk = False
        self.hjk_ases = set()
        self.countries = set()
        self.continents = set()
        self.root_folder = root_folder
        self.override = override
        self.debug = debug


    def add_connections(self, input_file:str):
        '''
        Add connections in the graph using AS relationship from CAIDA
        File source = https://publicdata.caida.org/datasets/as-relationships/serial-2/
        :param input_file: path to the file
        :return: None
        '''
        # Tier-2 source = https://en.wikipedia.org/wiki/Tier_2_network (accessed in 2024-11-11)
        tier2 = [6939, 7713, 9002, 1764, 34549, 4766, 9304, 22652, 9318, 3292, 2497, 1273, 2516, 23947, 4134, 4809,
                 4837, 3462, 5400, 7922, 1257, 12390, 2711, 8002, 14744, 38930, 33891, 41327, 7473, 24482, 9121,
                 6663, 7195]
        tier1 = list()
        ixp = list()
        self.tier2 = tier2
        if input_file.endswith('.bz2'):
            lines = bz2.open(input_file,'rt')
        else:
            lines = open(input_file,'r')

        for line in lines:
            if line.startswith('#'):
                if line.startswith("# input"):
                    tmp = line.split(':')
                    tmp = tmp[-1]
                    tmp = tmp.strip()
                    for t in tmp.split(' '):
                        tier1.append(int(t))
                    self.tier1 = tier1
                elif line.startswith('# IXP'):
                    tmp = line.split(':')
                    tmp = tmp[-1]
                    tmp = tmp.strip()
                    for t in tmp.split(' '):
                        ixp.append(int(t))
                    self.ixp = ixp
                continue
            tmp = line.strip('\n').split('|')
            if len(tmp)<3:
                continue
            as1 = int(tmp[0])
            as2 = int(tmp[1])
            conn = int(tmp[2])
            if not as1 in self.ases.keys():
                self.ases[as1] = AS(as1)
            if not as2 in self.ases.keys():
                self.ases[as2] = AS(as2)
            if conn == 0:
                self.ases[as1].add_peer(as2)
                self.ases[as2].add_peer(as1)
            elif conn == (-1):
                self.ases[as1].add_customer(as2)
                self.ases[as2].add_provider(as1)
        print(len(self.ases.keys()), 'ASes and their connections were loaded.')


    def add_siblings(self, asn:int, sibling:int):
        '''
        Not implement yet
        :param asn:
        :param sibling:
        :return: None
        '''
        if asn in self.ases.keys():
            self.ases[asn].add_sibling(sibling)
        else:
            print('AS not found!')


    def get_ases(self):
        '''
        Get all ASN presents in the graph.
        :return: a list with all ASes.
        '''
        return list(self.ases.keys())


    def get_fake_asp(self, asn:int()):
        '''
        Get forged AS path used by some AS to hijack a prefix
        :param asn: ASN (int)
        :return: a list of ASes in forged AS path (list)
        '''
        return self.ases[asn].get_fake_asp()


    def get_ases_infor(self):
        '''
        Return two information to create a pandas DataFrame to select the hijackers based on AS information
        Columns = 'asn','country','continent','degree'
        :return: columns names and a list with information to create a pandas DataFrame
        '''
        result = list()
        columns = ['asn','country','continent','degree']
        for asn in self.ases.keys():
            country = self.ases[asn].country
            continent = self.ases[asn].continent
            degree = len(self.ases[asn].customers) + len(self.ases[asn].providers) + len(self.ases[asn].peers)
            result.append([asn,country,continent,degree])
        return columns, result


    def get_as_infor(self, asn:int):
        '''
        Return AS information
        :return: Country, Continent and degree (number of neighbors)
        '''
        country = self.ases[asn].country
        continent = self.ases[asn].continent
        degree = len(self.ases[asn].customers) + len(self.ases[asn].providers) + len(self.ases[asn].peers)
        return (country,continent,degree)


    def get_neighbors_stats(self, asn:int):
        '''
        Return AS information
        :return: Country, Continent and degree (number of neighbors)
        '''
        if asn not in self.ases.keys():
            if self.debug:
                print('AS{} is not in the graph!'.format(asn))
            return None
        customers = self.ases[asn].customers
        providers = self.ases[asn].providers
        peers = self.ases[asn].peers
        neighbors = peers | customers | providers
        countries_c = set()
        continents_c = set()
        for n in customers:
            countries_c.add(self.ases[n].country)
            continents_c.add(self.ases[n].continent)
        countries_p = set()
        continents_p = set()
        for n in peers:
            countries_p.add(self.ases[n].country)
            continents_p.add(self.ases[n].continent)
        countries_pr = set()
        continents_pr = set()
        for n in providers:
            countries_pr.add(self.ases[n].country)
            continents_pr.add(self.ases[n].continent)
        countries = countries_c | countries_p | countries_pr
        continents = continents_c | continents_p | continents_pr
        result = {'Neighbors':{'Number':len(neighbors),'Countries':len(countries), 'Continents':len(continents)},
                  'Customers':{'Number':len(customers),'Countries':len(countries_c), 'Continents':len(continents_c)},
                  'Peers':{'Number':len(peers),'Countries':len(countries_p), 'Continents':len(continents_p)},
                  'Providers':{'Number':len(providers),'Countries':len(countries_pr), 'Continents':len(continents_pr)}}
        return result


    def print_as(self, asn:int):
        '''
        Print all AS information
        :param asn: ASN to print information (int)
        :return: None
        '''
        if asn in self.ases.keys():
            self.ases[asn].print_as()
        else:
            print('AS not found!')


    def print_route(self, asn:int):
        '''
        Print AS route information
        :param asn:  ASN to print information
        :return: None
        '''
        if asn in self.ases.keys():
            self.ases[asn].print_rib()
        else:
            print('AS{} not found!'.format(asn))


    def add_prefix(self, asn:int, prefix:str, roa:bool=False):
        '''
        Add a new prefix to AS
        :param asn: ASN that will announce a legitimate prefix.
        :param prefix: IPv4 prefix to announce
        :param roa: Enable Route Origin Authorization to this prefix and AS
        :return: True if the prefix was added, False if the AS is not in the graph
        '''
        if asn in self.ases.keys():
            self.ases[asn].add_prefix(prefix)
            if roa:
                p = Prefix(prefix)
                if p not in self.roa.keys():
                    self.roa[p] = set()
                self.roa[p].add(asn)
            return True
        else:
            print('ERROR: AS{} not found in the graph!!'.format(asn))
            return False



    def hijack(self, hijacker:int, prefix:str, fake_asp:list):
        '''
        Select a AS to hijack IP prefix
        :param hijacker: ASN to make a hijack (int)
        :param prefix: Hijacked prefix (X.X.X.X/X) - IPv4
        :param fake_asp: A forged AS path (list)
        :return: None
        '''
        if hijacker in self.ases.keys():
            self.ases[hijacker].hijack(prefix, fake_asp)
        else:
            print('ERROR: AS{} not found in the graph!!'.format(hijacker))


    def route_propagate(self, asn:int, hijack:bool=False, ignore_model_sometimes:bool=False):
        '''
        Announce the prefixes from the AS, legitimate or hijacked
        :param asn: ASN to announce the prefixes
        :param hijack: Is a hijacked Prefix? (True or False)
        :param ignore_model_sometimes: Ignore Gao-Rexford model when there are no connections to all ASes
        :return: None
        '''
        ases_new_route = set()
        without_route = set(self.ases.keys())
        if hijack:
            prefixes = self.ases[asn].get_hijacks()
            asp = self.ases[asn].get_fake_asp()
            self.hjk_announce = [asn, asp, prefixes]
            asp.insert(0,asn)
        else:
            prefixes = self.ases[asn].get_prefixes()
            asp = [asn]
            self.leg_announce = [asn, asp, prefixes]

        list_ases = self.ases[asn].customers | self.ases[asn].providers | self.ases[asn].peers
        nexts_ases = list()
        if len(prefixes)==0:
            print('No {} route to propagate from AS{}.'.format(('hijack' if hijack else 'legitimate'), asn))
        else:
            for n in list_ases:
                nexts_ases.append([n, copy(asp), prefixes])
            while len(nexts_ases)>0:
                n_asn, asp, prefixes = nexts_ases.pop(0)
                prefix_add = list()
                ases_new_route.add(n_asn)
                if self.ases[n_asn].is_rov_enabled():
                    for p in prefixes:
                        if p in self.roa.keys():
                            if asp[-1] in self.roa[p]:
                                prefix_add.append(p)
                            else:
                                if self.debug:
                                    print('ROV: AS{} reject prefix {} originated by AS{}.'.format(n_asn, p, asp[-1]))
                else:
                    prefix_add = prefixes
                tmp_ases, tmp_asp, tmp_prefixes = self.ases[n_asn].add_route(prefix_add, asp, hijack,debug=self.debug)
                for ta in tmp_ases:
                    nexts_ases.append([ta, tmp_asp, tmp_prefixes])
            without_route = without_route - ases_new_route
            if self.debug:
                print("{} routes propagated from the AS{} to {} ASes".format(('Hijacked' if hijack else 'Legitimate'), asn, len(ases_new_route)))
                print('{} AS(es) did not receive the route from the AS{}'.format(len(without_route), asn))
            if ignore_model_sometimes:
                more_routes = self.ignore_model_sometimes(prefixes)
                if self.debug:
                    print('More {} ASes added the route breaking Gao-Rexford model'.format(len(more_routes)))
        return without_route


    def all_route_propagate(self):
        '''
        Announce all prefixes from all ASes
        :return: None
        '''
        asns = self.ases.keys()
        for asn in asns:
            self.route_propagate(asn, hijack=False)
            self.route_propagate(asn, hijack=True)


    def clear_all_routes(self):
        '''
        Clear all ASes route information
        :return: None
        '''
        asns = self.ases.keys()
        for asn in asns:
            self.ases[asn].clear_routes()


    def restart_graph(self):
        '''
        Clear all ASes information (prefixes and routes) to start a new test with the same graph
        :return: None
        '''
        asns = self.ases.keys()
        for asn in asns:
            self.ases[asn].clear_all()
        self.roa.clear()
        self.hjk_announce.clear()
        self.checked_hjk = False
        self.leg_announce.clear()
        self.rov.clear()
        print('All clear!!!')


    def check_hijack(self, asn:int=0, print_ases:bool=False, nb_prefix_full_route:int=100000):
        '''
        Check which ASes have a route to a hijacked prefix
        :param asn: ASN to check if it has a hijack or 0 to all ASes
        :param print_ases: Show ASes information with hijacked route
        :param nb_prefix_full_route: Minimum number of prefixes exported by a VPS to be considered full route information
        :return: a set with the ASNs that have a route to prefix hijacked
        '''
        vps = set()
        if asn==0:
            asns = self.ases.keys()
        else:
            asns = [asn]
        hjk = set()
        for asn in asns:
            hijacks = self.ases[asn].has_hijack()
            if len(hijacks) > 0:
                hjk.add(asn)
                if self.ases[asn].vps_prefixes >= nb_prefix_full_route:
                    vps.add(asn)
                elif self.ases[asn].vps_prefixes > 0:
                    for p, asp in hijacks:
                        if asp[0] in self.ases[asn].customers:
                            vps.add(asn)
                if print_ases:
                    print('ASN{} has {} prefix(es) hijacked:'.format(asn, len(hijacks)))
                    for p in hijacks:
                        print('Prefix {} -> {}'.format(p[0], p[1]))
        print('{}/{} ASes got hijacked prefixes.'.format(len(hjk), len(asns)))
        print('{} VPs exported the hijacked route to the collectors.'.format(len(vps)))
        self.vps_hjk = vps
        self.checked_hjk = True
        self.hjk_ases = hjk
        return hjk


    def enable_rov(self, percentage:float=0, ases:list=[]):
        '''
        Random enable Route Origin Validations (ROV) in some X% ASes or enable in a list of ASes
        :param percentage: 0-100(%) or 0-1, pertentage of ASes to enable ROV
        :param ases: a list of ASes to enable ROV
        :return: None
        '''
        if percentage==0 and len(ases)==0:
            print('ERROR: Informe the percentage of ASes to enable ROV or informe the list of ASes to enable.')
            return None
        elif percentage>0 and len(ases)>0:
            print('ERROR: Informe the percentage of ASes to enable ROV or informe the list of ASes to enable.')
            return None
        if (percentage > 100 or percentage < 0) and len(ases)==0:
            print('Set percentage as a value between 1 and 100(%) or between 0 and 1.')
            return None
        if len(ases)==0:
            n = int((percentage/100) * len(self.ases.keys()))
            selected = random.sample(list(self.ases.keys()), n)
        else:
            selected = ases
        n_ases = 0
        for asn in selected:
            if asn in self.ases.keys():
                n_ases += 1
                self.ases[asn].set_rov(True)
            else:
                print('AS{} not found in the graph to enable ROV'.format(asn))
        print('ROV enabled in {} of {} ASes.'.format(n_ases, len(self.ases.keys())))
        self.rov=selected


    def check_graph(self):
        '''
        Check if the graph is full connected
        :return: None
        '''
        graphs = list()
        ases = list(self.ases.keys())
        while len(ases) > 0:
            graphs.append(set())
            i = len(graphs) - 1
            asi = ases.pop(0)
            graphs[i].add(asi)
            connections = self.ases[asi].providers | self.ases[asi].peers | self.ases[asi].customers | self.ases[asi].siblings
            while len(connections) > 0:
                c = connections.pop()
                if c in ases:
                    ases.remove(c)
                graphs[i].add(c)
                tmp = self.ases[c].providers | self.ases[c].peers | self.ases[c].customers | self.ases[c].siblings
                for t in tmp:
                    if not t in graphs[i]:
                        connections.add(t)

        print('{} graph(s) created.'.format(len(graphs)))
        for i, g in enumerate(graphs):
            print('{} -> with {} ASes'.format(i,len(g)))


    def only_has_peers(self, print_ases:bool=False):
        '''
        Print how many ASes have only peers connections
        :param print_ases: print ASes information (True or False)
        :return: None
        '''
        only_peers =  set()
        for asn in self.ases.keys():
            if len(self.ases[asn].peers)>0:
                if len(self.ases[asn].customers) == 0 and len(self.ases[asn].providers) == 0:
                    only_peers.add(asn)
        print('{}/{} ASes have only peer-to-peer connections.'.format(len(only_peers), len(self.ases.keys())))
        if print_ases:
            for asn in only_peers:
                print('ASN{} has only peer connections:'.format(asn))
                print('Peers: {}'.format(self.ases[asn].peers))


    def only_has_providers(self, print_ases:bool=False):
        '''
        Print how many ASes have only connections with providers
        :param print_ases: print ASes information (True or False)
        :return: None
        '''
        only_providers =  set()
        for asn in self.ases.keys():
            if len(self.ases[asn].providers)>0:
                if len(self.ases[asn].customers) == 0 and len(self.ases[asn].peers) == 0:
                    only_providers.add(asn)
        print('{}/{} ASes have only providers.'.format(len(only_providers), len(self.ases.keys())))
        if print_ases:
            for asn in only_providers:
                print('ASN{} has only providers:'.format(asn))
                print('Providers: {}'.format(self.ases[asn].proveiders))


    def only_has_customers(self, print_ases:bool=False):
        '''
        Print how many ASes have only connections with customers
        :param print_ases: print ASes information (True or False)
        :return: None
        '''
        only_customers =  set()
        for asn in self.ases.keys():
            if len(self.ases[asn].customers)>0:
                if len(self.ases[asn].providers) == 0 and len(self.ases[asn].peers) == 0:
                    only_customers.add(asn)
        print('{}/{} ASes have only customers.'.format(len(only_customers), len(self.ases.keys())))
        if print_ases:
            for asn in only_customers:
                print('ASN{} has only customers:'.format(asn))
                print('Customers: {}'.format(self.ases[asn].customers))


    def ignore_model_sometimes(self, prefixes:list):
        '''
        Ignore the Goa-Rexford model to propagate prefixes to all ASes
        :param prefixes: Prefixes to propagate
        :return: a set with ASN that received the route breaking the model
        '''
        ases = copy(list(self.ases.keys()))
        more_routes = set()
        try_again = True
        for i in range(2):
            if try_again:
                try_again = False
                for asn in ases:
                    known_prefixes = self.ases[asn].routes.keys()
                    for prefix in prefixes:
                        if prefix in known_prefixes:
                            continue
                        neighbors = (list(self.ases[asn].providers) + list(self.ases[asn].peers) +
                                     list(self.ases[asn].siblings) + list(self.ases[asn].customers))
                        while len(neighbors)>0:
                            n = neighbors.pop(0)
                            if prefix in self.ases[n].routes.keys():
                                asp = copy(self.ases[n].routes[prefix]['AS_path'])
                                if not asn in asp:
                                    hijack = copy(self.ases[n].routes[prefix]['hijack'])
                                    asp.insert(0,n)
                                    if n in self.ases[asn].providers:
                                        conn = 'provider'
                                    elif n in self.ases[asn].peers:
                                        conn = 'peer'
                                    elif n in self.ases[asn].siblings:
                                        conn = 'sibling'
                                    else:
                                        conn = 'customer'
                                    self.ases[asn].add_route([prefix],asp, hijack,debug=self.debug)
                                    more_routes.add(asn)
                                    if self.debug:
                                        print('Gao-Rexford ERROR: AS{} added route to {} from AS{} ({}).'.format(asn, prefix, n, conn))
                                    break
                        if len(neighbors) == 0:
                            try_again = True
        return more_routes


    def asp_type(self, asp:list):
        '''
        Check the AS path to classify it.
        :param asp: AS path (list of ASN)
        :return: AS path classification and the sequence by type connections
        '''
        path=list()
        asp = copy(asp)
        prev_asn = asp.pop(-1)
        result = ''
        for asn in reversed(asp):
            if asn in self.ases[prev_asn].peers:
                path.append(0) # peer-to-peer connection
            elif asn in self.ases[prev_asn].providers:
                path.append(1) # provider (asn) received announce from client (c2p) (up)
            elif asn in self.ases[prev_asn].customers:
                path.append(-1) # customer (asn) received announce from provider (p2c) (down)
            else:
                path.append(2) # Unkown
            prev_asn = asn
        got_c2p = False
        got_p2c = False
        got_p2p = False
        for p in path:
            if p == 1: # Up
                got_c2p = True
                if got_p2c or got_p2p:
                    result = 'valley_violation'
            elif p == 0:
                got_p2p = True
                if got_p2c: # Down
                    result = 'valley_violation'
            elif p == -1: # Down
                got_p2c = True
        if result == '':
            if got_c2p:
                result = 'Up'
                if got_p2p:
                    result += '-Peer'
                if got_p2c:
                    result += '-Down'
            elif got_p2p:
                result = 'Peer'
                if got_p2c:
                    result += '-Down'
            elif got_p2c:
                result = 'Down'
            else:
                result = 'Unkown'
        tmp = list(reversed(path))
        return result, tmp


    def export_hijack_as_paths(self,asn_leg:int, asn_hjk:int, ases:set, outfile:str = 'as_paths.csv'):
        '''
        Export hijacked AS path to a file and other information (Prefix;AS_path;Type;Sequence)
        :param asn_leg: the legitimate ASN to check the hijack
        :param asn_hjk: the hijecker ASN
        :param ases: a set of ASes to check the hijack
        :param folder: folder to create a file with information
        :return: None
        '''
        fake_asp = self.ases[asn_hjk].fake_asp
        asps = list()
        for asn in ases:
            tmp = self.ases[asn].has_hijack()
            if len(tmp)>0:
                asps += tmp
        result = []
        for prefix, asp in asps:
            asp_type, sequence = self.asp_type(asp)
            result.append([prefix, asp, asp_type, sequence])
        if os.path.isfile(outfile):
            lines = ''
        else:
            lines = 'Prefix;AS_path;Type;Sequence'
        line = '\n{};{};{};{}'
        for r in result:
            lines += line.format(r[0],r[1],r[2],r[3])
        with open(outfile,'a') as out:
            out.writelines(lines)


    def text_report(self, outfile:str, export_asp:bool=False, only_vps_asp:bool=True):
        '''
        Export information about hijack to a file
        :param outfile: file will create with output information (must end with .csv)
        :param export_asp: create files with hijacked AS paths
        :param only_vps_asp: Only create files with AS path from VPs
        :return: None
        '''
        if not (outfile.endswith('.csv') or outfile.endswith('.tmp')):
            outfile += '.csv'
        if len(self.leg_announce) == 0 or len(self.hjk_announce) == 0:
            print('To get a text report make one legitimate announce and one hijack announce first.')
        else:
            if self.checked_hjk == False:
                self.check_hijack()
            if len(self.countries) == 0:
                self.get_country_ases()
            p_leg = self.leg_announce[2]
            asn_leg = self.leg_announce[0]
            desc_leg = self.ases[asn_leg].description
            count_leg = self.ases[asn_leg].country
            cont_leg = self.ases[asn_leg].continent
            cus_leg = len(self.ases[asn_leg].customers)
            peers_leg = len(self.ases[asn_leg].peers)
            prov_leg = len(self.ases[asn_leg].providers)
            degree_leg = cus_leg + peers_leg +prov_leg
            roa = ('Y' if len(self.roa)>0 else 'N')
            p_hjk = self.hjk_announce[2]
            asn_hjk = self.hjk_announce[0]
            desc_hjk = self.ases[asn_hjk].description
            count_hjk = self.ases[asn_hjk].country
            cont_hjk = self.ases[asn_hjk].continent
            cus_hjk = len(self.ases[asn_hjk].customers)
            peers_hjk = len(self.ases[asn_hjk].peers)
            prov_hjk = len(self.ases[asn_hjk].providers)
            degree_hjk = cus_hjk + peers_hjk + prov_hjk
            fake_asp = self.ases[asn_hjk].get_fake_asp()
            t_ases = len(self.ases.keys())
            hjk_ases = self.hjk_ases
            rov = len(self.rov)
            lines = ''
            line = '\n{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{};{}'
            if not os.path.isfile(outfile):
                lines = ('Prefix_leg;Leg_ASN;Description_leg;Country_leg;Continent_leg;Customer_leg;Providers_leg;Peers_leg;Degree_leg;ROA;'
                         'Prefix_hjk;Hijacker;Description_hjk;Country_hjk;Continent_hjk;Customer_hjk;Providers_hjk;Peers_hjk;Degree_hjk;Forged_AS_path;Type;'
                         'Total_ASes;Contaminated_ASes;VPs_observ_hjk;ROV')
            lines += line.format(p_leg,asn_leg,desc_leg,count_leg,cont_leg,cus_leg,prov_leg,peers_leg,degree_leg,roa,
                                 p_hjk,asn_hjk,desc_hjk,count_hjk,cont_hjk,cus_hjk,prov_hjk,peers_hjk,degree_hjk,fake_asp,len(fake_asp),
                                 t_ases,len(hjk_ases),len(self.vps_hjk),rov)
            with open(outfile, 'a') as out:
                out.writelines(lines)
            if outfile.endswith('.csv'):
                asp_outfile = outfile.replace('.csv', '_as-path_type-{}.csv')
            else:
                asp_outfile = outfile.replace('.tmp', '_as-path_type-{}.csv')
            if export_asp:
                asp_outfile = asp_outfile.format(len(fake_asp))
                if only_vps_asp:
                    self.export_hijack_as_paths(asn_leg, asn_hjk, self.vps_hjk, outfile=asp_outfile)
                else:
                    self.export_hijack_as_paths(asn_leg, asn_hjk, hjk_ases, outfile=asp_outfile)


    def get_vps(self, rv:bool=True, ripe:bool=True):
        '''
        Get ASNs that export information to collectors (VPs)
        :param rv: Get RouteViews VPs (True or False)
        :param ripe: Get RIPE-RIS VPs (True or False)
        :return: a dict with VPs and how many prefixes they export
        '''
        # Based on DFOH code (source: https://dfoh.uclouvain.be/code)
        vps = dict()
        folder = self.root_folder
        if not os.path.isdir(folder):
            os.mkdir(folder)
        file = '{}/vps{}{}.pk'.format(folder, ('_rv' if rv else ''), ('_ripe' if ripe else ''))
        if os.path.isfile(file) and not self.override:
            with open(file,'rb') as f:
                vps = pk.load(f)
        else:
            if rv:
                url = 'http://www.routeviews.org/peers/peering-status.html'

                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

                for line in urllib.request.urlopen(url, context=ctx).read().decode().split('\n'):
                    if 'routeviews.org' in line:
                        line = ' '.join(line.split())
                        meta = line.split('|')[0]
                        metatab = meta.split(' ')

                        collector = metatab[0].replace('.routeviews.org', '')
                        asn = int(metatab[1])
                        nb_pref = int(metatab[3])
                        asn_name = line.split('|')[3]
                        if not asn in vps.keys():
                            vps[asn] = {'collector':collector,'nb_pref':0,'name':asn_name}
                        vps[asn]['nb_pref'] += nb_pref

            if ripe:
                url = 'https://www.ris.ripe.net/peerlist/all.shtml'
                cur_collector = None
                cur_line = 0
                for line in urllib.request.urlopen(url).read().decode().split('\n'):
                    line = line.strip()

                    if '<h2> RRC' in line:
                        cur_collector = line.split(' -- ')[0].replace('<h2>', '').strip()

                    # Get the AS number.
                    if cur_line == 0 and line.startswith('<td> <a href="https://stat.ripe.net/'):
                        linetab = line.split('<td>')
                        asn = int(linetab[1].split('>')[1].replace('</a', '').replace('AS', ''))
                        cur_line += 1

                    elif cur_line == 1:
                        linetab = line.split('<td>')
                        asn_name = linetab[1].replace('</td>', '').strip()
                        cur_line += 1

                    elif cur_line == 2:
                        linetab = line.split('<td>')
                        peerip = linetab[1].replace('</td>', '').strip()
                        cur_line += 1

                    elif cur_line == 3:
                        linetab = line.split('<td>')
                        nb_pref_ipv4 = int(linetab[1].replace('</td>', '').strip())
                        cur_line += 1

                    elif cur_line == 4:
                        linetab = line.split('<td>')
                        nb_pref_ipv6 = int(linetab[1].replace('</td>', '').strip())
                        cur_line = 0

                        if not asn in vps.keys():
                            vps[asn] = {'collector': cur_collector, 'nb_pref': 0, 'name': asn_name}
                        vps[asn]['nb_pref'] += nb_pref_ipv4 + nb_pref_ipv6

            with open(file, 'wb') as f:
                pk.dump(vps, f)
        total_vps = list()
        for asn in vps:
            if asn in self.ases.keys():
                self.ases[asn].set_vps(vps[asn]['nb_pref'])
                self.ases[asn].description += '({} - {})'.format(vps[asn]['name'], vps[asn]['collector'])
                total_vps.append(asn)
        print('From {} VPS, {} ASes were found in the graph and will be considered VPS based on information from RouteViews and/or RIPE-RIS.'.format(len(vps), len(total_vps)))
        self.vps = vps
        return vps


    def load_continents(self):
        '''
        Load Country and Continent information from file countries_and_continents.csv.
        This file has information from https://cloford.com/resources/codes/index.htm and was manually created.
        :return: a dict with country and continent information
        '''
        continent_file = '{}/countries_and_continents.csv'.format(self.root_folder)
        # Source continent information = https://cloford.com/resources/codes/index.htm accessed in 2024-11-11
        # CSV file was created with information in website table with same format (columns).
        result = dict()
        if os.path.isfile(continent_file):
            lines = open(continent_file, 'r')
            for line in lines:
                meta = line.strip('\n').split(';')
                country = meta[5]
                continent = meta[0]
                if not country in result.keys():
                    result[country]=continent
        else:
            print('Country and continent file not found ({})'.format(continent_file))
        return result


    def get_country_ases(self):
        '''
        Use information from 'https://thyme.apnic.net/current/data-used-autnums' to complete the graph with Country,
        Description and continent of the ASes.
        :return: None
        '''
        file = '{}/country.csv'.format(self.root_folder)

        if os.path.isfile(file) and not self.override:
            input_lines = open(file,'r')
            for line in input_lines:
                if line.startswith('asn'):
                    continue
                meta = line.strip('\n').split(';')
                asn = int(meta[0])
                description = meta[1]
                country = meta[2]
                continent = meta[3]
                if asn in self.ases.keys():
                    self.ases[asn].description = description
                    self.ases[asn].country = country
                    self.ases[asn].continent = continent
        else:
            url = 'https://thyme.apnic.net/current/data-used-autnums'
            input_lines = urllib.request.urlopen(url).read().decode().split('\n')
            country_continent = self.load_continents()
            lines = 'asn;description;country;continent'
            new_line = '\n{};{};{};{}'
            for line in input_lines:
                line = ' '.join(line.split())
                meta = line.split(',')[0]
                if len(meta) < 2:
                    continue
                asn = int(meta.split(' ')[0])
                description = meta.replace(str(asn)+' ','')
                country = line.split(',')[-1]
                country = country.strip()
                if country.upper() in country_continent.keys():
                    continent = country_continent[country]
                else:
                    continent = 'Unkown'
                lines += new_line.format(asn, description, country, continent)
                if asn in self.ases.keys():
                    self.ases[asn].description = description
                    self.ases[asn].country = country
                    self.ases[asn].continent = continent
                    self.countries.add(country)
                    self.continents.add(continent)
            with open(file, 'w') as f:
                f.writelines(lines)
        print('Countries and continents for ASes loaded!!!')


