from graph import Graph
import pandas as pd
import random

class Hijackers:
    def __init__(self, internet:Graph):
        '''
        Create an object to select a set of hijackers based in a graph
        :param internet: Graph object with ASes and their connections
        '''
        self.hjk_ranges = list()
        self.clusters = dict()
        self.internet = internet
        columns, data = internet.get_ases_infor()
        self.df_degree = pd.DataFrame(data,columns=columns)
        self.victim = 0

    def create_clusters(self, ranges:list):
        '''
        Inform the ranges to create a clusters of ASes to select the hijackers.
        The range needs to be a list with ranges for all groups, like [[1,2],[3,3],[4,10],[11,0]].
        If the range has the same number, only ASes with this degree will be considered.
        The number 0 (zero) in the last cluster represents the maximum number of degrees.
        :param ranges: a list with minimum and maximum degree for any cluster to create.
        :return: None
        '''
        max_nb = 0
        nb_clusters = len(ranges)
        for i, (m1, m2) in enumerate(ranges):
            if m1 > m2:
                if i+1 < nb_clusters or m2 != 0:
                    print('Error: check the range format.')
                    break
                elif m2 == 0:
                    m2 = max(self.df_degree['degree'].values.tolist())
                    self.hjk_ranges.append([m1, m2])
            elif m1 <= max_nb:
                print('Error: check the sequence of the range.')
                break
            else:
                self.hjk_ranges.append([m1, m2])
                max_nb = m2
        print('{} clusters were created.'.format(len(self.hjk_ranges)))

        for i, (m1,m2) in enumerate(self.hjk_ranges):
            dft = self.df_degree.loc[(self.df_degree['degree']>=m1)&(self.df_degree['degree']<=m2)]
            data_tmp = dft.values.tolist()
            self.clusters[i]=dict()
            for asn, country, continent, degree in data_tmp:
                self.clusters[i][asn]={'country':country, 'continent':continent}
            r_degree = ('degree = {}'.format(m1) if m1 == m2 else 'degree between {} and {}'.format(m1,m2))
            print('Cluster {} ({}) have {} ASes.'.format(i, r_degree,len(self.clusters[i].keys())))


    def select_victim(self, asn:int):
        '''
        Inform AS victim to set parameters to select the hijackers
        :param asn: ASN of AS victim
        :return: None
        '''
        self.victim = asn


    def hijackers_same_continent(self, nb:int):
        '''
        Get N hijackers from the same continent of the AS victim
        :param nb: how many hijackers per cluster
        :return: list of ASNs
        '''
        if self.victim == 0:
            print('Select the AS victim first!!!!')
            return None
        continent = self.internet.ases[self.victim].continent
        hijackers = list()
        for k in self.clusters.keys():
            candidates = list()
            for asn in self.clusters[k].keys():
                if self.clusters[k][asn]['continent'] == continent and asn != self.victim:
                    candidates.append(asn)
            hijackers += random.sample(candidates, nb)
        return hijackers


    def hijackers_other_continents(self, nb:int):
        '''
        Get N hijackers from the different continents of the AS victim
        :param nb: how many hijackers per cluster
        :return: list of ASNs
        '''
        if self.victim == 0:
            print('Select the AS victim first!!!!')
            return None
        continent = self.internet.ases[self.victim].continent
        hijackers = list()
        for k in self.clusters.keys():
            candidates = list()
            for asn in self.clusters[k].keys():
                if self.clusters[k][asn]['continent'] != continent and asn != self.victim:
                    candidates.append(asn)
            hijackers += random.sample(candidates, nb)
        return hijackers


    def hijackers_same_country(self, nb:int):
        '''
        Get N hijackers from the same country of the AS victim
        :param nb: how many hijackers per cluster
        :return: list of ASNs
        '''
        if self.victim == 0:
            print('Select the AS victim first!!!!')
            return None
        country = self.internet.ases[self.victim].country
        hijackers = list()
        for k in self.clusters.keys():
            candidates = list()
            for asn in self.clusters[k].keys():
                if self.clusters[k][asn]['country'] == country and asn != self.victim:
                    candidates.append(asn)
            hijackers += random.sample(candidates, nb)
        return hijackers


    def hijackers_other_countries(self, nb:int):
        '''
        Get N hijackers from the different countries of the AS victim
        :param nb: how many hijackers per cluster
        :return: list of ASNs
        '''
        if self.victim == 0:
            print('Select the AS victim first!!!!')
            return None
        country = self.internet.ases[self.victim].country
        hijackers = list()
        for k in self.clusters.keys():
            candidates = list()
            for asn in self.clusters[k].keys():
                if self.clusters[k][asn]['country'] != country and asn != self.victim:
                    candidates.append(asn)
            hijackers += random.sample(candidates, nb)
        return hijackers


    def any_hijackers(self, nb:int):
        '''
        Get N hijackers
        :param nb: how many hijackers will be selected
        :return: list of ASNs
        '''
        if self.victim == 0:
            print('Select the AS victim first!!!!')
            return None
        candidates = self.internet.get_ases()
        candidates.remove(self.victim)
        return random.sample(candidates, nb)


    def hijackers_by_country(self, nb:int, country:str):
        '''
        Get N hijackers from the country
        :param nb: how many hijackers will be selected
        :param country: The country where the ASes are from that will be selected to be hijacker
        :return: list of ASNs
        '''
        if self.victim == 0:
            print('Select the AS victim first!!!!')
            return None
        if country.upper() not in (c.upper() for c in self.internet.countries):
            print('Use ISO 3166 two characters code to select the country.\n'
                  'Look at the file \"./data/countries_and_continents.csv\" column ISO(2).')
            return None
        hijackers = list()
        candidates = list()
        for asn in self.internet.get_ases():
            if self.internet.ases[asn].country.upper() == country.upper() and asn != self.victim:
                candidates.append(asn)
        hijackers += random.sample(candidates, nb)
        return hijackers


    def hijackers_by_continent(self, nb:int, continent:str):
        '''
        Get N hijackers from the continent
        :param nb: how many hijackers will be selected
        :param continent: The continent where the ASes are from that will be selected to be hijacker
        :return: list of ASNs
        '''
        if self.victim == 0:
            print('Select the AS victim first!!!!')
            return None
        if continent.upper() not in (c.upper() for c in  self.internet.continents):
            print('Not found any AS in this continent. Check if it\'s write correctly ({}).\n'.format(continent),
                  'Look at the file \"./data/countries_and_continents.csv\" column Continent.')
            return None
        hijackers = list()
        candidates = list()
        for asn in self.internet.get_ases():
            if self.internet.ases[asn].continent.upper() == continent.upper() and asn != self.victim:
                candidates.append(asn)
        hijackers += random.sample(candidates, nb)
        return hijackers


    def hijackers_by_clusters(self, nb:int, legitimate_ases:list=[]):
        '''
        Get N hijackers per clusters
        :param nb: how many hijackers per cluster
        :param legitimate_ases: list of legitimate ASes to bre exclude from candidates to be a hijacker,
        if empty, only the legitimate AS informed will be excluded
        :return: list of ASNs
        '''
        if self.victim == 0 and len(legitimate_ases)==0:
            print('Select the AS victim first!!!!')
            return None
        hijackers = list()
        for k in self.clusters.keys():
            candidates = list()
            for asn in self.clusters[k].keys():
                if asn != self.victim and asn not in legitimate_ases:
                    candidates.append(asn)
            hijackers += random.sample(candidates, nb)
        return hijackers
