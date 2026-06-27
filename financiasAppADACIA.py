import json
import yfinance as yf
import math
import requests
import pandas as pd
import streamlit as st
import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"

# --- BANCO DE DADOS ---
ARQUIVO_DB = "acoes_db.json"

#  testa se o arquivo existe, ou cria uma lista vazia.
try:
    with open(ARQUIVO_DB, "r") as arquivo:
        lista_acoes = json.load(arquivo)
except FileNotFoundError:
    lista_acoes = []

# --- FUNÇÕES  ---
def analisar_graham(ticker_escolhido:str)->tuple:
    acao = yf.Ticker(ticker_escolhido)
    ficha = acao.info

    preco_atual = ficha.get('currentPrice', 0)
    lpa = ficha.get('trailingEps')
    vpa = ficha.get('bookValue')

    if lpa is None or vpa is None or lpa <= 0 or vpa <= 0:
        return preco_atual, "Erro de dados ou prejuízo", 0 

    numero_graham = math.sqrt(22.5 * lpa * vpa)
    numero_graham_arredondado = round(numero_graham, 2)

    indicadores = {
            "P/L": round(ficha.get('trailingPE') or 0, 2),
            "P/VP": round(ficha.get('priceToBook') or 0, 2),
            "Liquidez Corrente": round(ficha.get('currentRatio') or 0, 2),
            "Dividend Yield (%)": round((ficha.get('dividendYield') or 0) * 100, 2),
            "Fluxo de Caixa Livre": ficha.get('freeCashflow', 0),
            "Divida/Patrimonio": round(ficha.get('debtToEquity') or 0, 2)}
    

    hoje = datetime.date.today()
    inicio = hoje - datetime.timedelta(weeks=52) 
    
    
    historico = acao.history(start=inicio, end=hoje)
    
    if not historico.empty:
        menor_preco = round(historico['Low'].min(), 2)
    else:
        menor_preco = 0
    # ------------------------------------------

    return preco_atual, numero_graham_arredondado, menor_preco,indicadores

