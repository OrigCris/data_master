# Azure Data Pipeline Demonstration

## I. Resumo
Este projeto visa demonstrar a criação de uma pipeline completa de processamento de dados utilizando diversas ferramentas da Microsoft Azure. 
<br>Inicialmente, o Azure Functions é configurado para consumir dados de uma API externa, utilizando uma Service Principal Name (SPN) para autenticação segura. Esses dados são enviados para o Event Hub, que atua como um hub central para ingestão de dados em tempo real. Posteriormente, o Databricks é utilizado para processar esses dados com Spark Streaming, configurado com a opção de trigger once para realizar a ingestão apenas quando novos dados estão disponíveis, economizando recursos computacionais. No Databricks, os dados são armazenados na camada Bronze para ingestão bruta, passam por um processo de tratamento e normalização na camada Silver e, finalmente, são agregados na camada Gold. A camada Gold é utilizada para consolidar informações importantes que podem ser visualizadas em ferramentas de Business Intelligence (BI). 
<br>É importante destacar que os dados utilizados são fictícios e servem exclusivamente para fins demonstrativos, evidenciando a funcionalidade e a integração das diferentes ferramentas.

## II. Objetivo
O objetivo principal deste projeto é ilustrar como integrar e utilizar o Azure Functions, Event Hub e Databricks para criar uma solução eficiente de processamento e análise de dados. 
<br>A partir desta demonstração, pretende-se mostrar:
<li>Como o Azure Functions pode ser utilizado para consumir dados de APIs externas de forma segura.
<li>A eficiência do Event Hub como ponto central de ingestão de dados em tempo real.
<li>O uso do Databricks para processar dados com Spark Streaming, otimizando a ingestão de dados com a opção de trigger once.
<li>O fluxo de dados desde a camada Bronze até a camada Gold, incluindo ingestão bruta, tratamento e normalização, e agregação de informações.
<li>A visualização dos dados processados através de ferramentas de BI, destacando a relevância e o valor das informações extraídas.

Esse case foi desenvolvido com o intuito de proporcionar um entendimento claro e prático de como essas ferramentas podem ser usadas em conjunto para resolver problemas reais de processamento de dados, além de demonstrar a flexibilidade e a robustez da plataforma Azure.

## III. Explicação de como foi desenvolvido
### 1. Configuração da Infraestrutura
Para iniciar o processo, executamos o [script.sh](Infraestrutura/script.sh) disponível no repositório do Git. Este script é responsável por criar todas as infraestruturas necessárias para o projeto, incluindo recursos no Azure como EventHub, Azure Functions e Databricks.

### 2. Registro do Schema no EventHub
Em seguida, configuramos o schema registry do EventHub utilizando o arquivo user_schema.avsc. Este arquivo define a estrutura dos dados que serão enviados para o EventHub e pode ser encontrado no repositório do Git. A configuração do schema registry assegura que os dados enviados estejam em conformidade com o formato esperado.

### 3. Implementação da Função no Azure Functions
Para a implementação da função no Azure Functions, utilizamos o arquivo func_user.py, disponível no repositório do Git. Este arquivo contém o código em Python necessário para processar os dados e enviá-los para o EventHub. A função é implantada no Azure Functions, onde é executada em resposta a eventos, processando e transmitindo os dados de forma eficiente.

### 4. Envio de Dados utilizando SPN
A função Python implementada no Azure Functions utiliza uma Service Principal Name (SPN) para autenticação segura e envio dos dados ao EventHub. A SPN garante que a comunicação entre os serviços seja segura e confiável.

### 5. Integração com Databricks
No Databricks, utilizamos outra SPN para autenticação e busca dos dados enviados para o EventHub. Este processo é realizado utilizando o Spark Streaming, que consome os dados do EventHub em tempo real.

### 6. Arquitetura Medallion no Databricks
A arquitetura Medallion é implementada no Databricks para organizar e processar os dados em camadas, visando melhorar a qualidade e a acessibilidade dos dados. Este processo é dividido em três camadas principais:

#### Camada Bronze
Utilizando o Spark Streaming, os dados brutos são consumidos do EventHub e armazenados na camada Bronze. Esta camada contém os dados em seu formato original, conforme recebidos do EventHub.

#### Camada Silver
Em seguida, os dados são processados em lote (batch) utilizando Spark. Durante este processo, realizamos a normalização e limpeza dos dados. Os dados tratados são armazenados na camada Silver, que apresenta um formato mais estruturado e pronto para análises.

#### Camada Gold
Finalmente, os dados são transformados e agregados na camada Gold. Esta camada contém dados altamente estruturados e otimizados para análise de negócios e geração de relatórios. A camada Gold oferece a melhor qualidade de dados, pronta para consumo por ferramentas de BI e análises avançadas.
