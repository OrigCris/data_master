# Azure Data Pipeline Demonstration

## I. Resumo
Este projeto visa demonstrar a criação de uma pipeline completa de processamento de dados utilizando diversas ferramentas da Microsoft Azure. Inicialmente, o **Azure Functions** produz dados usando a biblioteca faker do python e utilizando uma **Service Principal Name (SPN)** para autenticação segura, os dados produzidos são enviados para o **Event Hub**, que atua como um hub central para ingestão de dados em tempo real. Posteriormente, o **Databricks** é utilizado para processar as informações com **Spark Streaming**, configurado com a opção de **trigger once** para realizar a ingestão apenas quando novos dados estão disponíveis, economizando recursos computacionais.

No Databricks, os dados são armazenados na camada Bronze para ingestão bruta, passam por um processo de tratamento e normalização na camada Silver e, finalmente, são agregados na camada Gold. A camada Gold é utilizada para consolidar informações importantes que podem ser visualizadas em ferramentas de Business Intelligence (BI).

## II. Objetivo
O objetivo principal deste projeto é ilustrar como integrar e utilizar o Azure Functions, Event Hub e Databricks para criar uma solução eficiente de processamento e análise de dados. 
<br>A partir deste projeto, pretende-se mostrar:
  - Como o Azure Functions pode ser utilizado para envio de dados de forma segura ao Event Hub.
  - A eficiência do Event Hub como ponto central de ingestão de dados em tempo real.
  - O uso do Databricks para processar dados com Spark Streaming, otimizando a ingestão de dados com a opção de trigger once.
  - O fluxo de dados desde a camada Bronze até a camada Gold, incluindo ingestão bruta, tratamento e normalização, e agregação de informações.

Esse case foi desenvolvido com o intuito de proporcionar um entendimento claro e prático de como essas ferramentas podem ser usadas em conjunto para resolver problemas reais de processamento de dados, além de demonstrar a flexibilidade e a robustez da plataforma Azure.

## III. Arquitetura de solução e Arquitetura técnica
### Arquitetura Solução
Com esta arquitetura visamos mostrar de forma simples e direta como será o pipeline de dados deste projeto. A solução envolve coletar dados de uma API e processá-los para obter insights valiosos, no caso, usamos dados fícticios para exemplificar isso. Começamos coletando os dados e enviando-os para um sistema de armazenamento temporário. Em seguida, os dados são processados e transformados, garantindo que sejam limpos e estruturados. Por fim, podemos usar ferramentas de BI para gerar valores em cima dos dados.
Essa arquitetura visa ilustrar uma pipeline de dados completa, desde a sua captura, transformação e armazenamento dos dados.
<p align="center">
  <img src="Imagens\arquitetura_solucao.png" alt="Arquitetura de solução" width="1000px"/>
</p>

### Arquitetura Técnica
<p align="center">
  <img src="Imagens\arquitetura_tecnica.png" alt="Arquitetura técnica" width="1000px"/>
</p>

#### 1. Azure Functions
  &nbsp;&nbsp;**Coleta de Dados**: As Azure Functions coletam dados de uma API específica.<br/>
  &nbsp;&nbsp;**Envio de Dados**: Depois, esses dados são enviados para o EventHub usando uma Service Principal (SPN), garantindo segurança na autenticação e autorização.<br/>
  &nbsp;&nbsp;**Motivo da Escolha**: Escolhemos Azure Functions pela capacidade de escalar automaticamente e pela facilidade de execução de códigos sem precisar gerenciar infraestrutura. Além disso, são ideais para tarefas baseadas em eventos, como coletar dados de APIs.
  
#### 2. EventHub
  &nbsp;&nbsp;**Buffer de Dados**: O EventHub serve como um buffer para os dados coletados, garantindo que sejam recebidos e armazenados temporariamente antes de serem processados.<br/>
  &nbsp;&nbsp;**Motivo da Escolha**: O EventHub é ótimo para ingerir grandes volumes de dados em tempo real, com alta disponibilidade e baixa latência, perfeito para cenários de streaming de dados.

#### 3. Databricks
  &nbsp;&nbsp;**Busca de Dados**: O Databricks busca os dados no EventHub.<br/>
  &nbsp;&nbsp;**Processamento e Transformação**:
  - Bronze: Utiliza Spark Streaming para ingerir dados brutos em tempo real.
  - Silver: Faz a limpeza e transformação dos dados em batch.
  - Gold: Armazena os dados refinados e prontos para análises, também em batch.

  &nbsp;&nbsp;**Escrita de Dados**: Os dados processados são escritos no Storage Account usando SPN para segurança.<br/>
  &nbsp;&nbsp;**Motivo da Escolha**: Escolhemos o Databricks por sua capacidade poderosa de processamento de dados, integração com Apache Spark e facilidade de uso com notebooks colaborativos. Ele permite processamento em tempo real e em batch, atendendo diversas necessidades.

