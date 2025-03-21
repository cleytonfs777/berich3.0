import os
import sys
from time import sleep, time
import pandas as pd
from dotenv import load_dotenv
from handler import *
from iqoptionapi.stable_api import IQ_Option
from utils import IteradorPosicoes, check_colors, normalize_timeframe, calibrar_entrada, myround, ListaControladora
from datetime import datetime
from messeger import enviar_mensagem_telegram
from threading import Thread
import numpy as np
from collections import defaultdict


# Nesse módulo serão descritas as principais estratégias a ser utilizadas em opções binárias

load_dotenv()


def all_entry(lc: IteradorPosicoes):
    lista = get_one_data('valor_por_ciclo')
    i = lc.proxima_posicao()
    elemento = lista[i[0]][i[1]]

    return elemento

def banca(API: IQ_Option=None):
    if not API:
        API = IQ_Option(os.getenv('EMAIL_IQPTION'),os.getenv('PASSWORD_IQPTION'))
        API.connect()
        typeacount = get_one_data("tipo_conta")
        API.change_balance(typeacount)
        if API.check_connect():
            print(' Conectado com sucesso!')
        else:
            print(' Erro ao conectar')
            input('\n\n Aperte enter para sair')
            sys.exit()
    return round(API.get_balance(), 2)

def enviar_mensagem_em_thread(*mensagens):
    t = Thread(target=enviar_mensagem_telegram, args=mensagens)
    t.start()

def paridades(type_d, API: IQ_Option=None):
    if not API:
        API = IQ_Option(os.getenv('EMAIL_IQPTION'),os.getenv('PASSWORD_IQPTION'))
        API.connect()
        typeacount = get_one_data("tipo_conta")
        API.change_balance(typeacount)  # PRACTICE / REAL

        if API.check_connect():
            print(' Conectado com sucesso!')
        else:
            print(' Erro ao conectar')
            input('\n\n Aperte enter para sair')
            sys.exit()

    par = API.get_all_open_time()
    binario = []
    digital = []

    if type_d == 'binario':

        for paridade in par['turbo']:
            if par['turbo'][paridade]['open'] == True:
                binario.append(paridade)
        return binario

    if type_d == 'digital':
        for paridade in par['digital']:
            if par['digital'][paridade]['open'] == True:
                digital.append(paridade)
        return digital

    # Sobe um ciclo

def entrega_valor(lc: IteradorPosicoes):
    print("Escalando valor...")
    i_s = list(lc.proxima_posicao())
    print(f"Posição atual: {i_s}")
    alter_config("stage_ciclo", i_s)
    coin_n = get_one_data("valor_por_ciclo")[i_s[0]][i_s[1]]
    alter_config("valor_entry", coin_n)
    # alter_config("valor_entry", coin_n)
    return get_one_data("valor_entry")

def scale(itr):
    alter_config("stage_ciclo", list(itr.proxima_posicao()))
    ind_x = get_one_data("stage_ciclo")[0]
    ind_y = get_one_data("stage_ciclo")[1]
    alter_config("valor_entry", get_one_data("valor_por_ciclo")[ind_x][ind_y])
    print()
    print(f"Valor de entrada: {get_one_data('valor_entry')}")
    print()
    
def resetar(irt):
    irt.reset()
    alter_config("valor_entry", get_one_data("valor_por_ciclo")[0][0])
    alter_config("stage_ciclo", [0, 0])
    print()
    print(f"Valor de entrada: {get_one_data('valor_entry')}")
    print()
    print(f"Posição atual: {get_one_data('stage_ciclo')}")
    print()

