import os
import sys
current_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
print("Current dir: ", current_dir)
sys.path.append(current_dir)
from backend.handler import get_one_data


def ajuste_entrada(banca, ciclos=6, fator=2.5):
    # Recupera o valor de ciclos e fator_martingale
    ciclos = int(get_one_data('qtd_ciclos'))
    print(f"Quantidade de ciclos: {ciclos}")
    fator = float(get_one_data('fator_martingale'))
    print(f"Fator de martingale: {fator}")

    # Calcular a soma da série geométrica
    soma_serie = sum([fator ** i for i in range(ciclos)])
    
    # Calcular a primeira parte da banca
    primeira_parte = round(banca / soma_serie, 2)
    
    # Inicializar a lista de partes da banca
    partes_banca = [primeira_parte]
    
    # Calcular as partes restantes da banca
    for i in range(1, ciclos):
        partes_banca.append(round(partes_banca[-1] * fator, 2))
    
    # Verificar se a soma das partes é igual à banca
    # Se não for, ajustar a última parte
    soma_partes = sum(partes_banca)
    if soma_partes != banca:
        partes_banca[-1] += round(banca - soma_partes, 2)

    print(f"Partes da banca: {partes_banca}")
    # Retornar a lista de partes da banca
    return partes_banca


if __name__ == "__main__":
    ajuste_entrada(100)