#### 4. Storage Account
&nbsp;&nbsp;**Armazenamento de Dados**: O Storage Account guarda os dados em diferentes estágios (bronze, silver, gold), gerenciando os dados de forma eficiente e segura.<br/>
&nbsp;&nbsp;**Motivo da Escolha**: Escolhemos o Azure Storage Account por sua alta durabilidade, escalabilidade e segurança para armazenar grandes volumes de dados. Ele é econômico e acessível para diferentes usos.<br/>

## IV. Explicação de como foi desenvolvido
### 1. Configuração da Infraestrutura
Para iniciar o processo, executamos o [script.sh](Infraestrutura/script.sh) disponível no repositório do Git. Este script é responsável por criar todas as infraestruturas necessárias para o projeto, incluindo recursos no Azure como EventHub, Azure Functions e Databricks.

### 2. Implementação da Função no Azure Functions
Para a implementação da função no Azure Functions, utilizamos o arquivo [func_user.py](Infraestrutura/Functions/func_user.py), disponível no repositório do Git. Este arquivo contém o código em Python necessário para processar os dados e enviá-los para o EventHub. A função é implantada no Azure Functions, onde é executada em resposta a eventos, processando e transmitindo os dados de forma eficiente.

### 3. Envio de Dados utilizando SPN
A função Python implementada no Azure Functions utiliza uma Service Principal Name (SPN) para autenticação segura e envio dos dados ao EventHub. A SPN garante que a comunicação entre os serviços seja segura e confiável.

### 4. Integração com Databricks
No Databricks, utilizamos outra SPN para autenticação e busca dos dados enviados para o EventHub. Este processo é realizado utilizando o Spark Streaming, que consome os dados do EventHub em tempo real.

### 5. Arquitetura Medallion no Databricks
A arquitetura Medallion é implementada no Databricks para organizar e processar os dados em camadas, visando melhorar a qualidade e a acessibilidade dos dados. Este processo é dividido em três camadas principais:

#### Camada Bronze
Utilizando o Spark Streaming, os dados brutos são consumidos do EventHub e armazenados na camada Bronze. Esta camada contém os dados em seu formato original, conforme recebidos do EventHub.

#### Camada Silver
Em seguida, os dados são processados em lote (batch) utilizando Spark. Durante este processo, realizamos a normalização e limpeza dos dados. Os dados tratados são armazenados na camada Silver, que apresenta um formato mais estruturado e pronto para análises.

#### Camada Gold
Finalmente, os dados são transformados e agregados na camada Gold. Esta camada contém dados altamente estruturados e otimizados para análise de negócios e geração de relatórios. A camada Gold oferece a melhor qualidade de dados, pronta para consumo por ferramentas de BI e análises avançadas.

## V. Passo a passo para a implementação

### 1. Criando todos os recursos
Passos para executar o script:
  1. Faça o upload do arquivo para o Cloud Shell.
  2. Conceda permissão de execução ao script com o comando: `chmod +x script.sh`
  3. Execute o script, passando o caminho onde ele se encontra: `./script.sh`

<p align="center">
  <img src="Imagens\cloud_shell_import.png" alt="Import script.sh" width="500px">
</p>

Feito isso já podemos ver os recursos criados dentro do *resource group*

### 2. Realizando o deploy da Função no Azure Functions
Passos para a implementação:
  1. Faça o deploy do arquivo func_user.py para o Azure Functions (<a href="https://learn.microsoft.com/en-us/azure/azure-functions/create-first-function-vs-code-python">Como fazer o deploy</a>).
  2. Acompanhe a execução da função para verificar se os dados estão sendo processados e enviados corretamente para o EventHub.

### 3. Preparando o ambiente do Databricks
  1. Primeiro precisamos de uma `scope`, que será necessário para que possamos realizar nossos acessos (<a href="https://learn.microsoft.com/en-us/azure/databricks/security/secrets/">Como criar o secret scope</a>).
  2. Já com o `scope` criado podemos criar o nosso cluster, o arquivo json irá apoiar nisso, [cluster_json](Databricks/cluster.json). (Não esqueça de substituir os dados da SPN)
  3. Adicione a biblioteca maven para conectar ao EventHub: em **"bibliotecas"**, clique em **"instalar novo"**, selecione `maven` e procure por `com.microsoft.azure:azure-eventhubs-spark_2.12:2.3.22`
  4. Importe os notebooks disponíveis no GIT e coloque-os para rodar.