def gerar_analise_ia(ticker:str, preco_atual:float, preco_justo:float, ind:dict)-> str:
    prompt_para_ia = f"""
    Atue como um analista fundamentalista senior especializado em Value Investing.
    Analise a acao {ticker} com base nos seguintes dados de hoje:
    
    - Preco Atual: R$ {preco_atual}
    - Numero de Graham (Teto): R$ {preco_justo}
    - P/L: {ind.get('P/L')}
    - P/VP: {ind.get('P/VP')}
    - Liquidez Corrente: {ind.get('Liquidez Corrente')}
    - Dividend Yield: {ind.get('Dividend Yield (%)')}%
    - Fluxo de Caixa Livre (FCF): {ind.get('Fluxo de Caixa Livre')}
    - Divida/Patrimonio: {ind.get('Divida/Patrimonio')}
    
    Sua tarefa: Avalie esses indicadores e classifique a acao em UMA das 3 categorias abaixo (ou informe categoricamente se ela for uma armadilha de valor e nao se encaixar em nenhuma):
    
    1. Acao Defensiva: P/L abaixo de 15, P/VP abaixo de 1.5, Liquidez > 2.0 e paga dividendos.
    2. Acao Net-Net / Deep Value: Altamente descontada, P/VP muito baixo, mas com Fluxo de Caixa Livre positivo e liquidez garantindo a sobrevivencia (simulando filtro Piotroski).
    3. Acao de Qualidade (Screener): Destaque absoluto para Fluxo de Caixa forte e baixo endividamento (Divida/Patrimonio < 100), mesmo que o preco nao esteja em desconto profundo.
    
    Responda diretamente: Em qual dos 3 perfis essa acao melhor se encaixa e por que? Existe margem de seguranca real? Limite sua analise a 2 paragrafos diretos.
    """
    pacote = {
        "model": "gpt-oss", 
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

def deletar_acao(ticker: str) -> None:
    try:
        with open(ARQUIVO_DB, "r") as arquivo:
            dados_atuais = json.load(arquivo)
            
        dados_filtrados = [acao for acao in dados_atuais if acao["Ticker"] != ticker]
        
        with open(ARQUIVO_DB, "w") as arquivo:
            json.dump(dados_filtrados, arquivo, indent=4)
    except FileNotFoundError:
        pass

# --- INTERFACE VISUAL (STREAMLIT) ---

st.title(" Analisador de Ações com Inteligência Artificial")
st.write("usando a metodologia de Benjamin Graham para explicar qual tipo de investimento a ação se enquadra \n\n 1. Ação Defensiva (Investidor Clássico): Filtra ativos com múltiplos controlados (P/L < 15, P/VP < 1.5), alta liquidez corrente (> 2.0, garantindo solvência de curto prazo) e distribuição regular de proventos através do Dividend Yield.\n\n 2. Ação Net-Net (Barganhas Profundas): Identifica empresas negociadas com descontos patrimoniais severos (P/VP muito baixo), mas que mantém o Fluxo de Caixa Livre positivo para mitigar o risco de falência iminente. \n\n 3. Métricas de Qualidade Extras: Avalia a relação Dívida/Patrimônio para garantir que a alavancagem financeira não comprometa a estabilidade estrutural da empresa no longo prazo \n\n Se a empresa apresentar prejuízo contábil ou patrimônio líquido negativo, o cálculo é abortado, refletindo a regra número um do investimento defensivo: a preservação do capital. \n\n deve-se colocar 'sa.' apos o nome ticker da ação .   ")

with st.form(key="form_analise"):
    ticker_da_vez = st.text_input("Digite o Ticker da Ação (Ex: VALE3.SA, NIKE34.SA, VIVA3.SA):").upper()
    botao_analisa = st.form_submit_button("Analisar Ação")
    


if botao_analisa:
    if ticker_da_vez:
        if ticker_da_vez in [acao["Ticker"] for acao in lista_acoes]: 
            st.warning(f"O ativo {ticker_da_vez} já está na sua base de dados. Utilize o botão 'Sincronizar Cotações' para atualizar os valores.")
        else:
            with st.spinner(f"Baixando dados de {ticker_da_vez} e calculando..."):
                
                preco, graham,minima_historica,indicadores = analisar_graham(ticker_da_vez)
            
                if isinstance(graham, float): 
                    with st.spinner("Enviando para o Ollama pensar..."):
                        veredito_ia = gerar_analise_ia(ticker_da_vez, preco, graham,indicadores)
                    
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
                        "Fundo 52 Semanas": minima_historica,
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
                
                novo_preco, novo_graham, nova_minima, _ = analisar_graham(ticker_salvo)
                
                if isinstance(novo_graham, float):
                    potencial_reais = novo_graham - novo_preco
                    potencial_porcentagem = (potencial_reais / novo_preco) * 100 if novo_preco > 0 else 0
                    
                    item["Preco Atual"] = novo_preco
                    item["Preco Justo (Graham)"] = novo_graham
                    item["Potencial (%)"] = round(potencial_porcentagem, 2)
                    item["Fundo 52 Semanas"] = nova_minima
                                
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
            potencial = item.get('Potencial (%)', 0) 
            
            if potencial > 0:
                st.success(f"📈 +{potencial}%")
            else:
                st.error(f"📉 {potencial}%")
        with col5:
            fundo = item.get('Fundo 52 Semanas', 0)
            st.write(f"Fundo: R$ {fundo:.2f}")        
        with col6:
            botao_deletar = st.button("Deletar", key=f"del_{item['Ticker']}", help="Excluir")
            if botao_deletar:
                deletar_acao(item['Ticker'])
                st.rerun()
                
    st.divider()
    tabela = pd.DataFrame(lista_acoes)
    st.dataframe(tabela, use_container_width=True)
else:
    st.write("Nenhuma ação no banco de dados ainda.")
