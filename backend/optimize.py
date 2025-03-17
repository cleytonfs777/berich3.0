import itertools
import pandas as pd
from backtest import backtest_estrategia


def otimizar_estrategia(api_conn, par, timeframe, estrategia_nome, parametros, metodo, tempo):
    """ Otimiza os parâmetros da estratégia testando todas as combinações possíveis """
    
    estrategias = {
        "medias_rsi": "estrategia_medias_rsi",
        "price_action": "estrategia_price_action",
        "fibonacci": "estrategia_fibonacci",
        "probabilistica": "estrategia_probabilistica",
        "smc": "estrategia_smc"
    }
    
    if estrategia_nome not in estrategias:
        raise ValueError("Estratégia inválida. Escolha: medias_rsi, price_action, fibonacci ou probabilistica.")
    
    # Gerar todas as combinações possíveis de parâmetros
    chaves = parametros.keys()
    combinacoes = list(itertools.product(*parametros.values()))
    
    melhor_config = None
    melhor_taxa_acerto = 0
    
    for combinacao in combinacoes:
        config_atual = dict(zip(chaves, combinacao))
        
        print(f"Testando configuração: {config_atual}")
        resultado = backtest_estrategia(api_conn, par, timeframe, estrategias[estrategia_nome], metodo, tempo)
        
        if resultado and resultado['taxa_acerto'] > melhor_taxa_acerto:
            melhor_taxa_acerto = resultado['taxa_acerto']
            melhor_config = config_atual
    
    print("Melhor configuração encontrada:")
    print(f"Parâmetros: {melhor_config}")
    print(f"Taxa de acerto: {melhor_taxa_acerto}%")
    
    return melhor_config, melhor_taxa_acerto
