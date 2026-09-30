"""
Constantes iniciais do Blowfish.

O Blowfish inicializa o vetor P (18 palavras de 32 bits) e as 4 caixas S
(4 x 256 palavras de 32 bits) com os digitos hexadecimais da parte
fracionaria do numero PI. Ou seja: "nada na manga" (nothing up my sleeve),
ninguem pode acusar o projetista de ter escondido uma backdoor nas tabelas.

Em vez de colar ~4 KB de numeros magicos no codigo, calculamos os digitos
de PI aqui mesmo com aritmetica de inteiros grandes (formula de Machin):

    PI = 16 * arctan(1/5) - 4 * arctan(1/239)
"""

QTD_P = 18            # 18 palavras no vetor P
QTD_S = 4 * 256       # 4 caixas S de 256 palavras
BITS_NECESSARIOS = (QTD_P + QTD_S) * 32


def _arctan_inverso(x, escala):
    """Calcula arctan(1/x) * escala usando a serie de Taylor com inteiros."""
    termo = escala // x
    soma = termo
    x2 = x * x
    n = 3
    sinal = -1
    while termo:
        termo //= x2
        soma += sinal * (termo // n)
        sinal = -sinal
        n += 2
    return soma


def calcular_pi_fracionario(qtd_bits):
    """Retorna a parte fracionaria de PI como inteiro com `qtd_bits` bits."""
    guarda = 64                                  # bits extras contra erro de arredondamento
    escala = 1 << (qtd_bits + guarda)
    pi = 16 * _arctan_inverso(5, escala) - 4 * _arctan_inverso(239, escala)
    fracao = pi - (3 * escala)                   # tira a parte inteira (3)
    return fracao >> guarda


def gerar_tabelas_iniciais():
    """Devolve (P, S): P com 18 palavras e S com 4 listas de 256 palavras."""
    fracao = calcular_pi_fracionario(BITS_NECESSARIOS)
    palavras = []
    for i in range(QTD_P + QTD_S):
        deslocamento = BITS_NECESSARIOS - 32 * (i + 1)
        palavras.append((fracao >> deslocamento) & 0xFFFFFFFF)
    P = palavras[:QTD_P]
    S = [palavras[QTD_P + 256 * k: QTD_P + 256 * (k + 1)] for k in range(4)]
    return P, S


# Calculado uma unica vez, quando o modulo e importado.
P_INICIAL, S_INICIAL = gerar_tabelas_iniciais()
