import os.path
import subprocess
import pickle as pk
import progressbar
import pandas as pd


def get_files(folder:str, date:str):
    '''
    Create a list with downloaded files from colectors for a date
    :param date: 'YYYY-MM-DD'
    :return : a list with files
    '''
    folders=[folder]
    files = []
    while len(folders)> 0:
        tmp = folders.pop()
        date = date.replace('-','')
        if os.path.isdir(tmp):
            tmp_f = os.listdir(tmp)
            for f in tmp_f:
                folders.append(tmp+'/'+f)
        elif date in tmp:
            files.append(tmp)

    return files


def reading_files(files:list, ases:list, outfile:str):
    '''
    Get prepend information for ASes from files
    :param files: a list of files
    :param ases: a list of ASes to analyze
    :param outfile: path to save information
    :return: a dict with information
    '''
    result = dict()
    if os.path.isfile(outfile):
        with open(outfile, 'rb') as of:
            result = pk.load(of)
    else:
        bar = progressbar.ProgressBar(max_value=len(files), redirect_stdout=True)
        for a in ases:
            result[a]=dict()
        i = 0
        for file in files:
            i += 1
            bar.update(i)
            command = "bgpdump -M {}".format(file)
            output = subprocess.check_output(command, shell=True)
            output = output.decode('utf-8')
            for line in output.split('\n'):
                tmp = line.split('|')
                if len(tmp)>7:
                    asp = tmp[6]
                    vp = int(tmp[4])
                    prefix = tmp[5]
                    if '{' in asp:
                        continue
                    asp = asp.split(' ')
                    asp_t = []
                    for a in asp:
                        try:
                            asp_t.append(int(a))
                        except:
                            continue
                    if len(asp_t)<2:
                        continue
                    origem = asp_t[-1]
                    if origem in ases:
                        if not vp in result[origem].keys():
                            result[origem][vp] = dict()
                        if not prefix in result[origem][vp].keys():
                            result[origem][vp][prefix]=[]
                        result[origem][vp][prefix].append(asp_t)
        bar.finish()
        with open(outfile, 'wb') as of:
            pk.dump(result, of)

    return result

def create_df(result:dict, outfile:str):
    '''
    Create a pandas DataFrame with prepend information
    :param result: Previous dict calculated
    :param outfile: path to save .csv file
    :return: a pandas DataFrame
    '''
    columns = ['AS','VP','Prefix','AS_path','X_origin','X_others']
    df_list = []
    for asn in result.keys():
        for vp in result[asn].keys():
            for prefix in result[asn][vp].keys():
                for asp in result[asn][vp][prefix]:
                    x_origem = asp.count(asn)
                    x_demais = 1
                    for a in asp:
                        qtde = asp.count(a)
                        if qtde>x_demais:
                            x_demais=qtde
                    df_list.append([asn,vp,prefix,asp,x_origem,x_demais])

    df = pd.DataFrame(df_list, columns=columns)
    df.to_csv(outfile, index=False, sep=';')
    return df


def create_file(df:pd.DataFrame, date:str, input_folder:str='../input'):
    '''
    Create a file formated to be used in "run_simulation_with_prepend.py"
    :param df: a pandas DataFrame with prepends information
    :param date: The date of information
    :param input_folder: Path of simulation input folder to save de file
    :return: None
    '''
    if not os.path.isdir(input_folder):
        os.mkdir(input_folder)
    df_origin = df.loc[df['X_origin'] > 1]
    ases_orig = set(df_origin['AS'].values.tolist())
    prepend_origin = dict()

    for asn in ases_orig:
        neighbors = set()
        prepend_origin[asn] = {}
        asps = df_origin.loc[df_origin['AS'] == asn]['AS_path'].values.tolist()
        for asp in asps:
            asp = asp.replace('[', '').replace(']', '').split(', ')
            tmp_asp = []
            for a in asp:
                tmp_asp.append(int(a))
            p = tmp_asp.count(asn) - 1
            neigbord = tmp_asp[0]
            for tp in tmp_asp:
                if tp == asn:
                    break
                neigbord = tp
            neighbors.add(neigbord)
            if p > 0:

                if not neigbord in prepend_origin[asn].keys():
                    prepend_origin[asn][neigbord] = 0
                if p > prepend_origin[asn][neigbord]:
                    prepend_origin[asn][neigbord] = p
    columns = ['AS', 'Neighbord', 'Prepend']
    result = []
    for a in prepend_origin.keys():
        for n in prepend_origin[a].keys():
            result.append([a, n, prepend_origin[a][n]])
    dfneig = pd.DataFrame(result, columns=columns)
    dfneig.to_csv('{}/asn_prepend_{}.csv'.format(input_folder, date), index=False, sep=';')


if __name__ == '__main__':
    dates = ['2024-02-01', '2024-03-01', '2024-04-01']
    input_folder = '../input'
    outfolder = './prepend' # to save DataFrame and dict with prepend information
    ases = [] # A list of ASN to create file to use in "run_simulations_with_prepend.py"
    if not os.path.isdir(outfolder):
        os.mkdir(outfolder)
    for date in dates:
        files = get_files('./RIB', date)
        outfile = '{}/{}.pk'.format(outfolder, date)
        result = reading_files(files, ases, outfile)
        outfile = '{}/{}.csv'.format(outfolder, date)
        df = create_df(result, outfile)
        create_file(df, date, input_folder)
