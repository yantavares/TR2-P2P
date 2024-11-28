# TR2-P2P
Implementação de um Sistema P2P com Funcionalidades de Comunicação, Compartilhamento de Arquivos e Incentivo ao Uso Colaborativo da Rede 

## Descrição Geral 

Este trabalho tem como objetivo implementar um sistema Peer-to-Peer (P2P) simplificado que permita: 

- Comunicação por chat entre peers. 
- Busca e compartilhamento de arquivos (incluindo imagens, vídeos e documentos). 
- Transferência de arquivos com suporte a múltiplas conexões paralelas para melhorar a taxa de download. 
- Uso de um mecanismo de incentivo que priorize peers mais colaborativos na rede. 
- Os grupos (compostos por 2 ou 3 alunos) devem aplicar conceitos das camadas de aplicação, transporte, rede e enlace, desenvolvendo um sistema funcional durante o período do semestre. 

## Funcionalidades Obrigatórias 

- Chat entre peers: 
- Comunicação direta entre dois peers conectados. 
- Busca de arquivos na rede: 
- Um peer deve ser capaz de buscar arquivos disponíveis a partir de metadados. 
- Transferência de arquivos: 
- Implementar envio e recebimento de arquivos diretamente entre peers. 
- Divisão de arquivos em blocos para transferência em conexões paralelas (ex.: até N conexões simultâneas, onde N>2). Este tipo de mecanismo pode ser utilizado como forma de incentivo.  
- Conexão a um tracker centralizado: 
- O tracker é responsável por gerenciar a lista de peers ativos e permitir que os clientes descubram uns aos outros.  
- Interface básica: 
- Um cliente com interface simples para interagir com as funcionalidades descritas. 
 

## Mecanismo de Incentivo 

O trabalho deve incluir um mecanismo de incentivo que priorize peers mais colaborativos na rede. Esse mecanismo deve ser baseado em uma métrica definida pelo grupo, tais como: 

- Volume de compartilhamento: 
- Priorizar peers que compartilhem mais arquivos ou dados na rede. 
- Tempo de uso:
- Peers com mais tempo conectados podem receber maior prioridade. 
- Comportamento colaborativo: 
- Incentivar peers que frequentemente respondem a pedidos de outros usuários. 
- Métrica híbrida (sugerido): 
- Combinação de critérios, como volume compartilhado e tempo de conexão, para calcular uma pontuação de incentivo. 

O incentivo pode ser uma taxa maior de download (ou seja, se temos N conexões paralelas, um peer com maior incentivo poderia ter maiores taxas de download). Ou, de outra forma, peers com menor incentivo teriam uma taxa de download limitada em M Kbps por exemplo.  

## Entregáveis 

- Código-fonte: 
- Implementação funcional, organizada e documentada. 
- Relatório técnico: 
- Arquitetura do sistema. 
- Especificação do protocolo usado (chat, transferência e tracker). 
- Descrição do mecanismo de incentivo e sua métrica. 
- Análise de desempenho com e sem o uso de múltiplas conexões paralelas (sugestão de testes com 1, 2, 3 e 4 conexões paralelas para baixar um arquivo com volume considerável).  
- Testes de desempenho do mecanismo de limite de banda. 
- Demonstração: 
- Conexão de peers via tracker. 
- Busca e transferência de arquivos com múltiplas conexões. 
- Mostra de como o mecanismo de incentivo prioriza peers na rede. 

## Critérios de Avaliação 

- Funcionalidade: 
- O sistema atende aos requisitos especificados? 
- Qualidade técnica: 
- Implementação das conexões paralelas e/ou mecanismos de limite de taxa de download. 
- Eficiência do mecanismo de incentivo. 
- Clareza e completude: 
- Documentação e apresentação dos resultados. 
