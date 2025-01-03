import os
import pandas as pd
import progressbar

def convert(files:list):
    lines = ''
    bar = progressbar.ProgressBar(max_value=len(files), redirect_stdout=True)
    for i, input_file in enumerate(files):
        bar.update(i)
        df = pd.read_csv(input_file, sep=';')
        df['AS_path'] = df['AS_path'].str.strip('[]').str.split(', ')
        asps = df['AS_path'].values.tolist()
        for asp in asps:
            if len(asp)<4:
                continue
            as1 = asp[-1]
            as2 = asp[-2]
            tmp = ''
            for a in asp:
                if tmp == '':
                    tmp += a
                else:
                    tmp += ' ' + a
            if lines == '':
                lines += '{} {},{}'.format(as1, as2, tmp)
            else:
                lines += '\n{} {},{}'.format(as1, as2, tmp)
    bar.finish()
    return lines


if __name__ == '__main__':
    folder = './without_rov'
    date = '2024-04-01'
    input_files_t0 = []
    input_files_t1 = []
    files = os.listdir(folder)
    for f in files:
        file = '{}/{}'
        if f.endswith('type-0.csv') and date in f:
            input_files_t0.append(file.format(folder,f))
        elif f.endswith('type-1.csv') and date in f:
            input_files_t1.append(file.format(folder,f))

    lines = convert(input_files_t0)
    output_file = '{}/{}_as_path_dfoh_type-0'.format(folder, date)
    with open(output_file, 'w') as out:
        out.writelines(lines)
    print('File created: {}'.format(output_file))

    lines = convert(input_files_t1)
    output_file = '{}/{}_as_path_dfoh_type-1'.format(folder, date)
    with open(output_file, 'w') as out:
        out.writelines(lines)
    print('File created: {}'.format(output_file))
