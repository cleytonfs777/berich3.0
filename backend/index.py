import os
import sys
from datetime import datetime
from time import sleep, time
import pandas as pd
from dotenv import load_dotenv
from handler import *
# Adiciona o diretório raiz ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from iqoptionapi.stable_api import IQ_Option
from strategies import estrategia_bollinger_rsi, estrategia_fibonacci, estrategia_media_rsi, estrategia_price_action, estrategia_probabilistica, estrategia_sequencia_cores_otimizada, estrategia_smc, estrategia_teste, operation_start
from utils import *
from colorama import Fore, init
from messeger import enviar_mensagem_telegram
from threading import Thread

# Inicializa o colorama
init(autoreset=True)  # O 'autoreset=True' fará com que cada print volte à cor padr

load_dotenv()


def mainbot():

    def enviar_mensagem_em_thread(*mensagens):
        t = Thread(target=enviar_mensagem_telegram, args=mensagens)
        t.start()


    def get_data(par, timeframe, periods = 200):

        velas = API.get_candles(par, timeframe * 60, periods, time())

        df = pd.DataFrame(velas)
        df.rename(columns={"max": "high", "min": "low"}, inplace=True)

        return df

    def banca():
        return round(API.get_balance(), 2)
 
    # ESTRATEGIAS INICIO
    def pair_open(API, par, tipo):

        paridades = API.get_all_open_time()
        binario = []
        digital = []

        if tipo == 'binaria':
            for paridade in paridades['turbo']:
                if paridades['turbo'][paridade]['open'] == True:
                    binario.append(paridade)
            if par in binario:
                return True
            else:
                return False
        elif tipo == 'digital':
            for paridade in paridades['digital']:
                if paridades['digital'][paridade]['open'] == True:
                    digital.append(paridade)
            if par in digital:
                return True
            else:
                return False

        
    ##########################################################################################

    API = IQ_Option(os.getenv('EMAIL_IQPTION'), os.getenv('PASSWORD_IQPTION'))

    def conectar_api():
        while True:
            try:
                print("Conectando à IQ Option...")
                API.connect()
                if API.check_connect():
                    print("✅ Conectado com sucesso!")
                    break
                else:
                    print("🔴 Erro ao conectar. Tentando novamente em 5 segundos...")
                    time.sleep(5)
            except Exception as e:
                print(f"⚠️ Erro na conexão: {e}. Tentando novamente em 5 segundos...")
                time.sleep(5)

    conectar_api()

    # 🔥 CORREÇÃO: Carregar configurações antes de usar
    configs = all_configs()  
    API.change_balance(configs['tipo_conta'])  # PRACTICE / REAL
    
    banca_value = banca()
    value_stop_gain = round(banca_value * configs['porcentagem_stop_win'], 2)
    value_stop_loss = round(banca_value * configs['porcentagem_stop_loss'], 2) * -1

    alter_config('banca', banca_value)
    changed_on()
    alter_config('valor_entry', get_one_data('valor_por_ciclo')[0][0])
    alter_config('luc_prej', 0)
    alter_config('firstis', True)

    # Relaciona todas as estratégias criadas
    estrategias = {
        "bbands_rsi": estrategia_bollinger_rsi,
        "media_rsi": estrategia_media_rsi,
        "price_action": estrategia_price_action,
        "fibonacci": estrategia_fibonacci,
        "probabilistica": estrategia_probabilistica,
        "teste": estrategia_teste,
        "sequencia_cores_otimizada": estrategia_sequencia_cores_otimizada,
    }

    INITIAL_LOOP = True
    par = configs['pares_favoritos'][0]
    timeframe = normalize_timeframe(configs['timeframe'])
    if configs['estrategia_principal'] == 'media_simples':
        periods = 14
        tyme_avg = 'SMA'
        dfg = get_data(par, timeframe, 500)
        dec = 7 - len(str(dfg.iloc[-1]['close']).split('.')[0])
    print(Fore.YELLOW + f"""
            __  __  ____  _____  _  _  ____  __  __  ____  _  _  ____  ____  ____  ____  ____  ____  ____
           \ \        / _ \  | \ \     / ____|  ___|   __ )  ____|   _ \ _ _|  ___| |   |  __ )   _ \__ __| 
            \ \  \   / |   | |  \ \   /  __|  \___ \   __ \  __|    |   |  |  |     |   |  __ \  |   |  |   
             \ \  \ /  |   | |   \ \ /   |          |  |   | |      __ <   |  |     ___ |  |   | |   |  |   
              \_/\_/  \___/ _____|\_/   _____|_____/  ____/ _____| _| \_\___|\____|_|  _| ____/ \___/  _|   
                                                                                                

                #########################################################################################
                #   BANCA : {banca_value}  #   GAIN : {value_stop_gain}   #   LOSS: {value_stop_loss}   #
                #                                                                                       #
                #########################################################################################
    """)
    ## Inicial reset. Deve ser resetado valor_entry e stage_ciclo
    calibrar_entrada(API)
    alter_config("valor_entry",get_one_data("valor_por_ciclo")[0][0])
    alter_config("stage_ciclo",[0, 0])

    inital_config = True
    lista_ll = get_one_data('valor_por_ciclo')
    itr = IteradorPosicoes(lista_ll)
    direction = None

    while True:

        # Verifica se o bot está habilitado
        if is_enabled():

            if is_changed():
                print("\nAtualiza configurações...")
                changed_off()
                configs = all_configs()

                if not pair_open(API, configs['pares_favoritos'][0], configs['typecoin']):
                    print(f'{Fore.RED}Paridade {configs["pares_favoritos"][0]} não está aberta...{Fore.RESET}')
                    enviar_mensagem_em_thread(f"⚠️ Paridade {configs['pares_favoritos'][0]} não está aberta... ⚠️")
                    alter_config("status","off")
                    continue
                changed_off()
                print("Fim de leitura de paridades e desligando mundanças...")

            # Verifica se houve alteração nas configurações

            if configs['estrategia_principal'] in estrategias:
                estrategia = estrategias[configs['estrategia_principal']]

                print(f'\rRastreando oportunidades...para Estratégia: {configs["estrategia_principal"]}   {datetime.now().strftime("%H:%M:%S")}', end='')
                
                if permited_time("general_permissions"):
                    print(f"Tempo correto para analise...")
                    direction = estrategia(API, configs['pares_favoritos'][0], configs['timeframe'])
            else:
                print(f'{Fore.RED}Estratégia {configs["estrategia_principal"]} não encontrada...{Fore.RESET}')


            if direction:
                enviar_mensagem_em_thread(f"Realizada entrada no par {configs['pares_favoritos'][0]} com direção {direction}",
                                            f"Banca atual: {banca()} | Lucro/Prejuízo: {get_one_data('luc_prej')} | Valor de entrada: {get_one_data('valor_entry')}")
                print("Realizando operacao - ", datetime.now().strftime("%H:%M:%S"))
                operation_start(API, get_one_data('pares_favoritos')[0], direction,
                                normalize_timeframe(configs['timeframe']), get_one_data('tipo_entrada'),
                                get_one_data('typecoin'), itr)
                
                if get_one_data('luc_prej') >= value_stop_gain:
                    enviar_mensagem_em_thread(f"🤑 Você bateu o Stop Gain de {value_stop_gain} e o bot foi desligado 🤑")
                    alter_config("status", "off")
                if get_one_data('luc_prej') <= value_stop_loss:
                    enviar_mensagem_em_thread(f"😭 Você bateu o Stop Loss de {value_stop_loss} e o bot foi desligado. Seu prejuízo é: {get_one_data('luc_prej')*-1} 😭")
                    alter_config("status", "off")
                changed_on()

                direction = None

            
            print(f'\rRastreado Opotunidades...para Estratégia: {configs['estrategia_principal']}   {datetime.now().strftime("%H:%M:%S")}', end='')    

        else:
            print(f'\rApenas monitorando...   {datetime.now().strftime("%H:%M:%S")}', end='')
            # Zera o lucro/prejuízo
            alter_config('luc_prej', 0)
            # Aqui o bot apenas monitora
            if is_changed():
                print("\nAtualiza configurações...")
                changed_off()
                configs = all_configs()

        # Aguarda 1 segundo para a próxima iteração
        sleep(1)


if __name__ == '__main__':
    mainbot()