Obs: Em todos os passos e configurações, não esquecer de trocar os nomes das variáveis de acordo com a sua configuração.

## VI. Monitoramento com Azure Monitor
### 1. Introdução
Neste case, usamos o Azure Monitor para garantir a observabilidade e o monitoramento contínuo dos diversos recursos da nossa solução. O monitoramento é essencial para garantir a eficiência, disponibilidade e desempenho das aplicações, ajudando a identificar e resolver problemas rapidamente.

### 2. Objetivos do Monitoramento
O monitoramento visa:
- Detectar Problemas Proativamente: Identificar problemas antes que impactem os usuários.
- Otimização de Desempenho: Analisar métricas para otimizar a execução dos serviços.
- Garantia de SLA: Assegurar que os níveis de serviço acordados (SLA) sejam cumpridos.
- Segurança e Conformidade: Monitorar logs para garantir conformidade com as políticas de segurança.

### 3. Recursos Monitorados
Utilizamos o Azure Monitor para acompanhar as seguintes métricas:

#### Eventhub:
  1. Requests: Número de requisições processadas.
  2. Mensagens Enviadas: Total de mensagens enviadas.
  3. Mensagens Lidas: Total de mensagens lidas.

#### Function App:
  1. Número de Execuções: Quantas vezes as funções foram executadas.
  2. Memory Working Set: Uso de memória das funções.
    
#### Storage Account:
  1. Transações Realizadas: Total de transações.

#### Databricks:
  1. Memória Disponível: Quantidade de memória disponível nos clusters.
  2. Média de Uso de CPU (%): Média do uso de CPU nos clusters.

<p align="center">
  <img src="Imagens\monitoramento_1.jpeg" alt="Monitoramento 1" width="900px"/> 
  <img src="Imagens\monitoramento_2.jpeg" alt="Monitoramento 2" width="900px"/>
  <img src="Imagens\monitoramento_3.jpeg" alt="Monitoramento 3" width="900px"/>
</p>

A implementação do monitoramento com o Azure Monitor é essencial para assegurar a operação adequada de todos os recursos da solução. Isso permite que a equipe de desenvolvimento se concentre em melhorar continuamente a aplicação, sabendo que qualquer problema será rapidamente detectado e resolvido.

O dashboard oferece informações cruciais para identificar possíveis problemas na ingestão de dados ou gargalos na pipeline. Para resolver esses problemas (troubleshooting), basta clicar no recurso à direita do painel, o que permite uma análise detalhada das métricas e logs correspondentes.

Para as métricas do Spark, é fundamental acessar também as métricas e logs do cluster. Isso ajuda a identificar a causa raiz de qualquer problema potencial.

## VII. Melhorias e Considerações Finais

Para melhorar a resiliência de nossa Function App, propomos a implementação de um sistema de filas. Em um ambiente de computação em nuvem, a disponibilidade e a resiliência são fatores cruciais para garantir que os dados sejam processados de maneira eficiente e confiável. As intermitências do EventHub podem representar um desafio significativo, pois podem resultar na perda de dados valiosos. Portanto, a solução proposta é a implementação de uma fila (Queue), como o Azure Queue Storage ou o Azure Service Bus Queue, para armazenar temporariamente os dados recebidos do EventHub durante essas intermitências.

A implementação de uma fila oferece vários benefícios. Primeiro, ela melhora a resiliência do sistema, garantindo que nenhum dado seja perdido, mesmo quando o EventHub enfrenta intermitências. Os dados armazenados na fila podem ser processados pela Function App assim que a conexão com o EventHub for restabelecida. Além disso, essa abordagem permite que o sistema lide de forma mais eficiente com picos de carga, escalando conforme necessário para garantir a continuidade do processamento de dados.

Essa abordagem não apenas melhora a resiliência e a escalabilidade do sistema, mas também oferece uma camada adicional de redundância, fundamental para sistemas críticos.

Em conclusão, investir em mecanismos de resiliência, como a implementação de um sistema de filas, é vital para garantir a disponibilidade contínua dos dados. Sugerimos a realização de testes de carga e falha para validar a eficácia dessa implementação e identificar possíveis melhorias adicionais.
