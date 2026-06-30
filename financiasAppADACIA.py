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
        return preco_atual, "Erro de dados ou prejuízo", 0, {}

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

    1. Preço Atual
    É o preço de mercado da ação na bolsa de valores neste exato momento (o preço de tela). Ele oscila continuamente durante o horário de pregão com base na oferta e na procura pelo papel.

    2. Número de Graham (Teto)
    É o limite máximo que a ação deveria custar segundo a fórmula de avaliação matemática de Benjamin Graham. Ele representa o valor intrínseco teórico do ativo. Se o Preço Atual estiver abaixo do Número de Graham, significa que a ação está sendo negociada com desconto, gerando uma Margem de Segurança para o comprador.

    3. P/L (Preço / Lucro)
    Mede a relação entre o preço atual da ação e o lucro líquido acumulado por ela nos últimos 12 meses. Tecnicamente, ele indica quantos anos o mercado aceita esperar para recuperar o capital investido se o lucro da empresa permanecer constante. Na regra clássica de Graham, um P/L abaixo de 15 indica um preço moderado e seguro.

    4. P/VP (Preço / Valor Patrimonial)
    Compara o preço de mercado da empresa com o seu valor patrimonial líquido real (bens, imóveis, caixas e ativos menos as obrigações). Um P/VP de 1,0 significa que a empresa está sendo vendida na bolsa exatamente pelo preço que seu patrimônio vale no balanço. Graham recomendava que o investidor defensivo buscasse um P/VP abaixo de 1,5 para evitar pagar caro por expectativas exageradas de crescimento.

    5. Liquidez Corrente
    Indica a capacidade da empresa de honrar suas dívidas e obrigações de curto prazo (que vencem nos próximos 12 meses) usando os seus recursos de curto prazo (dinheiro em caixa, estoques e recebíveis). O cálculo é feito dividindo o Ativo Circulante pelo Passivo Circulante. Um índice superior a 2,0 significa que a empresa possui pelo menos o dobro de recursos líquidos do que precisa para cobrir seus compromissos imediatos, oferecendo excelente blindagem contra crises de liquidez.

    6. Dividend Yield (%)
    Representa o retorno financeiro gerado pelos dividendos e juros sobre capital próprio (JCP) pagos pela empresa nos últimos 12 meses, proporcional ao preço atual da ação. É o indicador que mede o rendimento passivo direto enviado para o bolso do investidor. Graham valorizava empresas com histórico perene de pagamento de dividendos como prova de lucros reais.

    7. Fluxo de Caixa Livre (FCF)
    É o volume de dinheiro limpo e real que sobra no caixa da empresa após ela pagar todas as despesas operacionais e realizar os investimentos necessários para manter ou expandir suas instalações (o chamado CapEx). Diferente do Lucro Líquido, que é um dado puramente contábil, o Fluxo de Caixa Livre mostra a geração de dinheiro tangível. Um FCF robusto e positivo assegura que a empresa tem capacidade de pagar dividendos, recomprar ações ou amortizar dívidas sem precisar recorrer a empréstimos bancários.

    8. Dívida / Patrimônio (Debt to Equity)
    Mede o nível de alavancagem financeira da empresa comparando o total de suas dívidas com o patrimônio líquido investido pelos acionistas. Ele demonstra o grau de dependência de capital de terceiros (como empréstimos e emissão de debêntures) para financiar as operações do negócio. Valores abaixo de 100% (ou 1,0) revelam que a dívida total não supera o patrimônio próprio da companhia, caracterizando uma estrutura financeira saudável e de baixo risco estrutural
        
    Sua tarefa: Avalie esses indicadores e classifique a acao em UMA das 3 categorias abaixo (ou informe caso nao se encaixar em nenhuma):
    
    1.  Acao Defensiva: P/L abaixo de 15, P/VP abaixo de 1.5, Liquidez > 2.0 e paga dividendos.
        Ação Defensiva (Investidor Clássico): Filtra ativos com múltiplos controlados (P/L < 15, P/VP < 1.5), alta liquidez corrente (> 2.0, garantindo solvência de curto prazo) e distribuição regular de proventos através do Dividend Yield.
    
    2.  Acao Net-Net / Deep Value: Altamente descontada, P/VP muito baixo, mas com Fluxo de Caixa Livre positivo e liquidez garantindo a sobrevivencia (simulando filtro Piotroski).
        Ação Net-Net (Barganhas Profundas): Identifica empresas negociadas com descontos patrimoniais severos (P/VP muito baixo), mas que mantém o Fluxo de Caixa Livre positivo para mitigar o risco de falência iminente.

    3.  Acao de Qualidade (Screener): Destaque absoluto para Fluxo de Caixa forte e baixo endividamento (Divida/Patrimonio < 100), mesmo que o preco nao esteja em desconto profundo.
        Acao de Qualidade (Screener): Avalia a relação Dívida/Patrimônio para garantir que a alavancagem financeira não comprometa a estabilidade estrutural da empresa no longo prazo



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
st.write("usando a metodologia de Benjamin Graham para explicar qual tipo de investimento a ação se enquadra \n\n 1. Ação Defensiva (Investidor Clássico): Filtra ativos com múltiplos controlados (P/L < 15, P/VP < 1.5), alta liquidez corrente (> 2.0, garantindo solvência de curto prazo) e distribuição regular de proventos através do Dividend Yield.\n\n 2. Ação Net-Net (Barganhas Profundas): Identifica empresas negociadas com descontos patrimoniais severos (P/VP muito baixo), mas que mantém o Fluxo de Caixa Livre positivo para mitigar o risco de falência iminente. \n\n 3. Acao de Qualidade (Screener): Avalia a relação Dívida/Patrimônio para garantir que a alavancagem financeira não comprometa a estabilidade estrutural da empresa no longo prazo \n\n Se a empresa apresentar prejuízo contábil ou patrimônio líquido negativo, o cálculo é abortado, refletindo a regra número um do investimento defensivo: a preservação do capital. \n\n deve-se colocar '.sa' apos o nome ticker da ação .   ")

# Caixa de texto para você digitar a ação (O .upper() garante que fique em maiúsculo)
with st.form(key="form_analise"):
    ticker_da_vez = st.text_input("Digite o Ticker da Ação (Ex: VALE3.SA, NIKE34.SA, VIVA3.SA):").upper()
    botao_analisa = st.form_submit_button("Analisar Ação")
    


if botao_analisa:
    if ticker_da_vez:
        if ticker_da_vez in [acao["Ticker"] for acao in lista_acoes]: 
            st.warning(f"O ativo {ticker_da_vez} já está na sua base de dados.")
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
