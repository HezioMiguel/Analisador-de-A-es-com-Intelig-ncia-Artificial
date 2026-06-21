import json
import yfinance as yf
import math
import requests
import pandas as pd
import streamlit as st

# --- BANCO DE DADOS ---
ARQUIVO_DB = "acoes_db.json"

#  testa se o arquivo existe, ou cria uma lista vazia.
try:
    with open(ARQUIVO_DB, "r") as arquivo:
        lista_acoes = json.load(arquivo)
except FileNotFoundError:
    lista_acoes = []

# --- FUNÇÕES  ---
def analisar_graham(ticker_escolhido):
    acao = yf.Ticker(ticker_escolhido)
    ficha = acao.info

    # Dica: usar 'ç' deu erro 
    preco_atual = ficha.get('currentPrice', 0)
    lpa = ficha.get('trailingEps')
    vpa = ficha.get('bookValue')

    if lpa is None or vpa is None or lpa <= 0 or vpa <= 0:
        return preco_atual, "Essa empresa deu prejuizo, tem patrimonio negativo ou não é um Ticker da Ação."

    numero_graham = math.sqrt(22.5 * lpa * vpa)
    numero_graham_arredondado = round(numero_graham, 2)

    return preco_atual, numero_graham_arredondado

def gerar_analise_ia(ticker, preco_atual, preco_justo):
    prompt_para_ia = f"""
    Atue como um analista fundamentalista sênior especializado na metodologia de Benjamin Graham.
    
    Analise a ação {ticker}, que possui os seguintes indicadores calculados hoje:
    - Preço Atual de Tela: R$ {preco_atual}
    - Número de Graham (Preço Justo/Teto): R$ {preco_justo}
    
    Responda de forma direta: Essa ação possui margem de segurança e está descontada em relação ao seu valor intrínseco? Justifique a sua resposta em no máximo 2 parágrafos.
    """
    
    OLLAMA_URL = "http://localhost:11434/api/generate"
    pacote = {
        "model": "gpt-oss", # esse modelo é meio pesado
        "prompt": prompt_para_ia,
        "stream": False
    }

    try: 
        resposta = requests.post(OLLAMA_URL, json=pacote)
        if resposta.status_code == 200:
            dados = resposta.json()
            return dados.get("response", "Erro ao extrair o texto.")
        else:
            return f"Erro no servidor. Codigo:{resposta.status_code}"
    except requests.exceptions.ConnectionError:
        return "Erro de conexao. Verifique se o OLLAMA esta rodando no terminal"


# --- INTERFACE VISUAL (STREAMLIT) ---

st.title(" Analisador de Ações com Inteligência Artificial")
st.write("Metodologia de Benjamin Graham")

# Caixa de texto para você digitar a ação (O .upper() garante que fique em maiúsculo)
with st.form(key="form_analise"):
    ticker_da_vez = st.text_input("Digite o Ticker da Ação (Ex: VALE3.SA, NIKE34.SA, VIVA3.SA):").upper()
    botao_analisar = st.form_submit_button("Analisar Ação")
    


if botao_analisar:
    if ticker_da_vez: 
        with st.spinner(f"Baixando dados de {ticker_da_vez} e calculando..."):
        
            # ... TODO O SEU CÓDIGO CONTINUA EXATAMENTE IGUAL DAQUI PARA BAIXO ...
            preco, graham = analisar_graham(ticker_da_vez)
        
            if isinstance(graham, float): 
                with st.spinner("Enviando para o Ollama pensar..."):
                    veredito_ia = gerar_analise_ia(ticker_da_vez, preco, graham)
            
                nova_acao = {
                    "Ticker": ticker_da_vez,
                    "Preco Atual": preco,
                    "Preco Justo (Graham)": graham,
                    "Veredito": veredito_ia
                }
                lista_acoes.append(nova_acao)
            
                with open(ARQUIVO_DB, "w") as arquivo:
                    json.dump(lista_acoes, arquivo, indent=4)
                
                st.success("Análise Salva com Sucesso!")
                st.info(veredito_ia)
            else:
                st.error(f"Análise ignorada: {graham}")
    else:
        st.warning("Por favor, digite um Ticker antes de clicar em Analisar.")

# --- A TABELA DO PANDAS E ATUALIZAÇÃO ---
st.divider() 
st.subheader(" Histórico de Análises")

# --- BOTÃO DE ATUALIZAR ---
if st.button("Atualizar Cotações Salvas"):
    if len(lista_acoes) > 0:
        with st.spinner("Buscando preços atualizados na bolsa... Isso pode levar alguns segundos."):
            
            for item in lista_acoes:
                ticker_salvo = item["Ticker"]
                

                novo_preco, novo_graham = analisar_graham(ticker_salvo)
                
                # Atualiza os valores
                if isinstance(novo_graham, float):
                    item["Preco Atual"] = novo_preco
                    item["Preco Justo (Graham)"] = novo_graham
                    # Nota: Não estamos pedindo para a IA ler de novo para economizar tempo, 
                    # estamos apenas atualizando a matemática e o preço de tela.
            
            # Salva a lista inteira atualizada de volta no arquivo JSON acoes_db.json
            with open(ARQUIVO_DB, "w") as arquivo:
                json.dump(lista_acoes, arquivo, indent=4)
                
            st.success("Preços atualizados com sucesso!")
            st.rerun() # Comando mágico do Streamlit que recarrega a página automaticamente!
    else:
        st.warning("Seu banco de dados está vazio. Adicione ações primeiro.")

# ---TABELA ---
if len(lista_acoes) > 0:
    tabela = pd.DataFrame(lista_acoes)
    st.dataframe(tabela, use_container_width=True)
else:
    st.write("Nenhuma ação no banco de dados ainda.")
