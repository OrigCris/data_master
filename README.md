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
