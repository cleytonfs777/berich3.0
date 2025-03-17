import os
from dotenv import load_dotenv
import sys
current_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(current_dir)
from iqoptionapi.stable_api import IQ_Option
from backend.backtest import executar_backtest
from backend.handler import get_one_data

load_dotenv()


# Inicialização da API
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

# Teste da Função de Estratécia Probabilistica

executar_backtest(API, "EURUSD-OTC", 1, "probabilistica", "current", "6h")