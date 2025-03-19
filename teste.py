# import os
# import sys
# from iqoptionapi.stable_api import IQ_Option
# import time
# from dotenv import load_dotenv, find_dotenv
# import pandas as pd

# from backend.handler import get_one_data

# _ = load_dotenv(find_dotenv())

# def conectar_IQOption():
#     API = IQ_Option(os.getenv('EMAIL_IQPTION'),os.getenv('PASSWORD_IQPTION'))
#     API.connect()

#     API.change_balance(get_one_data('tipo_conta'))  # PRACTICE / REAL

#     if API.check_connect():
#         print(' Conectado com sucesso!')
#     else:
#         print(' Erro ao conectar')
#         input('\n\n Aperte enter para sair')
#         sys.exit()

#     return API

# api_conn: IQ_Option = conectar_IQOption()

# # PEGA OS CANDLES DO EURUSD E TRANSFORMA EM UM DATAFRAME
# df_candles = api_conn.get_candles('EURUSD', 60, 1000, time.time())

# df_candles = pd.DataFrame(df_candles, columns=['id', 'from', 'at', 'to', 'open', 'close', 'min', 'max', 'volume'])

# # Criar a coluna data/hora
# df_candles['data'] = pd.to_datetime(df_candles['from'], unit='s').dt.tz_localize('UTC').dt.tz_convert('America/Sao_Paulo').dt.strftime('%Y-%m-%d %H:%M')

# print(df_candles.head())   # DataFrame com os candles

# # ANALISA OS CANDLES
# resultados = []  # Lista para armazenar os resultados

# for _, row in df_candles.iterrows():
#     open_price = row['open']
#     close_price = row['close']
    
#     if close_price > open_price:
#         resultados.append('call')
#     elif close_price < open_price:
#         resultados.append('sell')
#     else:
#         resultados.append(None)

# print(resultados)

from dotenv import load_dotenv, find_dotenv
# from backend.handler import get_one_data
# from backend.utils import IteradorPosicoes, ajuste_entrada

_ = load_dotenv(find_dotenv())

class BackTestMoney:
    def __init__(self, qtd_ciclos, fator, banca_value):
        """
        Inicializa a classe com uma lista de elementos e um índice de controle.
        :param elementos: Lista de elementos a serem percorridos ciclicamente.
        """

        self.index = 0  # Começa do primeiro elemento
        self.qtd_ciclos = qtd_ciclos
        self.fator = fator
        self.banca_value = banca_value
        self.elementos = self.calibra_entrada_backtest()
        self.lucro_total = 0
        self.quebra_bancas = 0

    def proximo(self):
        """
        Retorna o próximo elemento da lista. Quando chega ao final, retorna ao primeiro.
        """
        elemento = self.elementos[self.index]
        self.index = (self.index + 1) % len(self.elementos)  # Loop cíclico
        return elemento

    def reset(self):
        """
        Reinicia a lista para começar novamente do primeiro elemento.
        """
        self.index = 0
        print("Iteração reiniciada para o primeiro elemento.")


    def entrada_min(self):
        # Recupera o valor de ciclos e fator_martingale
        initial = 1
        total_banca = initial
        self.qtd_ciclos = int(self.qtd_ciclos)
        for i in range(1,self.qtd_ciclos):
            total_banca += round(initial * self.fator,2)
            initial = round(initial * self.fator,2)

        return round(total_banca, 2)

    def ajuste_entrada_backtest(self):

        # Calcular a soma da série geométrica
        soma_serie = sum([self.fator ** i for i in range(self.qtd_ciclos)])
        
        # Calcular a primeira parte da banca
        primeira_parte = round(self.banca_value / soma_serie, 2)
        
        # Inicializar a lista de partes da banca
        partes_banca = [primeira_parte]
        
        # Calcular as partes restantes da banca
        for i in range(1, self.qtd_ciclos):
            partes_banca.append(round(partes_banca[-1] * self.fator, 2))
        
        # Verificar se a soma das partes é igual à banca
        # Se não for, ajustar a última parte
        soma_partes = sum(partes_banca)
        if soma_partes != self.banca_value:
            partes_banca[-1] += round(self.banca_value - soma_partes, 2)

        print(f"Partes da banca: {partes_banca}")
        # Retornar a lista de partes da banca
        return partes_banca

    def calibra_entrada_backtest(self):

        # Executa a função banca e salva na variável "banca_value"
        print(f"Banca: {self.banca_value}")

        ciclos = self.ajuste_entrada_backtest()

        min_ent = self.entrada_min()

        if int(ciclos[0]) < 1:

            return f"Para que seja possivel realizar {ciclos} ciclos é necessario ter no minimo banca de U$ {min_ent}"
        
        # lista_fim = agrupar_pares(ciclos)


        return ciclos
    

banca_simulada = 165

simula_back = BackTestMoney(4, 2.5, banca_simulada)

partes = simula_back.calibra_entrada_backtest()

print(f"Essas são as partes do ciclo: {partes}")
print()

for i in range(10):

    if i == 7:
        simula_back.reset()
        print()

    print("*" * 10)
    print(f"Rodando o {i+1}º ciclo")
    print(f"Entrada: {simula_back.proximo()}")
    print("*" * 10)

