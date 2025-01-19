# Prefix Hijack Simulator

Este código tem por finalidade simular a propagação de diversos tipos de sequestro de prefixo.
Para a criação do ambiente é utilizada as informações de relacionamento entre ASes disponiblizada pela CAIDA (https://publicdata.caida.org/datasets/as-relationships/serial-2/).

Os arquivos *run_simulation.py* e *run_simulation_with_prepend.py* possuem exemplos de simulação, mas para sua execução os arquivos de entrada com a relação de ASes e seus prefixos para a simulação devem ser alimentados. 
O arquivo *input/ases_prefixes.csv* contém a relação de ASes que serão as vítimas na simulação e deve seguir o exemplo de formatação abaixo:

- input/ases_prefix.csv<\br>
ASN;Prefix;Country;Desc_AS<\br>
1;10.1.1.0/24;br;AS 1

2;10.2.2.0/24;ar; AS 2

Para simulação com prepend, um arquivo com as informações do AS, seu vizinho e a quantidade de vezes a mais que o ASN será inserido deve ser gerado com tools/create_prepend_file_to_simulation.py a partir dos arquivos já baixados dos coletores (https://archive.routeviews.org/ e/ou https://ris.ripe.net/docs/mrt/) ou gerado manualmente com a seguinte formatação:

-input/asn_prepend_2024-04-01.csv

AS;Neighbor;Prepend

1;2;2

1;3;1

1;6;2

2;5;2

2;3;1
