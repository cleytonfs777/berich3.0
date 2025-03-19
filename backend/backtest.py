# Converte time() para data/hora
from datetime import datetime, timedelta
import math
import sys
import time
import pandas as pd
from utils import DataFrameIterator
from handler import get_one_data
from strategies import estrategia_probabilistica
from dotenv import load_dotenv
import os
from iqoptionapi.stable_api import IQ_Option


load_dotenv()

class ManagerBacktest:
    def __init__(self, moeda, timeframe_bk, estrategia, metodo, tempo):
        self.moeda = moeda
        self.timeframe_bk = timeframe_bk
        self.estrategia = estrategia
        self.metodo = metodo
        self.tempo = tempo
        self.lucro_total = 0
        self.quebra_bancas = 0
        self.API = self.conexao_IqOption()

    def conexao_IqOption(self):
        API = IQ_Option(os.getenv('EMAIL_IQPTION'),os.getenv('PASSWORD_IQPTION'))
        API.connect()
        typeacount = get_one_data("tipo_conta")
        API.change_balance(typeacount)  # PRACTICE / REAL

        if API.check_connect():
            return API
        else:
            print('Erro ao conectar')
            sys.exit()
            return None
        
    def analisar_candles(self, df_candles):
        """
        Analisa um DataFrame contendo múltiplos candles e retorna uma lista com os resultados.
        
        Para cada candle:
        - 'call' se o fechamento for maior que a abertura (candle positivo)
        - 'sell' se o fechamento for menor que a abertura (candle negativo)
        - None se o candle for neutro (abertura igual ao fechamento)

        :param df_candles: DataFrame contendo um ou mais registros de candles.
        :return: Lista com os resultados ['call', 'sell', None, ...] para cada candle.
        """

        resultados = []  # Lista para armazenar os resultados

        for _, row in df_candles.iterrows():
            open_price = row['open']
            close_price = row['close']

            if close_price > open_price:
                resultados.append('call')  # Candle positivo (alta)
            elif close_price < open_price:
                resultados.append('sell')  # Candle negativo (baixa)
            else:
                resultados.append(None)  # Candle neutro

        return resultados

    def calcular_range_candles(self, hora_atual=None, data_hora_inicial=None, data_hora_final=None):
        """
        Calcula o número de candles, a hora do primeiro e do último candle com base no tempo especificado.
        
        :param tempo: String no formato '15m', '2h', '1d' indicando o período de análise.
        :param timeframe_bk: timeframe_bk em minutos (ex: 1 para 1m, 5 para 5m, 60 para 1h).
        :param hora_atual: Data/hora atual como string 'dd/mm/yyyy HH:MM' ou None para usar o time() atual.
        :return: Dicionário com a hora do primeiro candle, hora do último candle e número de candles.
        """
        if self.metodo == 'current':
            # Se a hora atual não for fornecida, usa o time() do sistema
            if not hora_atual:
                hora_atual = datetime.now()
            else:
                hora_atual = datetime.strptime(hora_atual, "%d/%m/%Y %H:%M")  # Converte para datetime

            # Define o tempo total em segundos
            unidade = self.tempo[-1]  # Último caractere indica a unidade (m/h/d)
            valor = int(self.tempo[:-1])  # Remove a unidade e pega o valor numérico

            if unidade == 'm':
                tempo_total = valor * 60  # Minutos para segundos
            elif unidade == 'h':
                tempo_total = valor * 3600  # Horas para segundos
            elif unidade == 'd':
                tempo_total = valor * 86400  # Dias para segundos
            else:
                raise ValueError("Unidade de tempo inválida. Use 'm' para minutos, 'h' para horas ou 'd' para dias.")

            # Calcula o número de candles (arredondado para cima)
            timeframe_segundos = self.timeframe_bk * 60  # Converte timeframe para segundos
            num_candles = math.ceil(tempo_total / timeframe_segundos)

            # Calcula o horário do primeiro candle
            primeiro_candle = hora_atual - timedelta(seconds=(num_candles - 1) * timeframe_segundos)

            print(f"Dados puros: Primeiro candle: {primeiro_candle}, Último candle: {hora_atual}, Número de candles: {num_candles}")

            # Formata os horários para exibição
            primeiro_candle_timestmap = primeiro_candle.timestamp()
            primeiro_candle_str = datetime.fromtimestamp(primeiro_candle_timestmap).strftime("%d/%m/%Y %H:%M:%S")
            ultimo_candle_timestmap = hora_atual.timestamp()
            ultimo_candle_str = hora_atual.strftime("%d/%m/%Y %H:%M:%S")

            print(f"Primeiro candle: {primeiro_candle_str}, Último candle: {ultimo_candle_str}, Número de candles: {num_candles}")

            # Retorna os valores calculados
            return [primeiro_candle_timestmap, ultimo_candle_timestmap, num_candles]
        
        elif self.metodo == 'personal':

            data_hora_inicial, data_hora_final = self.tempo.split(' - ')

            # Converte as strings de data para objetos datetime
            dt_inicial = datetime.strptime(data_hora_inicial, "%d/%m/%Y %H:%M")
            dt_final = datetime.strptime(data_hora_final, "%d/%m/%Y %H:%M")

            # Garante que a data inicial não seja maior que a final
            if dt_inicial > dt_final:
                raise ValueError("A data inicial não pode ser maior que a data final.")

            # Converte timeframe para segundos
            timeframe_segundos = self.timeframe_bk * 60

            # Calcula o número total de candles no período (arredondando para cima)
            diferenca_segundos = (dt_final - dt_inicial).total_seconds()
            num_candles = math.ceil(diferenca_segundos / timeframe_segundos)

            # Converte datas para timestamps (em segundos)
            timestamp_inicial = int(dt_inicial.timestamp())
            timestamp_final = int(dt_final.timestamp())

            # Faz um print nos dados no formato de data/hora para conferencia
            print(f"Primeiro candle: {dt_inicial}, Último candle: {dt_final}, Número de candles: {num_candles}")

            # Retorna os resultados
            return [timestamp_inicial, timestamp_final, num_candles]

    
    def get_candles_by_time(self):
        """
        Pega todos os candles necessários para a estratégia pegando 500 candles antes do primeiro até o último
        """

        pri_candle, ulti_candle, quantos = self.calcular_range_candles()
        print(f"Primeiro candle: {pri_candle}, Último candle: {ulti_candle}, Número de candles: {quantos}")

        # Adiciona um buffer para garantir que está pegando a quantidade correta de candles
        total_candles = quantos + 500

        print(f"Variaveis de Entrada: moeda: {self.moeda}, timeframe: {self.timeframe_bk}, total_candles: {total_candles}, ulti_candle: {ulti_candle}")

        all_candles_needed = self.API.get_candles(
            self.moeda, self.timeframe_bk * 60, total_candles, ulti_candle
        )

        # Garante que os dados estão ordenados corretamente
        df = pd.DataFrame(all_candles_needed)
        df = df.sort_values(by=['from'])  # Ordena por timestamp

        # Remove possíveis duplicatas
        df = df.drop_duplicates(subset=['from'])

        return df


    def convert_to_df(self):
        # Prepara as velas em um dataframe
        velas = self.get_candles_by_time()
        df = pd.DataFrame(velas)
        df.rename(columns={"max": "high", "min": "low", "open": "open", "close": "close"}, inplace=True)

        # Ajusta o fuso horário para America/Sao_Paulo e formata a data
        df['data'] = pd.to_datetime(df['from'], unit='s').dt.tz_localize('UTC').dt.tz_convert('America/Sao_Paulo').dt.strftime('%Y-%m-%d %H:%M')

        return df
    
    def backtest_main(self):
        # para o df para a estratégia escolhida
        df = self.convert_to_df()

        # Recupera quantidade de martingales pela prop get_one_data
        num_separados = get_one_data("qtd_martingale")
        num_separados = num_separados if num_separados else 1

        # Iterador de frames
        divisor_df = DataFrameIterator(df, num_separados)

        for i in range(2):

            registros, separados = divisor_df.next_batch()
            print(f"{i}ª Chamada:")
            print(registros.tail())  # Mostra os primeiros registros
            print("Registros separados:\n", separados)
            direcao_candles = self.analisar_candles(separados)
            print("Analise de direção dos separados: ", direcao_candles)

        # if self.estrategia == 'estrategia_probabilistica':
        #     result = estrategia_probabilistica(self.API, self.moeda, self.timeframe_bk, df)
            

        




def backtest_for_telegram(modedas, timeframe_bk, estrategia, metodo, tempo): #metodo: personal -> 18/03/2025 08:00 - 18/03/2025 08:05 ou current -> 6h
    retultado = f"""
    moedas: {modedas}
    timeframe_bk: {timeframe_bk}
    estrategia: {estrategia}
    metodo: {metodo}
    tempo: {tempo}
    """
    print("Exibinbdo em tela o resultado...")
    print(retultado)

    return retultado



if __name__ == '__main__':
    backtest1 = ManagerBacktest('EURUSD', 1, 'estrategia_probabilistica', 'personal', '18/03/2025 17:20 - 18/03/2025 17:35')
    backtest1.backtest_main()


    # print(f"Timestamp: {time()}")
    # print(datetime.fromtimestamp(time()))
    # data = '2021-09-01 00:00:00'
    # # tranformar para timestamp
    # print(datetime.strptime(data, '%Y-%m-%d %H:%M:%S').timestamp())