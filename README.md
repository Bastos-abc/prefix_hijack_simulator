# Prefix Hijack Simulator

Material relacionado ao trabalho publicado -> https://sol.sbc.org.br/index.php/sbrc/article/view/35124

Este código tem por finalidade simular a propagação de diversos tipos de sequestro de prefixo.
Para a criação do ambiente é utilizada as informações de relacionamento entre ASes disponiblizada pela CAIDA (https://publicdata.caida.org/datasets/as-relationships/serial-2/).

Os arquivos *run_simulation.py* e *run_simulation_with_prepend.py* possuem exemplos de simulação, mas para sua execução os arquivos de entrada com a relação de ASes e seus prefixos para a simulação devem ser alimentados. 
O arquivo *input/ases_prefixes.csv* contém a relação de ASes que serão as vítimas na simulação e deve seguir o exemplo de formatação abaixo mantendo a linha com o título das colunas:

```
ASN;Prefix;Country;Desc_AS
1;10.1.1.0/24;br;AS 1
2;10.2.2.0/24;ar;AS 2
```
Para simulação com prepend, um arquivo com as informações do AS, seu vizinho e a quantidade de vezes a mais que o ASN será inserido deve ser gerado com *tools/create_prepend_file_to_simulation.py* a partir dos arquivos baixados previamente dos coletores (https://archive.routeviews.org/ e/ou https://ris.ripe.net/docs/mrt/) ou gerado manualmente com a seguinte formatação mantendo a linha com o título das colunas:

```
AS;Neighbor;Prepend
1;2;2
1;3;1
1;6;2
2;5;2
2;3;1
```
Os arquivos podem ser baixados dos coletores com o código *tools/download_files_from_colectors.py*, no exemplo abaixo será baixado a primeira RIB (-t rib) de todos os coletores relacionados no arquivo *config.py* do dia 01/02/2024 (-y 2024 -m 02 -d 01) de somente 1 dia (-D 1):
```
python3 download_files_from_colectors.py -y 2024 -m 02 -d 01 -D 1 -t rib
```
