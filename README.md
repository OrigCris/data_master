# Azure Data Pipeline Demonstration

## I. Resumo
Este projeto visa demonstrar a criação de uma pipeline completa de processamento de dados utilizando diversas ferramentas da Microsoft Azure. Inicialmente, o **Azure Functions** é configurado para consumir dados de uma API externa, utilizando uma **Service Principal Name (SPN)** para autenticação segura. Esses dados são enviados para o **Event Hub**, que atua como um hub central para ingestão de dados em tempo real. Posteriormente, o **Databricks** é utilizado para processar esses dados com **Spark Streaming**, configurado com a opção de **trigger once** para realizar a ingestão apenas quando novos dados estão disponíveis, economizando recursos computacionais.

No Databricks, os dados são armazenados na camada Bronze para ingestão bruta, passam por um processo de tratamento e normalização na camada Silver e, finalmente, são agregados na camada Gold. A camada Gold é utilizada para consolidar informações importantes que podem ser visualizadas em ferramentas de Business Intelligence (BI).

Além disso, o projeto demonstra a otimização de recursos ao utilizar o Schema Registry.<br>
Foram configuradas duas instâncias no EventHub:
- Instância A (com Schema Registry): Utiliza o Schema Registry para validar e padronizar os dados antes de serem enviados.
- Instância B (sem Schema Registry): Não utiliza o Schema Registry, permitindo comparar a eficiência e os recursos consumidos em ambas as instâncias.

É importante destacar que os dados utilizados são fictícios e servem exclusivamente para fins demonstrativos, evidenciando a funcionalidade e a integração das diferentes ferramentas.

## II. Objetivo
O objetivo principal deste projeto é ilustrar como integrar e utilizar o Azure Functions, Event Hub e Databricks para criar uma solução eficiente de processamento e análise de dados. 
<br>A partir desta demonstração, pretende-se mostrar:
  - Como o Azure Functions pode ser utilizado para consumir dados de APIs externas de forma segura.
  - A eficiência do Event Hub como ponto central de ingestão de dados em tempo real.
  - O uso do Databricks para processar dados com Spark Streaming, otimizando a ingestão de dados com a opção de trigger once.
  - O fluxo de dados desde a camada Bronze até a camada Gold, incluindo ingestão bruta, tratamento e normalização, e agregação de informações.
  - A comparação entre o uso e não uso do Schema Registry no EventHub, evidenciando como ele otimiza o recurso.

Esse case foi desenvolvido com o intuito de proporcionar um entendimento claro e prático de como essas ferramentas podem ser usadas em conjunto para resolver problemas reais de processamento de dados, além de demonstrar a flexibilidade e a robustez da plataforma Azure.

## III. Explicação de como foi desenvolvido
### 1. Configuração da Infraestrutura
Para iniciar o processo, executamos o [script.sh](Infraestrutura/script.sh) disponível no repositório do Git. Este script é responsável por criar todas as infraestruturas necessárias para o projeto, incluindo recursos no Azure como EventHub, Azure Functions e Databricks.

### 2. Registro do Schema no EventHub
Em seguida, configuramos o schema registry do EventHub utilizando o arquivo [user_schema.avsc](Infraestrutura/EventHub/user_schema.avsc). Este arquivo define a estrutura dos dados que serão enviados para o EventHub e pode ser encontrado no repositório do Git. A configuração do schema registry assegura que os dados enviados estejam em conformidade com o formato esperado.

### 3. Implementação da Função no Azure Functions
Para a implementação da função no Azure Functions, utilizamos o arquivo [func_user.py](Infraestrutura/Functions/func_user.py), disponível no repositório do Git. Este arquivo contém o código em Python necessário para processar os dados e enviá-los para o EventHub. A função é implantada no Azure Functions, onde é executada em resposta a eventos, processando e transmitindo os dados de forma eficiente.

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

## IV. Passo a passo para a implementação

### 1. Criando todos os recursos
Passos para executar o script:
  1. Faça o upload do arquivo para o Cloud Shell.
  2. Conceda permissão de execução ao script com o comando: `chmod +x script.sh`
  3. Execute o script, passando o caminho onde ele se encontra: `./script.sh`

<p align="center">
  <img src="Imagens\cloud_shell_import.png" alt="Import script.sh" width="500px">
  <br>
  <em>Figura 1: Importar o arquivo SCRIPT.SH para criar recursos e permissões </em>
</p>

Feito isso já podemos ver os recursos criados dentro do *resource group*

### 2. Criar o Schema no EventHub
Passos para a criação do *schema* dentro do *schema group*:
  1. Dentro do recurso do Event Hub, procure por Schema Registry.
  2. No Schema Registry, você verá um Schema Group criado. Clique para acessá-lo.
  3. Clique na opção `+ Schema` depois coloque o nome e importe o arquivo `user_schema.avsc`.
  4. Após criar o schema, copie o **ID** do schema gerado. Este ID será utilizado na configuração da função no Azure Functions.

<img src="Imagens\option_schema.png" alt="Opção de criar um novo schema" width="200px"/> ---->
<img src="Imagens\create_schema.png" alt="Tela de criação de SCHEMA" width="200px"/> ---->
<img src="Imagens\schema_id.png" alt="ID do schema criado" width="200px"/>

