# Analisador de Acoes com inteligencia artificial

Este projeto e uma aplicacao web desenvolvida em Python que automatiza a analise de ativos financeiros utilizando a metodologia de Benjamin Graham. O sistema realiza a coleta de dados de mercado em tempo real, calcula o valor intrinseco da acao (Numero de Graham) e utiliza um modelo de Inteligencia Artificial local para gerar um parecer tecnico sobre a margem de seguranca do ativo.

## Arquitetura do Sistema

O sistema foi construido focando na integracao de APIs e no processamento local de dados para garantir a privacidade do usuario:

* Coleta de Dados: yfinance (Yahoo Finance API)
* Interface Web: Streamlit
* Processamento de Dados: Pandas
* ferramenta de código aberto que permite baixar e executar Modelos de Linguagem (LLMs): Ollama e oss-gpt
* Persistencia de Dados: Arquivo JSON local para historico de analises

## Pre-requisitos

Para executar este projeto na sua maquina, voce precisara de:

1. Python 3.8 ou superior instalado.
2. Ollama instalado e rodando em background.
3. Um modelo de linguagem baixado no Ollama (o codigo padrao utiliza o `gpt-oss`, mas pode ser alterado para `llama3` ou outro de sua preferencia).

## Instalacao e Execucao

1. Clone este repositorio para a sua maquina local:

2. Navegue ate a pasta do projeto:


3. Instale as dependencias necessarias:
pip install -r requirements.txt

4. Certifique-se de que o servidor do Ollama esta ativo no seu terminal. Se necessario, inicie o modelo:
ollama run gpt-oss

5. Inicie a aplicacao web do Streamlit:
python -m streamlit run financiasAppADACIA.py

## Como Utilizar

* Na interface principal, digite o Ticker do ativo que deseja analisar (ex: VALE3.SA para acoes brasileiras).
* O sistema fara o download dos dados de balanco e calculara o preco teto.
* Caso a empresa possua indicadores positivos, os dados sao enviados para a IA gerar o relatorio.
* O relatorio e os calculos sao salvos automaticamente no banco de dados e exibidos na tabela historica.
* Utilize o botao de atualizacao para recalcular os precos atuais de todas as acoes salvas no banco.

## Pitch
* https://youtu.be/J4oP_12tBBY

## Aviso Legal

Este software tem fins estritamente educacionais e de pesquisa em desenvolvimento de sistemas e integracao de IA. As analises geradas nao constituem recomendacao de compra ou venda de ativos financeiros.

## Licenca

Este projeto esta sob a licenca MIT.
