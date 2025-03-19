from backend.utils import BackTestMoney
import random


banca_simulada = 95

simula_back = BackTestMoney(5, 2.5, banca_simulada)

partes = simula_back.calibra_entrada_backtest()

print(f"Essas são as partes do ciclo: {partes}")
print()

def resultado_aleatorio(qtd=5):

    grupo = []

    for _ in range(qtd):
        grupo.append(random.choice(["win", "loss"]))

    return grupo

selecion = resultado_aleatorio(10)

for slc in selecion:
    simula_back.processa_game(slc)