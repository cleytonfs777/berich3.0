import json
import os
from time import sleep

# Caminho do arquivo JSON
current_dir = os.path.dirname(os.path.realpath(__file__))
db_path_main = os.path.join(current_dir, 'database.json')

# Variável de cache para evitar múltiplas leituras do arquivo
_cache_config = None

def get_one_data(chave):
    """Retorna um valor específico do JSON"""
    with open(db_path_main) as json_file:
        data = json.load(json_file)
        return data[chave]
    

def all_configs():
    """Retorna todas as configurações"""
    with open(db_path_main) as json_file:
        return json.load(json_file)

def alter_config(chave, valor):
    """Altera uma configuração e atualiza o JSON"""
    with open(db_path_main) as json_file:
        dados = json.load(json_file)
        dados[chave] = valor

    with open(db_path_main, 'w') as json_file:
        json.dump(dados, json_file, ensure_ascii=False, indent=4)


def is_enabled():
    """Verifica se o bot está ligado."""
    return get_one_data('status') == 'on'

def is_changed():
    """Verifica se houve alteração nas configurações."""
    return get_one_data('changed')

def changed_on():
    """Marca que houve mudança nas configurações."""
    return alter_config("changed", True)

def changed_off():
    """Marca que as configurações foram lidas e não há mudanças pendentes."""
    return alter_config("changed", False)

def scale_one_step():
    """
    Avança um nível no ciclo de martingale de forma segura, sem gerar erros de índice.
    Se atingir o final do ciclo, retorna True para indicar um reset.
    """
    ciclos = get_one_data("valor_por_ciclo")
    x, y = get_one_data("stage_ciclo")

    # Verifica se atingiu o último nível da matriz e precisa resetar
    if x >= len(ciclos) - 1 and y >= len(ciclos[x]) - 1:
        alter_config("stage_ciclo", [0, 0])
        return True  # Indica que o ciclo foi resetado
    
    # Se ainda há espaço na mesma linha, avança o índice y
    if y < len(ciclos[x]) - 1:
        y += 1
    else:  # Caso contrário, avança para a próxima linha e reseta y
        x += 1
        y = 0
    
    alter_config("stage_ciclo", [x, y])
    return False  # Indica que o ciclo ainda não foi resetado

def clear_all_steps(lc):
    """
    Reseta o ciclo para o nível (0,0), garantindo que os valores corretos sejam reiniciados.
    """
    alter_config("stage_ciclo", [0, 0])
    alter_config("valor_entry", get_one_data("valor_por_ciclo")[0][0])  # Reseta para o primeiro valor
    lc.pos_atual_x = 0
    lc.pos_atual_y = 0
    print("✅ Ciclo resetado para [0, 0]")


if __name__ == '__main__':
    while True:
        print("Valor Atualizado...")
        print()
        x, y = get_one_data("stage_ciclo")
        valor_por_ciclo = get_one_data("valor_por_ciclo")
        print(f"Valor atual: {valor_por_ciclo[x][y]}")
        result = scale_one_step()
        print(result)
        sleep(2)
