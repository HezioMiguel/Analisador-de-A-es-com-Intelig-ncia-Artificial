import json
import yfinance as yf
import math
import requests
import pandas as pd
import streamlit as st
import datetime


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

    preco_atual = ficha.get('currentPrice', 0)
    lpa = ficha.get('trailingEps')
    vpa = ficha.get('bookValue')

    if lpa is None or vpa is None or lpa <= 0 or vpa <= 0:
        # Note que adicionei um '0' a mais no return para não quebrar a lógica
        return preco_atual, "Erro de dados ou prejuízo", 0 

    numero_graham = math.sqrt(22.5 * lpa * vpa)
    numero_graham_arredondado = round(numero_graham, 2)

    hoje = datetime.date.today()
    inicio = hoje - datetime.timedelta(weeks=52) 
    
    
    historico = acao.history(start=inicio, end=hoje)
    
    if not historico.empty:
        menor_preco = round(historico['Low'].min(), 2)
    else:
        menor_preco = 0
    # ------------------------------------------

    # Agora a função retorna 3 informações!
    return preco_atual, numero_graham_arredondado, menor_preco

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

def deletar_acao(ticker_para_deletar):
    global lista_acoes
    # Filtra a lista mantendo apenas as ações que NÃO têm o ticker selecionado
    lista_acoes = [acao for acao in lista_acoes if acao["Ticker"] != ticker_para_deletar]
    
    # Salva a nova lista no arquivo JSON
    with open(ARQUIVO_DB, "w") as arquivo:
        json.dump(lista_acoes, arquivo, indent=4)

# --- INTERFACE VISUAL (STREAMLIT) ---

st.title(" Analisador de Ações com Inteligência Artificial")
st.write("Metodologia de Benjamin Graham")

# Caixa de texto para você digitar a ação (O .upper() garante que fique em maiúsculo)
with st.form(key="form_analise"):
    ticker_da_vez = st.text_input("Digite o Ticker da Ação (Ex: VALE3.SA, NIKE34.SA, VIVA3.SA):").upper()
    botao_analisa = st.form_submit_button("Analisar Ação")
    


if botao_analisa:
    if ticker_da_vez: 
        with st.spinner(f"Baixando dados de {ticker_da_vez} e calculando..."):
        
            preco, graham,minima_historica = analisar_graham(ticker_da_vez)
        
            if isinstance(graham, float): 
                with st.spinner("Enviando para o Ollama pensar..."):
                    veredito_ia = gerar_analise_ia(ticker_da_vez, preco, graham)
                
                potencial_reais = graham - preco
                
                if preco > 0:
                    potencial_porcentagem = (potencial_reais / preco) * 100
                else:
                    potencial_porcentagem = 0

                nova_acao = {
                    "Ticker": ticker_da_vez,
                    "Preco Atual": preco,
                    "Preco Justo (Graham)": graham,
                    "Potencial (R$)": round(potencial_reais, 2),
                    "Potencial (%)": round(potencial_porcentagem, 2),
                    "Fundo 57 Semanas": minima_historica,
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
                
                # 1. Agora recebemos as 3 variáveis corretamente
                novo_preco, novo_graham, nova_minima = analisar_graham(ticker_salvo)
                
                if isinstance(novo_graham, float):
                    # 2. Refazemos a matemática da porcentagem com o preço do dia
                    potencial_reais = novo_graham - novo_preco
                    potencial_porcentagem = (potencial_reais / novo_preco) * 100 if novo_preco > 0 else 0
                    
                    # 3. Atualizamos todos os dados no dicionário do item
                    item["Preco Atual"] = novo_preco
                    item["Preco Justo (Graham)"] = novo_graham
                    item["Potencial (%)"] = round(potencial_porcentagem, 2)
                    item["Fundo 57 Semanas"] = nova_minima
                    
                    # Nota: Continuamos não pedindo para a IA ler de novo para economizar tempo
            
            # Salva a lista inteira atualizada de volta no arquivo JSON
            with open(ARQUIVO_DB, "w") as arquivo:
                json.dump(lista_acoes, arquivo, indent=4)
                
            st.success("Preços, Fundos e Porcentagens atualizados com sucesso!")
            st.rerun() 
    else:
        st.warning("Seu banco de dados está vazio. Adicione ações primeiro.")



# ---TABELA ---
if len(lista_acoes) > 0:
    st.write("Ações salvas no seu banco de dados:")
    
    for item in lista_acoes:
        col1, col2, col3, col4, col5 ,col6= st.columns([1.5, 1.5, 1.5, 1.5, 1.5,1])
        
        with col1:
            st.markdown(f"**{item['Ticker']}**")
        with col2:
            st.write(f"Atual: R$ {item['Preco Atual']:.2f}")
        with col3:
            st.write(f"Justo: R$ {item['Preco Justo (Graham)']:.2f}")
        with col4:
            # Puxamos a porcentagem calculada (com formatação)
            potencial = item.get('Potencial (%)', 0) 
            
            # Um truque visual bacana: se for positivo, mostramos uma setinha pra cima
            if potencial > 0:
                st.success(f"📈 +{potencial}%")
            else:
                st.error(f"📉 {potencial}%")
        with col5:
            # Mostrando o menor preço do período para você ficar de olho
            fundo = item.get('Fundo 57 Semanas', 0)
            st.write(f"Fundo: R$ {fundo:.2f}")        
        with col6:
            botao_deletar = st.button("Deletar", key=f"del_{item['Ticker']}", help="Excluir")
            if botao_deletar:
                deletar_acao(item['Ticker'])
                st.rerun()
                
    st.divider()
    # Se ainda quiser ver o DataFrame completo formatado abaixo:
    tabela = pd.DataFrame(lista_acoes)
    st.dataframe(tabela, use_container_width=True)
else:
    st.write("Nenhuma ação no banco de dados ainda.")
