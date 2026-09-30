"""
Cifra de bloco Blowfish (Bruce Schneier, 1993) com a "expansao de chave
custosa" (Eksblowfish) usada pelo bcrypt.

- Bloco de 64 bits (duas metades de 32 bits: E e D = esquerda e direita)
- Rede de Feistel com 16 rodadas
- Vetor P (18 subchaves) + 4 caixas S (substituicao) dependentes da chave
"""

from .constantes import P_INICIAL, S_INICIAL

MASCARA = 0xFFFFFFFF


class EstadoBlowfish:
    """Guarda o vetor P e as caixas S (o 'estado' da cifra)."""

    def __init__(self):
        # Copia dos digitos de PI: o ponto de partida de todo Blowfish
        self.P = list(P_INICIAL)
        self.S = [list(caixa) for caixa in S_INICIAL]


def funcao_f(estado, x):
    """
    Funcao F do Blowfish: mistura 32 bits usando as 4 caixas S.
        F(x) = ((S0[a] + S1[b]) XOR S2[c]) + S3[d]   (somas mod 2^32)
    onde a, b, c, d sao os 4 bytes de x (do mais ao menos significativo).
    """
    S = estado.S
    a = (x >> 24) & 0xFF
    b = (x >> 16) & 0xFF
    c = (x >> 8) & 0xFF
    d = x & 0xFF
    return ((((S[0][a] + S[1][b]) & MASCARA) ^ S[2][c]) + S[3][d]) & MASCARA


def cifrar_bloco(estado, esq, dir_):
    """Cifra um bloco de 64 bits (esq, dir_) e devolve o novo par."""
    P = estado.P
    for i in range(16):                 # 16 rodadas de Feistel
        esq ^= P[i]                     # 1) XOR com a subchave da rodada
        dir_ ^= funcao_f(estado, esq)   # 2) mistura via F e XOR na outra metade
        esq, dir_ = dir_, esq           # 3) troca as metades
    esq, dir_ = dir_, esq               # desfaz a ultima troca
    dir_ ^= P[16]                       # "branqueamento" final
    esq ^= P[17]
    return esq, dir_


def _proxima_palavra(dados, posicao):
    """
    Le 4 bytes de `dados` (big-endian) a partir de `posicao`, dando a volta
    no inicio quando acaba (a chave e repetida ciclicamente).
    Retorna (palavra, nova_posicao).
    """
    palavra = 0
    n = len(dados)
    for _ in range(4):
        palavra = (palavra << 8) | dados[posicao]
        posicao = (posicao + 1) % n
    return palavra, posicao


def expandir_chave(estado, chave, sal=None):
    """
    ExpandKey(estado, sal, chave) do paper do bcrypt.

    1) P[i] ^= palavras da chave (repetida ciclicamente)
    2) Cifra um bloco zerado e usa o resultado para substituir P[0], P[1];
       cifra o resultado para P[2], P[3]... e depois para todas as caixas S.
    3) Se houver `sal` (16 bytes = 4 palavras), ele e somado por XOR ao bloco
       ANTES de cada cifragem, alternando as palavras do sal.
       Sem sal (sal=None) equivale ao "sal zero" -> Blowfish padrao.
    """
    # Passo 1: mistura a chave no vetor P
    posicao = 0
    for i in range(18):
        palavra, posicao = _proxima_palavra(chave, posicao)
        estado.P[i] ^= palavra

    palavras_sal = None
    if sal is not None:
        palavras_sal = [int.from_bytes(sal[i:i + 4], "big") for i in range(0, 16, 4)]

    esq = dir_ = 0
    indice_sal = 0

    def proximo_bloco(esq, dir_, indice_sal):
        if palavras_sal is not None:
            esq ^= palavras_sal[indice_sal % 4]
            dir_ ^= palavras_sal[(indice_sal + 1) % 4]
            indice_sal += 2
        esq, dir_ = cifrar_bloco(estado, esq, dir_)
        return esq, dir_, indice_sal

    # Passo 2: regenera P (9 blocos = 18 palavras)
    for i in range(0, 18, 2):
        esq, dir_, indice_sal = proximo_bloco(esq, dir_, indice_sal)
        estado.P[i], estado.P[i + 1] = esq, dir_

    # Passo 3: regenera as 4 caixas S (4 * 128 blocos)
    for caixa in estado.S:
        for i in range(0, 256, 2):
            esq, dir_, indice_sal = proximo_bloco(esq, dir_, indice_sal)
            caixa[i], caixa[i + 1] = esq, dir_


def expansao_custosa(custo, sal, chave, detalhar=False):
    """
    EksBlowfishSetup(custo, sal, chave): o coracao do bcrypt.

        estado <- PI
        estado <- ExpandKey(estado, sal, chave)
        repita 2^custo vezes:
            estado <- ExpandKey(estado, 0, chave)
            estado <- ExpandKey(estado, 0, sal)

    Cada +1 no custo DOBRA o tempo de processamento.
    """
    estado = EstadoBlowfish()
    if detalhar:
        print("   [2a] Estado inicial carregado com os digitos de PI (P e 4 caixas S)")
    expandir_chave(estado, chave, sal)
    if detalhar:
        print("   [2b] ExpandKey(sal, senha) feito: o SAL entrou no estado")
        print(f"   [2c] Iniciando {2 ** custo} iteracoes (2^{custo}) de ExpandKey(senha) + ExpandKey(sal)")
    for _ in range(2 ** custo):
        expandir_chave(estado, chave)
        expandir_chave(estado, sal)
    return estado
