import re
import subprocess
import numpy as np
import multiprocessing
import os
import shutil
import time

def modificar_conf(center_x, center_y, center_z, arquivo_conf):
    with open(arquivo_conf, 'r') as file:
        conteudo = file.readlines()

    for i in range(len(conteudo)):
        if 'center_x' in conteudo[i]:
            conteudo[i] = f'center_x = {center_x}\n'
        elif 'center_y' in conteudo[i]:
            conteudo[i] = f'center_y = {center_y}\n'
        elif 'center_z' in conteudo[i]:
            conteudo[i] = f'center_z = {center_z}\n'

    with open(arquivo_conf, 'w') as file:
        file.writelines(conteudo)

    print(f"Valores de center_x={center_x}, center_y={center_y} e center_z={center_z} atualizados no arquivo {arquivo_conf}.")

def run_docking(center_x, center_y, center_z, idx):
    # Cria uma cópia única do arquivo de configuração
    arquivo_conf = f'conf2_{idx}.txt'
    shutil.copy('conf2.txt', arquivo_conf)

    # Modifica o arquivo conf copiado
    modificar_conf(center_x, center_y, center_z, arquivo_conf)

    # Executa o Vina com o arquivo de configuração único
    comando = ["start", "cmd", "/c", "vina.exe", "--config", arquivo_conf, "--log", f"relatorio_{idx}.txt", "--cpu", "2"]
    subprocess.run(comando, shell=True)
    time.sleep(1)
    # Espera até que o arquivo de log seja gerado e contenha "Writing output ... done."
    while True:
        if os.path.exists(f"relatorio_{idx}.txt"):
            with open(f"relatorio_{idx}.txt", 'r') as file:
                conteudo = file.read()
                if "Writing output ... done." in conteudo:
                    break
        time.sleep(1)  # Aguarda 1 segundo antes de verificar novamente

    # Salvar o resultado no backup
    salvar_backup(center_x, center_y, center_z, idx)

    # Após o processo, exclui o arquivo de configuração específico
    os.remove(arquivo_conf)
    os.remove(f"relatorio_{idx}.txt")
    time.sleep(1)

# Função de backup ajustada para incluir o índice
def salvar_backup(center_x, center_y, center_z, idx):
    # Verifica se o arquivo de log existe e está pronto para ser lido
    if not os.path.exists(f'relatorio_{idx}.txt'):
        print(f"O arquivo de log relatorio_{idx}.txt não foi encontrado.")
        return

    with open(f'relatorio_{idx}.txt', 'r') as file:
        linhas = file.readlines()

    resultados = [linha for linha in linhas if re.match(r'^\s*\d+\s+', linha)]

    if len(resultados) >= 2:
        energia = resultados[1].strip().split()
        energia_valor = energia[1]

        with open('backup2.txt', 'a') as file:
            file.write(f"x = {center_x}\n")
            file.write(f"y = {center_y}\tAfi= {energia_valor}\n")
            file.write(f"z = {center_z}\n")

        print(f"Backup salvo em backup.txt com sucesso para center_x={center_x}, center_y={center_y}, center_z={center_z}.")
    else:
        print(f"Não foi possível encontrar resultados suficientes em relatorio_{idx}.txt.")

if __name__ == "__main__":
    valores = np.arange(-70, 50, 10)

    tarefas = [(x, y, z, idx) for idx, (x, y, z) in enumerate([(x, y, z) for x in valores for y in valores for z in valores])]

    with multiprocessing.Pool(processes=4) as pool:
        tarefas_por_lote = min(len(tarefas), pool._processes)

        while tarefas:
            tarefas_lote = tarefas[:tarefas_por_lote]
            tarefas = tarefas[tarefas_por_lote:]
            # Executa o lote de tarefas
            resultados = [pool.apply_async(run_docking, tarefa) for tarefa in tarefas_lote]

            # Espera a conclusão de todas as tarefas do lote atual
            for resultado in resultados:
                resultado.get()  # Aguarda a conclusão de cada tarefa

            print(f"Lote de 4 tarefas concluído, iniciando próximo lote...")
