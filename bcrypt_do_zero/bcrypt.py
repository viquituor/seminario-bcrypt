"""
bcrypt implementado do zero (sem bibliotecas de criptografia).

Formato do hash:  $2b$CC$SSSSSSSSSSSSSSSSSSSSSSHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH
                   |   |  |                     |
                   |   |  |                     +-- 31 chars: hash (23 bytes)
                   |   |  +-- 22 chars: sal (16 bytes)
                   |   +-- custo (2^CC iteracoes)
                   +-- versao do algoritmo
"""

import hmac
import os

from .blowfish import cifrar_bloco, expansao_custosa

VERSAO = "2b"
TAMANHO_SAL = 16
TAMANHO_MAX_SENHA = 72          # limite do bcrypt (bytes, contando o \0 final)
TEXTO_FIXO = b"OrpheanBeholderScryDoubt"   # 24 bytes = 3 blocos de 64 bits

# Alfabeto base64 do bcrypt (DIFERENTE do base64 padrao!)
ALFABETO = "./ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


# ---------------------------------------------------------------- base64 ----
def codificar_base64(dados):
    """Base64 do bcrypt, sem preenchimento com '='."""
    saida = []
    i = 0
    while i < len(dados):
        c1 = dados[i]
        i += 1
        saida.append(ALFABETO[c1 >> 2])
        c1 = (c1 & 0x03) << 4
        if i >= len(dados):
            saida.append(ALFABETO[c1])
            break
        c2 = dados[i]
        i += 1
        c1 |= c2 >> 4
        saida.append(ALFABETO[c1])
        c1 = (c2 & 0x0F) << 2
        if i >= len(dados):
            saida.append(ALFABETO[c1])
            break
        c2 = dados[i]
        i += 1
        c1 |= c2 >> 6
        saida.append(ALFABETO[c1])
        saida.append(ALFABETO[c2 & 0x3F])
    return "".join(saida)


def decodificar_base64(texto, tamanho):
    """Inverso de codificar_base64; devolve `tamanho` bytes."""
    valores = [ALFABETO.index(c) for c in texto]
    saida = bytearray()
    i = 0
    while len(saida) < tamanho and i + 1 < len(valores):
        saida.append(((valores[i] << 2) | (valores[i + 1] >> 4)) & 0xFF)
        if len(saida) >= tamanho or i + 2 >= len(valores):
            break
        saida.append(((valores[i + 1] << 4) | (valores[i + 2] >> 2)) & 0xFF)
        if len(saida) >= tamanho or i + 3 >= len(valores):
            break
        saida.append(((valores[i + 2] << 6) | valores[i + 3]) & 0xFF)
        i += 4
    return bytes(saida[:tamanho])


# ------------------------------------------------------------ algoritmo -----
def preparar_senha(senha):
    """
    Passo 1: senha -> bytes UTF-8 + terminador \\0, truncada em 72 bytes.
    (Por isso senhas com mais de 72 bytes tem o excedente ignorado!)
    """
    if isinstance(senha, str):
        senha = senha.encode("utf-8")
    if b"\x00" in senha:
        raise ValueError("A senha nao pode conter byte nulo")
    return (senha + b"\x00")[:TAMANHO_MAX_SENHA]


def calcular_hash_bruto(senha, custo, sal, detalhar=False):
    """Executa o bcrypt e devolve os 23 bytes do hash."""
    if not 4 <= custo <= 31:
        raise ValueError("O custo deve estar entre 4 e 31")
    if len(sal) != TAMANHO_SAL:
        raise ValueError("O sal deve ter 16 bytes")

    chave = preparar_senha(senha)
    if detalhar:
        print(f"   [1] Chave = senha + \\0, max 72 bytes -> {len(chave)} bytes")

    # Passo 2: Expansao de chave custosa (Eksblowfish)
    estado = expansao_custosa(custo, sal, chave, detalhar)

    # Passo 3: cifra 64 vezes o texto fixo "OrpheanBeholderScryDoubt"
    blocos = [[int.from_bytes(TEXTO_FIXO[i:i + 4], "big"),
               int.from_bytes(TEXTO_FIXO[i + 4:i + 8], "big")]
              for i in range(0, 24, 8)]
    for _ in range(64):
        for bloco in blocos:
            bloco[0], bloco[1] = cifrar_bloco(estado, bloco[0], bloco[1])
    if detalhar:
        print("   [3] Texto 'OrpheanBeholderScryDoubt' cifrado 64x em modo ECB")

    # Passo 4: concatena os 3 blocos (24 bytes) e descarta o ultimo byte -> 23
    saida = b"".join(e.to_bytes(4, "big") + d.to_bytes(4, "big") for e, d in blocos)
    return saida[:23]


def gerar_hash(senha, custo=12, sal=None, detalhar=False):
    """Gera o hash no formato $2b$CC$<sal><hash>."""
    if sal is None:
        sal = os.urandom(TAMANHO_SAL)      # sal aleatorio unico por senha
    if detalhar:
        print(f"Custo={custo} -> 2^{custo} = {2 ** custo} iteracoes | sal={sal.hex()}")
    bruto = calcular_hash_bruto(senha, custo, sal, detalhar)
    resultado = f"${VERSAO}${custo:02d}${codificar_base64(sal)}{codificar_base64(bruto)}"
    if detalhar:
        print(f"   [4] Hash final montado: {resultado}")
    return resultado


def verificar_senha(senha, hash_armazenado):
    """Recalcula o hash usando custo e sal do hash armazenado e compara."""
    try:
        _, versao, custo, resto = hash_armazenado.split("$")
        if versao not in ("2a", "2b", "2y") or len(resto) != 53:
            return False
        sal = decodificar_base64(resto[:22], TAMANHO_SAL)
        novo = calcular_hash_bruto(senha, int(custo), sal)
    except (ValueError, IndexError):
        return False
    esperado = decodificar_base64(resto[22:], 23)
    # Comparacao em tempo constante (evita ataque de temporizacao)
    return hmac.compare_digest(novo, esperado)