def operation_start(API: IQ_Option, par_n, dir_n, durt, tipo_entrada, typecoin, lc: IteradorPosicoes):
    # Cria variavel mtg com valor 1
    mtg = -1

    # Pega o valor de qtd_martingale
    qtd_martingale = get_one_data("qtd_martingale")



    # Realiza entrada na paridade Digital
    def entrada_d(ativo, valor, direcao, exp, tipo):
        """Executa a entrada e lida com falhas automaticamente."""
        try:
            if tipo == "digital":
                checkin, id = API.buy_digital_spot(ativo, valor, direcao, exp)
            else:
                checkin, id = API.buy(valor, ativo, direcao, tipo, exp)

            if not checkin:
                print(f"❌ Erro ao realizar a operação. Código de erro: {id}")
                return None
            
            print(f"✅ Entrada realizada com sucesso! ID: {id}")

            while True:
                sleep(0.1)
                status, resultado = (API.check_win_digital_v2(id) if tipo == "digital" else API.check_win_v3(id))
                if status:
                    return round(resultado, 2)
        
        except Exception as e:
            print(f"⚠️ Erro ao executar a entrada: {e}")
            return None

   
    print("---------------------- INICIO DA OPERAÇÃO -------------------")

    if typecoin == 'digital':
        print(f"Do tipo digital... - - {datetime.now().strftime('%H:%M:%S')}")

        scale(lc)
        while mtg <= qtd_martingale:
            print(f"Antes da entrada... - - {datetime.now().strftime('%H:%M:%S')}")
            ent_value = get_one_data("valor_entry")
            # Verifica se o valor de entrada é maior do que a banca
            if ent_value > banca(API):
                print("Valor de entrada maior que a banca")
                break
            result = entrada_d(par_n, ent_value, dir_n, durt, typecoin)
            print("Resultado:", result)
            if result < 0:
                mtg += 1
                tot_luc_prej = round(get_one_data("luc_prej") + result,2)
                alter_config("luc_prej", myround(tot_luc_prej))
                print(f"🔴 Operação perdida no par {par_n} com direção {dir_n} | Martingale nº {mtg}🔴", f"Banca atual: {banca(API)} | Lucro/Prejuízo: {get_one_data('luc_prej')} | Valor de entrada: {get_one_data('valor_entry')}")
                enviar_mensagem_em_thread(f"🔴 Operação perdida no par {par_n} com direção {dir_n} | Martingale nº {mtg - 1}🔴", f"Banca atual: {banca(API)} | Lucro/Prejuízo: {get_one_data('luc_prej')} | Valor de entrada: {get_one_data('valor_entry')}")
                if not mtg == qtd_martingale:
                    scale(lc)
                else:
                    break


            elif result > 0:
    #           # Reseta o ciclo
                resetar(lc)
                mtg = 0
                tot_luc_prej = round(get_one_data("luc_prej") + result,2)
                alter_config("luc_prej", myround(tot_luc_prej))
                
                print(f"🟢 Operação ganha no par {par_n} com direção {dir_n} | Martingale nº {mtg}🟢", f"Banca atual: {banca(API)} | Lucro/Prejuízo: {get_one_data('luc_prej')} | Valor de entrada: {get_one_data('valor_entry')}")
                enviar_mensagem_em_thread(f"🟢 Operação ganha no par {par_n} com direção {dir_n} | Martingale nº {mtg}🟢", f"Banca atual: {banca(API)} | Lucro/Prejuízo: {get_one_data('luc_prej')} | Valor de entrada: {get_one_data('valor_entry')}")
                auto_ciclo = get_one_data("autoscaling")
                if auto_ciclo == 'on':
                    calibrar_entrada(API)
                break
            else:
                print(f"⚪ Operação empatada no par {par_n} com direção {dir_n} | Martingale nº {mtg} ⚪", f"Banca atual: {banca(API)} | Lucro/Prejuízo: {get_one_data('luc_prej')} | Valor de entrada: {get_one_data('valor_entry')}")
                enviar_mensagem_em_thread(f"⚪ Operação empatada no par {par_n} com direção {dir_n} | Martingale nº {mtg} ⚪", f"Banca atual: {banca(API)} | Lucro/Prejuízo: {get_one_data('luc_prej')} | Valor de entrada: {get_one_data('valor_entry')}")

# FUNÇÕES AUXILIARES DIRETAS DAS ESTRATÉGIAS