### 3. Configuração da Variável de Ambiente no Azure Functions
Para que a função no Azure Functions possa acessar o schema criado, é necessário configurar o ID do schema como uma variável de ambiente.<br>
Passos para configurar a variável de ambiente:
  1. Acesse o recurso do Azure Functions no portal do Azure.
  2. Vá para Configurações e clique em **Variáveis de ambiente**.
  3. Adicione uma nova variável com o nome SCHEMA_USER_ID e cole o ID do schema copiado anteriormente como valor.
  4. Salve as alterações.

<img src="Imagens\environment_function_app.png" alt="Opção de variávei de ambiente" width="200px"/>

### 4. Realizando o deploy da Função no Azure Functions
Passos para a implementação:
  1. Faça o deploy do arquivo func_user.py para o Azure Functions (<a href="https://learn.microsoft.com/en-us/azure/azure-functions/create-first-function-vs-code-python">Como fazer o deploy</a>).
  2. Certifique-se de que a variável de ambiente SCHEMA_USER_ID está configurada corretamente, conforme descrito acima.
  3. Acompanhe a execução da função para verificar se os dados estão sendo processados e enviados corretamente para o EventHub.

### 5. Preparando o ambiente do Databricks
  1. Primeiro precisamos de uma `scope`, que será necessário para podemos realizar nossos acessos (<a href="https://learn.microsoft.com/en-us/azure/databricks/security/secrets/">Como criar o secret scope</a>).
  2. Já com o `scope` criado podemos criar o nosso cluster, o arquivo json irá apoiar nisso, [func_user.py](Databricks/cluster_json). (Não esqueça de substituir os dados da SPN)
  3. Adicione a biblioteca maven para conectar ao EventHub: em **"bibliotecas"**, clique em **"instalar novo"**, selecione `maven` e procure por `com.microsoft.azure:azure-eventhubs-spark_2.12:2.3.22`
  4. Importe os notebooks disponíveis no GIT e coloque-os para rodar.

Obs: Em todos os passos e configurações, não esquecer de trocar os nomes das variáveis de acordo com a sua configuração.

## V. Monitoramento com Azure Monitor
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
  4. Total de Bytes de Entrada: Comparação entre tópicos com e sem Schema Registry.

#### Function App:
  1. Número de Execuções: Quantas vezes as funções foram executadas.
  2. Memory Working Set: Uso de memória das funções.
    
#### Storage Account:
  1. Transações Realizadas: Total de transações.

#### Databricks:
  1. Memória Disponível: Quantidade de memória disponível nos clusters.
  2. Média de Uso de CPU (%): Média do uso de CPU nos clusters.

<p align="center">
  <img src="Imagens\monitoramento_1.jpeg" alt="Opção de criar um novo schema" width="900px"/> 
  <img src="Imagens\monitoramento_2.jpeg" alt="Opção de criar um novo schema" width="900px"/> 
  <img src="Imagens\monitoramento_3.jpeg" alt="Opção de criar um novo schema" width="900px"/>
</p>

A implementação do monitoramento com o Azure Monitor é essencial para assegurar a operação adequada de todos os recursos da solução. Isso permite que a equipe de desenvolvimento se concentre em melhorar continuamente a aplicação, sabendo que qualquer problema será rapidamente detectado e resolvido.

O dashboard oferece informações cruciais para identificar possíveis problemas na ingestão de dados ou gargalos na pipeline. Para resolver esses problemas (troubleshooting), basta clicar no recurso à direita do painel, o que permite uma análise detalhada das métricas e logs correspondentes.

Para as métricas do Spark, é fundamental acessar também as métricas e logs do cluster. Isso ajuda a identificar a causa raiz de qualquer problema potencial.

## VI. Melhorias e Considerações Finais

Para melhorar a resiliência de nossa Function App, propomos a implementação de um sistema de filas. Em um ambiente de computação em nuvem, a disponibilidade e a resiliência são fatores cruciais para garantir que os dados sejam processados de maneira eficiente e confiável. As intermitências do EventHub podem representar um desafio significativo, pois podem resultar na perda de dados valiosos. Portanto, a solução proposta é a implementação de uma fila (Queue), como o Azure Queue Storage ou o Azure Service Bus Queue, para armazenar temporariamente os dados recebidos do EventHub durante essas intermitências.

A implementação de uma fila oferece vários benefícios. Primeiro, ela melhora a resiliência do sistema, garantindo que nenhum dado seja perdido, mesmo quando o EventHub enfrenta intermitências. Os dados armazenados na fila podem ser processados pela Function App assim que a conexão com o EventHub for restabelecida. Além disso, essa abordagem permite que o sistema lide de forma mais eficiente com picos de carga, escalando conforme necessário para garantir a continuidade do processamento de dados.

Essa abordagem não apenas melhora a resiliência e a escalabilidade do sistema, mas também oferece uma camada adicional de redundância, fundamental para sistemas críticos.

Em conclusão, investir em mecanismos de resiliência, como a implementação de um sistema de filas, é vital para garantir a disponibilidade contínua dos dados. Sugerimos a realização de testes de carga e falha para validar a eficácia dessa implementação e identificar possíveis melhorias adicionais.
