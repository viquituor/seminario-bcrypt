"""
Demonstracao interativa do bcrypt implementado do zero.

Uso:  python main.py
"""

import getpass
import time

from bcrypt_do_zero import gerar_hash, verificar_senha

CUSTO_DEMO = 6   # rapido em Python puro; em producao use 12 ou mais


def opcao_gerar():
    senha = getpass.getpass("Senha: ")
    custo = int(input(f"Custo [{CUSTO_DEMO}]: ") or CUSTO_DEMO)
    print("\nExecutando os passos do bcrypt:")
    inicio = time.perf_counter()
    resultado = gerar_hash(senha, custo, detalhar=True)
    print(f"\nHash: {resultado}")
    print(f"Tempo: {time.perf_counter() - inicio:.2f} s")


def opcao_verificar():
    senha = getpass.getpass("Senha para testar: ")
    armazenado = input("Hash armazenado: ").strip()
    if verificar_senha(senha, armazenado):
        print("Senha CORRETA")
    else:
        print("Senha INCORRETA")


def opcao_custos():
    print("Cada +1 no custo dobra o tempo (Python puro, senha 'teste'):")
    for custo in range(4, 9):
        inicio = time.perf_counter()
        gerar_hash("teste", custo)
        print(f"  custo {custo:2d} -> {2 ** custo:4d} iteracoes -> {time.perf_counter() - inicio:6.2f} s")


def opcao_sal():
    print("Mesma senha, dois sais diferentes:")
    print(" ", gerar_hash("senha123", 4))
    print(" ", gerar_hash("senha123", 4))


MENU = {"1": ("Gerar hash (passo a passo)", opcao_gerar),
        "2": ("Verificar senha", opcao_verificar),
        "3": ("Comparar tempo por custo", opcao_custos),
        "4": ("Mostrar efeito do sal", opcao_sal)}

if __name__ == "__main__":
    while True:
        print("\n=== bcrypt do zero ===")
        for chave, (nome, _) in MENU.items():
            print(f" {chave}) {nome}")
        print(" 0) Sair")
        escolha = input("> ").strip()
        if escolha == "0":
            break
        if escolha in MENU:
            MENU[escolha][1]()