def calcular_rsi(series, period=14):
    """Calcula o RSI de forma otimizada."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def obter_padroes(api_conn, par, timeframe, num_candles=500):
    """ Obtém os últimos candles e identifica padrões recorrentes """
    timeframe = normalize_timeframe(timeframe) * 60
    velas = api_conn.get_candles(par, timeframe, num_candles, time())
    df = pd.DataFrame(velas)
    df.rename(columns={"max": "high", "min": "low"}, inplace=True)
    
    df['direcao'] = np.where(df['close'] > df['open'], 'call', 'put')
    
    return df

def analisar_padroes(df, tamanho_padrao=3):
    print("Df recebido para analisar padroes: ", df)
    """ Analisa a repetição de padrões e calcula probabilidades """
    padroes = defaultdict(lambda: {'call': 0, 'put': 0})
    
    for i in range(len(df) - tamanho_padrao):
        padrao = tuple(df['direcao'].iloc[i:i+tamanho_padrao])
        proximo_movimento = df['direcao'].iloc[i+tamanho_padrao]
        padroes[padrao][proximo_movimento] += 1
    
    probabilidades = {}
    for padrao, resultados in padroes.items():
        total = resultados['call'] + resultados['put']
        prob_call = resultados['call'] / total if total > 0 else 0
        prob_put = resultados['put'] / total if total > 0 else 0
        probabilidades[padrao] = {'call': round(prob_call * 100, 2), 'put': round(prob_put * 100, 2)}
    
    return probabilidades

def detectar_order_blocks(df):
    """ Identifica Order Blocks com base em grandes movimentações """
    df['body'] = abs(df['close'] - df['open'])
    order_blocks = df[df['body'] > df['body'].rolling(10).mean() * 1.5]  
    return order_blocks

def detectar_fvg(df):
    """ Identifica Fair Value Gaps (FVG) """
    df['fvg'] = df['high'].shift(1) < df['low'].shift(-1)  
    return df[df['fvg']]

def detectar_bos(df):
    """ Detecta Break of Structure (BOS) """
    df['bos_up'] = (df['high'] > df['high'].shift(1)) & (df['close'] > df['close'].shift(1))
    df['bos_down'] = (df['low'] < df['low'].shift(1)) & (df['close'] < df['close'].shift(1))
    return df[df['bos_up'] | df['bos_down']]

# ESTRATÉGIAS A SEREM IMPLEMNTADAS

def estrategia_medias_rsi(api_conn, par, timeframe, media_curta=9, media_longa=21, rsi_periodo=14):
    """
    Estratégia de Cruzamento de Médias Móveis + RSI.
    Retorna um sinal ('call', 'put' ou None).
    """
    print(f"Analisando {par} no timeframe {timeframe}...")

    # Pega os dados das velas
    timeframe = normalize_timeframe(timeframe)
    velas = api_conn.get_candles(par, timeframe * 60, 25, time())
    
    df = pd.DataFrame(velas)
    df.rename(columns={"max": "high", "min": "low"}, inplace=True)

    # Calcula as médias móveis
    df['media_curta'] = df['close'].rolling(window=media_curta).mean()
    df['media_longa'] = df['close'].rolling(window=media_longa).mean()

    # Calcula RSI
    df['RSI'] = calcular_rsi(df['close'], rsi_periodo)

    # Identifica cruzamento das médias e confirmação do RSI
    if df.iloc[-2]['media_curta'] < df.iloc[-2]['media_longa'] and df.iloc[-1]['media_curta'] > df.iloc[-1]['media_longa']:
        if df.iloc[-1]['RSI'] < 70:  # Confirma que não está sobrecomprado
            return "call"

    elif df.iloc[-2]['media_curta'] > df.iloc[-2]['media_longa'] and df.iloc[-1]['media_curta'] < df.iloc[-1]['media_longa']:
        if df.iloc[-1]['RSI'] > 30:  # Confirma que não está sobrevendido
            return "put"

    return None  # Sem sinal de entrada


# Estratégia de Price Action com Padrões de Velas + Suporte e Resistência
def estrategia_price_action(api_conn, par, timeframe):
    print(f"Analisando {par} no timeframe {timeframe} com Price Action...")
    
    timeframe = normalize_timeframe(timeframe)
    velas = api_conn.get_candles(par, timeframe * 60, 50, time())
    df = pd.DataFrame(velas)
    df.rename(columns={"max": "high", "min": "low"}, inplace=True)
    
    # Identificar zonas de suporte e resistência
    df['suporte'] = df['low'].rolling(window=10).min()
    df['resistencia'] = df['high'].rolling(window=10).max()
    
    # Detectar padrões de velas
    df['martelo'] = (df['close'] > df['open']) & ((df['high'] - df['low']) > 2 * (df['close'] - df['open']))
    df['engolfo_alta'] = (df['close'] > df['open']) & (df['close'].shift(1) < df['open'].shift(1)) & (df['close'] > df['open'].shift(1)) & (df['open'] < df['close'].shift(1))
    df['estrela_cadente'] = (df['open'] > df['close']) & ((df['high'] - df['low']) > 2 * (df['open'] - df['close']))
    
    ultima_vela = df.iloc[-1]
    
    if ultima_vela['low'] <= ultima_vela['suporte'] and (ultima_vela['martelo'] or ultima_vela['engolfo_alta']):
        return "call"
    
    if ultima_vela['high'] >= ultima_vela['resistencia'] and (ultima_vela['estrela_cadente']):
        return "put"
    
    return None

# Estratégia de Fibonacci Retracement + Confirmação de Tendência
def estrategia_fibonacci(api_conn, par, timeframe):
    print(f"Analisando {par} no timeframe {timeframe} com Fibonacci...")
    
    timeframe = normalize_timeframe(timeframe)
    velas = api_conn.get_candles(par, timeframe * 60, 50, time())
    df = pd.DataFrame(velas)
    df.rename(columns={"max": "high", "min": "low"}, inplace=True)
    
    # Calcular níveis de Fibonacci
    max_high = df['high'].max()
    min_low = df['low'].min()
    df['fib_38'] = min_low + (max_high - min_low) * 0.382
    df['fib_50'] = min_low + (max_high - min_low) * 0.5
    df['fib_61'] = min_low + (max_high - min_low) * 0.618
    
    ultima_vela = df.iloc[-1]
    
    if ultima_vela['low'] <= ultima_vela['fib_50'] or ultima_vela['low'] <= ultima_vela['fib_61']:
        return "call"
    
    if ultima_vela['high'] >= ultima_vela['fib_50'] or ultima_vela['high'] >= ultima_vela['fib_61']:
        return "put"
    
    return None

def estrategia_probabilistica(api_conn: IQ_Option, par, timeframe, df=None, confiabilidade=60, candles_padrao=3, tempo_inicial=None): 
    """
    Estratégia baseada em padrões recorrentes de cores de candles com análise probabilística.
    """
    print(f"Analisando {par} no timeframe {timeframe} com Probabilística de Cores...")

    # Configurações ajustáveis
    periodo_analise = 500  # Quantidade de candles históricos para análise
    tamanho_minimo_corpo = 0.00015  # Tamanho mínimo do corpo do candle (ajuste conforme o ativo)

    # Verifica se há tempo inicial
    tempo_inicial = tempo_inicial if tempo_inicial else time()

    # Coleta dados históricos se `df` não for passado ou estiver vazio
    if df is None or df.empty:
        velas = api_conn.get_candles(par, timeframe * 60, periodo_analise, tempo_inicial)
        df = pd.DataFrame(velas)
        df.rename(columns={"max": "high", "min": "low", "open": "open", "close": "close"}, inplace=True)

        # Ajusta o fuso horário para America/Sao_Paulo e formata a data
        df['data'] = pd.to_datetime(df['from'], unit='s').dt.tz_localize('UTC').dt.tz_convert('America/Sao_Paulo').dt.strftime('%Y-%m-%d %H:%M')

    # Se ainda estiver vazio, retorna None
    if df.empty:
        print("Nenhum dado disponível para análise.")
        return None  

    # Criando uma cópia antes de modificar colunas para evitar o SettingWithCopyWarning
    df = df.copy()

    # Calcula direção e corpo dos candles
    df['direcao'] = np.where(df['close'] > df['open'], 'call', 'put')
    df['corpo'] = abs(df['close'] - df['open'])
    df['tamanho_relativo'] = df['corpo'] / df['corpo'].rolling(20).mean()

    # Mantém apenas as colunas necessárias e evita erro de view do Pandas
    df = df[['data', 'direcao', 'corpo', 'tamanho_relativo']].copy()

    print("Até aqui meu DataFrame: ", df)

    # Identifica padrões de cores
    padroes = defaultdict(lambda: {'call': 0, 'put': 0})

    for i in range(len(df) - candles_padrao - 1):
        # Cria chave do padrão (ex: call-call-put)
        padrao = tuple(df['direcao'].iloc[i:i + candles_padrao])
        movimento_seguinte = df['direcao'].iloc[i + candles_padrao]

        # Verifica se o candle seguinte é válido
        if df['corpo'].iloc[i + candles_padrao] >= tamanho_minimo_corpo:
            padroes[padrao][movimento_seguinte] += 1

    # Calcula probabilidades
    ultimo_padrao = tuple(df['direcao'].iloc[-candles_padrao:])

    print("Último padrão: ", ultimo_padrao)

    if ultimo_padrao not in padroes:
        print("Padrão não encontrado no histórico")
        return None  

    total_ocorrencias = sum(padroes[ultimo_padrao].values())
    if total_ocorrencias < 15:  
        print("Menos de 15 ocorrências no histórico")
        return None  

    prob_call = (padroes[ultimo_padrao]['call'] / total_ocorrencias) * 100
    prob_put = (padroes[ultimo_padrao]['put'] / total_ocorrencias) * 100

    print(f"Probabilidade CALL: {prob_call:.2f}% | Probabilidade PUT: {prob_put:.2f}%")

    # Filtros adicionais (últimos candles)
    ultimo_candle = df.iloc[-1]
    penultimo_candle = df.iloc[-2]

    print(f"Último candle: {ultimo_candle}")
    print(f"Penúltimo candle: {penultimo_candle}")

    # Verifica se o último candle atende aos critérios de tamanho antes de entrar na operação
    if ultimo_candle['corpo'] < tamanho_minimo_corpo:
        print("Último candle muito pequeno, ignorando entrada.")
        return None

    if prob_call >= confiabilidade:
        return 'call'
    
    elif prob_put >= confiabilidade:
        return 'put'
    
    return None


def estrategia_teste(api_conn, par, timeframe):
    return "call"

def estrategia_smc(api_conn, par, timeframe):
    """
    Estratégia Smart Money Concept (SMC)
    Analisa Order Blocks, Fair Value Gaps e Break of Structure (BOS) para definir zonas de entrada.
    """
    print(f"Analisando {par} no timeframe {timeframe} com SMC...")

    timeframe = normalize_timeframe(timeframe)
    velas = api_conn.get_candles(par, timeframe * 60, 50, time())
    df = pd.DataFrame(velas)
    df.rename(columns={"max": "high", "min": "low"}, inplace=True)

    ob = detectar_order_blocks(df)
    fvg = detectar_fvg(df)
    bos = detectar_bos(df)

    if not ob.empty and not fvg.empty and not bos.empty:
        ultima_vela = df.iloc[-1]
        if ultima_vela['bos_up']:
            return "call"
        elif ultima_vela['bos_down']:
            return "put"

    return None  # Nenhuma condição atendida


if __name__ == '__main__':
    API = IQ_Option(os.getenv('EMAIL_IQPTION'),os.getenv('PASSWORD_IQPTION'))
    API.connect()
    typeacount = get_one_data("tipo_conta")
    API.change_balance(typeacount)  # PRACTICE / REAL

    if API.check_connect():
        print(' Conectado com sucesso!')
    else:
        print(' Erro ao conectar')
        input('\n\n Aperte enter para sair')
        sys.exit()
    
    res_op = estrategia_probabilistica(API, 'EURUSD', 1)
    print(f"Direção da Operação: {res_op}")

    # print(time())

    # # Converte time() para data/hora
    # print(datetime.fromtimestamp(time()))
    # data = '2021-09-01 00:00:00'
    # # tranformar para timestamp
    # print(datetime.strptime(data, '%Y-%m-%d %H:%M:%S').timestamp())