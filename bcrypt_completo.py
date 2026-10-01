"""
=============================================================================
 bcrypt implementado do zero em Python - 100% NATIVO (sem imports)
=============================================================================

Seminario 01 - Tema 09: bcrypt
Isabela Sousa & Paulo Victor Almeida

NENHUMA biblioteca externa ou modulo padrao (como `os`, `hmac`, `hashlib`,
`getpass` ou `time`) e importado! Tudo foi implementado manualmente:
  - Digitos de PI (que inicializam o Blowfish) calculados no proprio codigo,
    com inteiros grandes e a formula de Machin (nada de tabelas coladas).
  - Cifra de bloco Blowfish (rede de Feistel, 16 rodadas).
  - Expansao de chave custosa (Eksblowfish) - o "coracao" do bcrypt.
  - Base64 proprio do bcrypt (alfabeto diferente do base64 padrao).
  - Gerador pseudoaleatorio nativo (SplitMix64) no lugar de `os.urandom`.
  - Comparacao em tempo constante no lugar de `hmac.compare_digest`.
  - Cronometro nativo (contador de cifragens Blowfish) no lugar de `time`.

Passo a passo implementado:
  1. Senha -> bytes UTF-8 + terminador \\0, truncada em 72 bytes
  2. Estado Blowfish <- digitos hexadecimais de PI (vetor P e caixas S)
  3. ExpandKey(sal, senha): sal e senha entram no estado
  4. Repetir 2^custo vezes: ExpandKey(senha) e ExpandKey(sal)
  5. Cifrar 64 vezes o texto "OrpheanBeholderScryDoubt" (3 blocos de 64 bits)
  6. Montar o hash: $2b$ + custo + base64(sal) + base64(saida)

Como rodar:
    python bcrypt_completo.py
=============================================================================
"""

# -----------------------------------------------------------------------
# CRONOMETRO NATIVO (SUBSTITUINDO `time`)
# -----------------------------------------------------------------------

_contador_operacoes = 0


def _contar_operacao(n=1):
    """Contador global de operacoes nativas (cifragens de bloco Blowfish)"""
    global _contador_operacoes
    _contador_operacoes += n


class CronometroNativo:
    """
    Mede o ESFORCO de execucao sem usar a biblioteca `time`: conta quantas
    cifragens de bloco Blowfish foram feitas. Como o bcrypt e justamente
    uma "conta de esforco", essa medida e ate mais honesta que segundos:
    ela nao depende da velocidade do computador.
    """

    def __init__(self):
        self._inicio = _contador_operacoes

    def operacoes(self):
        """Quantidade de cifragens de bloco desde que o cronometro foi criado"""
        return _contador_operacoes - self._inicio


# -----------------------------------------------------------------------
# GERADOR NATIVO DE NUMEROS PSEUDOALEATORIOS (SUBSTITUINDO `os.urandom`)
# -----------------------------------------------------------------------

MASCARA_64 = 0xFFFFFFFFFFFFFFFF


class GeradorAleatorioNativo:
    """
    PRNG SplitMix64 com semente tirada de entropia do ambiente (enderecos de
    memoria id()). ATENCAO: serve para a demonstracao; em producao se usa o
    gerador do sistema operacional (os.urandom / secrets), que e um CSPRNG.
    """

    def __init__(self):
        s1 = id(object()) ^ id([]) ^ id({})
        s2 = hash((s1, id(lambda: 0), id(self)))
        self._estado = (s1 ^ (s2 << 32) ^ 0x9E3779B97F4A7C15) & MASCARA_64
        if self._estado == 0:
            self._estado = 0x853C49E65D806132
        for _ in range(16):                # descarta os primeiros valores
            self.proximo_u64()

    def proximo_u64(self):
        """Gera um inteiro de 64 bits (SplitMix64)"""
        self._estado = (self._estado + 0x9E3779B97F4A7C15) & MASCARA_64
        z = self._estado
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASCARA_64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASCARA_64
        return z ^ (z >> 31)

    def bytes_aleatorios(self, n):
        """Gera `n` bytes aleatorios (substitui os.urandom)"""
        saida = bytearray()
        while len(saida) < n:
            saida.extend(self.proximo_u64().to_bytes(8, "big"))
        return bytes(saida[:n])


_gerador = GeradorAleatorioNativo()


def gerar_sal():
    """Sal aleatorio de 16 bytes (128 bits), unico para cada senha"""
    return _gerador.bytes_aleatorios(16)


def comparar_tempo_constante(a, b):
    """
    Substitui hmac.compare_digest. Percorre TODOS os bytes mesmo depois de
    achar uma diferenca, para o tempo nao revelar "quantos bytes acertou".
    """
    if len(a) != len(b):
        return False
    diferenca = 0
    for x, y in zip(a, b):
        diferenca |= x ^ y
    return diferenca == 0


# -----------------------------------------------------------------------
# 1) CONSTANTES: OS DIGITOS DE PI (INICIALIZAM O BLOWFISH)
# -----------------------------------------------------------------------
#
# O Blowfish comeca com o vetor P (18 palavras de 32 bits) e 4 caixas S
# (4 x 256 palavras) preenchidos com os digitos hexadecimais da parte
# fracionaria de PI. Prova de "nada na manga": ninguem escondeu backdoor.
#
#     PI = 16 * arctan(1/5) - 4 * arctan(1/239)     (formula de Machin)

QTD_P = 18
QTD_S = 4 * 256
BITS_NECESSARIOS = (QTD_P + QTD_S) * 32     # 33.344 bits de PI


def arctan_inverso(x, escala):
    """arctan(1/x) * escala, pela serie de Taylor, so com inteiros"""
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
    """Parte fracionaria de PI, como um inteiro de `qtd_bits` bits"""
    guarda = 64                              # bits extras contra arredondamento
    escala = 1 << (qtd_bits + guarda)
    pi = 16 * arctan_inverso(5, escala) - 4 * arctan_inverso(239, escala)
    return (pi - 3 * escala) >> guarda       # tira o "3" da parte inteira


def gerar_tabelas_iniciais():
    """Devolve (P, S): 18 palavras e 4 caixas de 256 palavras"""
    fracao = calcular_pi_fracionario(BITS_NECESSARIOS)
    palavras = [(fracao >> (BITS_NECESSARIOS - 32 * (i + 1))) & 0xFFFFFFFF
                for i in range(QTD_P + QTD_S)]
    P = palavras[:QTD_P]
    S = [palavras[QTD_P + 256 * k: QTD_P + 256 * (k + 1)] for k in range(4)]
    return P, S


P_INICIAL, S_INICIAL = gerar_tabelas_iniciais()    # calculado uma unica vez


# -----------------------------------------------------------------------
# 2) A CIFRA BLOWFISH
# -----------------------------------------------------------------------

MASCARA_32 = 0xFFFFFFFF


class EstadoBlowfish:
    """O 'estado' da cifra: vetor P (18 subchaves) + 4 caixas S"""

    def __init__(self):
        self.P = list(P_INICIAL)
        self.S = [list(caixa) for caixa in S_INICIAL]


def funcao_f(estado, x):
    """
    Funcao F do Blowfish: mistura 32 bits usando as 4 caixas S.
        F(x) = ((S0[a] + S1[b]) XOR S2[c]) + S3[d]      (somas mod 2^32)
    onde a, b, c, d sao os 4 bytes de x (do mais ao menos significativo).
    """
    S = estado.S
    a = (x >> 24) & 0xFF
    b = (x >> 16) & 0xFF
    c = (x >> 8) & 0xFF
    d = x & 0xFF
    return ((((S[0][a] + S[1][b]) & MASCARA_32) ^ S[2][c]) + S[3][d]) & MASCARA_32


def cifrar_bloco(estado, esq, dir_, detalhar=False):
    """Cifra um bloco de 64 bits (esq, dir_) e devolve o novo par"""
    _contar_operacao()
    P = estado.P
    for i in range(16):                  # 16 rodadas de Feistel
        esq ^= P[i]                      # 1) XOR com a subchave da rodada
        f = funcao_f(estado, esq)
        dir_ ^= f                        # 2) mistura via F na outra metade
        esq, dir_ = dir_, esq            # 3) troca as metades
        if detalhar and i < 3:
            print(f"           rodada {i + 1:2d}: F = {f:08X} -> E = {esq:08X}  D = {dir_:08X}")
    if detalhar:
        print("           ... (rodadas 4 a 16) ...")
    esq, dir_ = dir_, esq                # desfaz a ultima troca
    dir_ ^= P[16]                        # "branqueamento" final
    esq ^= P[17]
    return esq, dir_


def proxima_palavra(dados, posicao):
    """
    Le 4 bytes (big-endian) de `dados` a partir de `posicao`, dando a volta
    no inicio quando os bytes acabam (a chave e repetida ciclicamente).
    """
    palavra = 0
    for _ in range(4):
        palavra = (palavra << 8) | dados[posicao]
        posicao = (posicao + 1) % len(dados)
    return palavra, posicao


def expandir_chave(estado, chave, sal=None):
    """
    ExpandKey(estado, sal, chave):
      1) P[i] ^= palavras da chave (repetida ciclicamente)
      2) cifra um bloco zerado; o resultado vira P[0],P[1]; cifra de novo
         para P[2],P[3]... e depois para as 4 caixas S inteiras
         (521 cifragens no total)
      3) se houver `sal` (16 bytes = 4 palavras), ele entra por XOR no bloco
         ANTES de cada cifragem. Sem sal, e o Blowfish padrao.
    """
    posicao = 0
    for i in range(18):
        palavra, posicao = proxima_palavra(chave, posicao)
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

    for i in range(0, 18, 2):                        # regenera P
        esq, dir_, indice_sal = proximo_bloco(esq, dir_, indice_sal)
        estado.P[i], estado.P[i + 1] = esq, dir_

    for caixa in estado.S:                           # regenera as 4 caixas S
        for i in range(0, 256, 2):
            esq, dir_, indice_sal = proximo_bloco(esq, dir_, indice_sal)
            caixa[i], caixa[i + 1] = esq, dir_


def expansao_custosa(custo, sal, chave, detalhar=False):
    """
    EksBlowfishSetup(custo, sal, chave) - o coracao do bcrypt:

        estado <- PI
        estado <- ExpandKey(estado, sal, chave)
        repita 2^custo vezes:
            estado <- ExpandKey(estado, 0, chave)
            estado <- ExpandKey(estado, 0, sal)

    Cada +1 no custo DOBRA o trabalho.
    """
    estado = EstadoBlowfish()
    if detalhar:
        print(f"   [Passo 2] Estado <- digitos de PI:   P[0] = {estado.P[0]:08X}  P[1] = {estado.P[1]:08X}")
    expandir_chave(estado, chave, sal)
    if detalhar:
        print(f"   [Passo 3] ExpandKey(sal, senha):     P[0] = {estado.P[0]:08X}  P[1] = {estado.P[1]:08X}")
    for _ in range(2 ** custo):
        expandir_chave(estado, chave)
        expandir_chave(estado, sal)
    if detalhar:
        print(f"   [Passo 4] Apos {2 ** custo} iteracoes (2^{custo}):  P[0] = {estado.P[0]:08X}  P[1] = {estado.P[1]:08X}")
    return estado


# -----------------------------------------------------------------------
# 3) BASE64 DO BCRYPT (alfabeto proprio, sem '=' no final)
# -----------------------------------------------------------------------

ALFABETO = "./ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


def codificar_base64(dados):
    """Bytes -> texto. 16 bytes viram 22 chars; 23 bytes viram 31 chars"""
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
    """Inverso de codificar_base64; devolve `tamanho` bytes"""
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


# -----------------------------------------------------------------------
# 4) O ALGORITMO BCRYPT
# -----------------------------------------------------------------------

VERSAO = "2b"
TAMANHO_MAX_SENHA = 72                       # limite do bcrypt, em bytes
TEXTO_FIXO = b"OrpheanBeholderScryDoubt"     # 24 bytes = 3 blocos de 64 bits


def preparar_senha(senha):
    """
    Passo 1: senha -> UTF-8 + byte \\0, truncada em 72 bytes.
    Consequencia: o que passar de 72 bytes e IGNORADO.
    """
    if isinstance(senha, str):
        senha = senha.encode("utf-8")
    if b"\x00" in senha:
        raise ValueError("A senha nao pode conter byte nulo")
    return (senha + b"\x00")[:TAMANHO_MAX_SENHA]


def calcular_hash_bruto(senha, custo, sal, detalhar=False):
    """Executa os passos do bcrypt e devolve os 23 bytes do hash"""
    if not 4 <= custo <= 31:
        raise ValueError("O custo deve estar entre 4 e 31")
    if len(sal) != 16:
        raise ValueError("O sal deve ter 16 bytes")

    chave = preparar_senha(senha)
    if detalhar:
        print(f"   [Passo 1] Chave = senha + \\0 (max 72 bytes) -> {len(chave)} bytes: {list(chave)}")

    estado = expansao_custosa(custo, sal, chave, detalhar)

    # Passo 5: cifra 64 vezes os 3 blocos de "OrpheanBeholderScryDoubt"
    blocos = [[int.from_bytes(TEXTO_FIXO[i:i + 4], "big"),
               int.from_bytes(TEXTO_FIXO[i + 4:i + 8], "big")]
              for i in range(0, 24, 8)]
    if detalhar:
        antes = "".join(f"{e:08X}{d:08X}" for e, d in blocos)
        print(f"   [Passo 5] Texto fixo (hex):          {antes}")
    for _ in range(64):
        for bloco in blocos:
            bloco[0], bloco[1] = cifrar_bloco(estado, bloco[0], bloco[1])
    saida = b"".join(e.to_bytes(4, "big") + d.to_bytes(4, "big") for e, d in blocos)
    if detalhar:
        print(f"   [Passo 5] Apos 64 cifragens (hex):   {saida.hex().upper()}")
        print("             (24 bytes; o ultimo e descartado -> 23 bytes de hash)")
    return saida[:23]


def gerar_hash(senha, custo=12, sal=None, detalhar=False):
    """Gera o hash completo: $2b$CC$<sal 22 chars><hash 31 chars>"""
    if sal is None:
        sal = gerar_sal()
    if detalhar:
        print(f"   Custo = {custo} -> 2^{custo} = {2 ** custo} iteracoes | sal (hex) = {sal.hex()}")
    bruto = calcular_hash_bruto(senha, custo, sal, detalhar)
    resultado = f"${VERSAO}${custo:02d}${codificar_base64(sal)}{codificar_base64(bruto)}"
    if detalhar:
        print(f"   [Passo 6] Hash final: {resultado}")
    return resultado


def separar_hash(hash_armazenado):
    """Divide '$2b$12$<sal><hash>' em (versao, custo, sal, hash_bytes)"""
    _, versao, custo, resto = hash_armazenado.split("$")
    if versao not in ("2a", "2b", "2y") or len(resto) != 53:
        raise ValueError("formato de hash invalido")
    return versao, int(custo), decodificar_base64(resto[:22], 16), decodificar_base64(resto[22:], 23)


def verificar_senha(senha, hash_armazenado):
    """Recalcula com o custo e o sal guardados no hash e compara"""
    try:
        _, custo, sal, esperado = separar_hash(hash_armazenado)
        novo = calcular_hash_bruto(senha, custo, sal)
    except (ValueError, IndexError):
        return False
    return comparar_tempo_constante(novo, esperado)


# =============================================================================
#  DEMONSTRACAO - roda automaticamente ao executar: python bcrypt_completo.py
# =============================================================================

CUSTO_DEMO = 4      # Python puro e lento: custo 4 a 6 na demo (producao: 12+)


def linha(titulo):
    print("\n" + "=" * 70)
    print(titulo)
    print("=" * 70)


def ler(prompt, padrao=""):
    """input() que nao quebra com Ctrl+C / fim da entrada"""
    try:
        return input(prompt).strip() or padrao
    except (EOFError, KeyboardInterrupt):
        return padrao


def parte_1_blowfish():
    linha("PARTE 1 - Base: a cifra Blowfish e os digitos de PI")
    print(" O bcrypt e construido sobre o Blowfish (Bruce Schneier, 1993).")
    print(f"\n [Passo 1] Digitos de PI calculados aqui (formula de Machin), {BITS_NECESSARIOS} bits:")
    print(f"           P[0] = {P_INICIAL[0]:08X}  (valor oficial: 243F6A88)")
    print(f"           P[1] = {P_INICIAL[1]:08X}  (valor oficial: 85A308D3)")
    print(f"           S0[0] = {S_INICIAL[0][0]:08X}  (valor oficial: D1310BA6)")
    ok = P_INICIAL[0] == 0x243F6A88 and S_INICIAL[0][0] == 0xD1310BA6
    print("           Status: " + ("OK: tabelas identicas as do paper do Blowfish." if ok else "ERRO!"))

    estado = EstadoBlowfish()
    x = 0x12345678
    print(f"\n [Passo 2] Funcao F de Feistel para x = {x:08X}:")
    print(f"           bytes a,b,c,d = {x >> 24:02X}, {(x >> 16) & 255:02X}, {(x >> 8) & 255:02X}, {x & 255:02X}")
    print("           F(x) = ((S0[a] + S1[b]) XOR S2[c]) + S3[d]  (mod 2^32)")
    print(f"           F(x) = {funcao_f(estado, x):08X}")

    print("\n [Passo 3] Cifrando UM bloco de 64 bits (E = 00000000, D = 00000000):")
    e, d = cifrar_bloco(estado, 0, 0, detalhar=True)
    print(f"           Resultado: E = {e:08X}  D = {d:08X}")
    print("\n Por que isso importa? Preparar a chave do Blowfish exige 521 cifragens")
    print(" (reescrever P e as 4 caixas S). O bcrypt repete isso MUITAS vezes de proposito.")


def parte_2_passo_a_passo():
    linha("PARTE 2 - bcrypt passo a passo (senha 'abc', custo 4)")
    senha = "abc"
    cron = CronometroNativo()
    resultado = gerar_hash(senha, CUSTO_DEMO, detalhar=True)
    print(f"\n Cifragens Blowfish executadas: {cron.operacoes():,}")
    esperado = 2 * 521 * (2 ** CUSTO_DEMO) + 521 + 192
    print(f" Conta: (1 + 2*2^{CUSTO_DEMO}) ExpandKey x 521 + 64*3 = {esperado:,}")
    print("\n Anatomia do hash (60 caracteres):")
    print(f"   {resultado}")
    print("   $2b$      versao do algoritmo")
    print(f"   {resultado[4:6]}        custo (2^{int(resultado[4:6])} iteracoes)")
    print(f"   {resultado[7:29]}  sal: 22 chars = 16 bytes")
    print(f"   {resultado[29:]}  hash: 31 chars = 23 bytes")


VETORES = [   # (senha, hash esperado) - gerados/conferidos com a biblioteca oficial
    ("U*U", "$2a$05$CCCCCCCCCCCCCCCCCCCCC.E5YPO9kmyuRGyh0XouQYb4YMJKvyOeW"),
    ("", "$2b$04$......................w74bL5gU7LSJClZClCa.Pkz14aTv/XO"),
    ("abc", "$2b$04$AAAAAAAAAAAAAAAAAAAAA.yZXZXV6HkSkIZ0VwC5Eh2gcvbnBww1G"),
]


def parte_3_vetores():
    linha("PARTE 3 - Prova de correcao: vetores de teste oficiais")
    print(" Mesmo sal + mesma senha DEVEM gerar exatamente o mesmo hash que o bcrypt oficial.")
    todos_ok = True
    for senha, esperado in VETORES:
        _, custo, sal, _ = separar_hash(esperado)
        obtido = gerar_hash(senha, custo, sal)
        ok = obtido[4:] == esperado[4:]       # $2a$ e $2b$ so diferem no prefixo
        todos_ok = todos_ok and ok
        print(f"\n Senha: {senha!r:6} custo {custo:02d}")
        print(f"   esperado: {esperado}")
        print(f"   obtido:   {obtido}   -> {'OK' if ok else 'ERRO'}")
    print("\n OK: implementacao confere com o bcrypt oficial." if todos_ok else "\n ERRO: algum vetor falhou!")


def parte_4_sal_e_custo():
    linha("PARTE 4 - Efeito do SAL e do CUSTO")
    print(" a) Mesma senha, dois sais aleatorios diferentes:")
    h1 = gerar_hash("senha123", CUSTO_DEMO)
    h2 = gerar_hash("senha123", CUSTO_DEMO)
    print(f"    hash 1: {h1}")
    print(f"    hash 2: {h2}")
    print(f"    Iguais? {h1 == h2}  -> rainbow tables viram inuteis e duas contas com a")
    print("    mesma senha nao revelam isso no banco de dados.")
    print("\n b) Cada +1 no custo DOBRA o esforco (medido em cifragens Blowfish):")
    anterior = 0
    for custo in range(4, 8):
        cron = CronometroNativo()
        gerar_hash("teste", custo)
        ops = cron.operacoes()
        razao = f"(x{ops / anterior:.2f})" if anterior else ""
        print(f"    custo {custo:2d} -> {2 ** custo:4d} iteracoes -> {ops:>9,} cifragens {razao}")
        anterior = ops
    print("    Custo 12 (recomendado hoje) seria cerca de 256x o custo 4.")


def tentar_dicionario(hash_alvo, lista, detalhar=True):
    """Ataque de dicionario: tenta cada palavra contra o hash roubado"""
    cron = CronometroNativo()
    for i, palavra in enumerate(lista, 1):
        acertou = verificar_senha(palavra, hash_alvo)
        if detalhar:
            print(f"    tentativa {i:2d}: {palavra!r:14} -> {'ACERTOU!' if acertou else 'errou'}")
        if acertou:
            return palavra, i, cron.operacoes()
    return None, len(lista), cron.operacoes()


DICIONARIO = ["123456", "password", "qwerty", "abc123", "letmein",
              "senha123", "admin", "iloveyou", "monkey", "dragon"]


def parte_5_cadastro_e_ataque():
    linha("PARTE 5 - Simulacao: cadastro, login e vazamento do banco de dados")
    banco = {}
    print(" Cadastro: o servidor NUNCA guarda a senha, so o hash.")
    banco["alice"] = gerar_hash("senha123", CUSTO_DEMO)
    banco["bruno"] = gerar_hash("senha123", CUSTO_DEMO)
    for usuario, h in banco.items():
        print(f"   {usuario:6} -> {h}")
    print("   (Alice e Bruno usam a MESMA senha, mas os hashes sao diferentes por causa do sal)")

    print("\n Login:")
    print(f"   alice digita 'senha123' -> {'ACESSO LIBERADO' if verificar_senha('senha123', banco['alice']) else 'NEGADO'}")
    print(f"   alice digita 'senha124' -> {'ACESSO LIBERADO' if verificar_senha('senha124', banco['alice']) else 'NEGADO'}")

    print("\n Vazamento: um atacante rouba o banco e testa um dicionario de senhas comuns:")
    palavra, tentativas, ops = tentar_dicionario(banco["alice"], DICIONARIO)
    print(f"\n   Senha fraca descoberta: {palavra!r} em {tentativas} tentativa(s), {ops:,} cifragens.")
    print(f"   Custo por tentativa: ~{ops // tentativas:,} cifragens. Com custo 12 seria ~256x mais.")
    print("   Com SHA-256 (1 chamada) ele testaria bilhoes de senhas por segundo; com bcrypt,")
    print("   cada palpite custa milhares de cifragens - e o SAL obriga a atacar cada usuario separado.")
    print("   Licao: bcrypt NAO salva senha fraca (ela cai em um dicionario); ele so encarece cada palpite.")


def parte_6_conceitos_avancados():
    linha("PARTE 6 - Conceitos avancados: limite de 72 bytes e comparacao com alternativas")
    sal = gerar_sal()
    base = "A" * 72
    h1 = gerar_hash(base + "123", CUSTO_DEMO, sal)
    h2 = gerar_hash(base + "999", CUSTO_DEMO, sal)
    print(" 1) LIMITE DE 72 BYTES (18 palavras do vetor P x 4 bytes):")
    print(f"    senha A = 72 x 'A' + '123'  (75 bytes)")
    print(f"    senha B = 72 x 'A' + '999'  (75 bytes)")
    print(f"    hash A: {h1}")
    print(f"    hash B: {h2}")
    print(f"    Iguais? {h1 == h2}  -> tudo depois do byte 72 e IGNORADO!")
    print("    Solucao usada na pratica: fazer um pre-hash (ex.: SHA-256 + base64) antes do bcrypt.")

    print("\n 2) BYTE NULO: o \\0 e o terminador da chave, por isso e proibido na senha:")
    try:
        gerar_hash(b"ab\x00cd", CUSTO_DEMO)
    except ValueError as erro:
        print(f"    gerar_hash(b'ab\\x00cd') -> ValueError: {erro}")

    print("\n 3) COMPARACAO COM OUTRAS FUNCOES DE HASH DE SENHAS:")
    print(" +-----------+------+-------------------+------------------------------+")
    print(" | Algoritmo | Ano  | Memoria exigida   | Observacao                   |")
    print(" +-----------+------+-------------------+------------------------------+")
    print(" | bcrypt    | 1999 | ~4 KB (fixa)      | Custo ajustavel; limite 72 B |")
    print(" | PBKDF2    | 2000 | minima            | Padrao antigo; so CPU        |")
    print(" | scrypt    | 2009 | configuravel (MB) | Memory-hard                  |")
    print(" | Argon2id  | 2015 | configuravel (MB) | Recomendado pela OWASP       |")
    print(" +-----------+------+-------------------+------------------------------+")


def aovivo_hash():
    linha("AO VIVO - Gerar hash passo a passo")
    senha = ler("Senha (padrao 'minhaSenha'): ", "minhaSenha")
    custo = int(ler(f"Custo 4 a 8 [{CUSTO_DEMO}]: ", str(CUSTO_DEMO)))
    cron = CronometroNativo()
    try:
        gerar_hash(senha, custo, detalhar=True)
        print(f"\n Cifragens Blowfish: {cron.operacoes():,}")
    except ValueError as erro:
        print(f" Erro: {erro}")


def aovivo_verificar():
    linha("AO VIVO - Verificar senha")
    senha = ler("Senha para testar: ")
    armazenado = ler("Hash armazenado ($2b$...): ")
    if verificar_senha(senha, armazenado):
        print(" Senha CORRETA")
    else:
        print(" Senha INCORRETA (ou hash invalido)")


def aovivo_ataque():
    linha("AO VIVO - Ataque de dicionario contra a SUA senha")
    senha = ler("Digite uma senha (padrao 'dragon'): ", "dragon")
    alvo = gerar_hash(senha, CUSTO_DEMO)
    print(f" Hash gerado: {alvo}\n Atacante testando {len(DICIONARIO)} senhas comuns:")
    palavra, tentativas, ops = tentar_dicionario(alvo, DICIONARIO)
    if palavra:
        print(f"\n QUEBRADA em {tentativas} tentativa(s)! Senha fraca nao se salva nem com bcrypt.")
    else:
        print(f"\n Nao esta no dicionario: {ops:,} cifragens gastas sem sucesso.")


def aovivo_limite72():
    linha("AO VIVO - Limite de 72 bytes")
    a = ler("Senha A (padrao 80 letras 'x'): ", "x" * 80)
    b = ler("Senha B (padrao igual a A com final diferente): ", a[:72] + "OUTRO")
    sal = gerar_sal()
    ha = gerar_hash(a, CUSTO_DEMO, sal)
    hb = gerar_hash(b, CUSTO_DEMO, sal)
    print(f" Tamanhos em bytes: A = {len(a.encode('utf-8'))}, B = {len(b.encode('utf-8'))}")
    print(f" Hashes iguais? {ha == hb}")


def menu_interativo():
    opcoes = {"1": ("Gerar hash passo a passo", aovivo_hash),
              "2": ("Verificar senha", aovivo_verificar),
              "3": ("Ataque de dicionario", aovivo_ataque),
              "4": ("Limite de 72 bytes", aovivo_limite72)}
    while True:
        print("\n" + "=" * 70)
        print("                     MENU INTERATIVO BCRYPT")
        print("=" * 70)
        for chave, (nome, _) in opcoes.items():
            print(f" [{chave}] {nome}")
        print(" [0] Sair")
        escolha = ler(" Escolha uma opcao [0-4]: ", "0")
        if escolha in opcoes:
            opcoes[escolha][1]()
        elif escolha in ("0", "sair", "exit"):
            print("\n Aplicacao encerrada. Bom seminario!")
            break
        else:
            print("\n [!] Opcao invalida.")


def main():
    parte_1_blowfish()
    parte_2_passo_a_passo()
    parte_3_vetores()
    parte_4_sal_e_custo()
    parte_5_cadastro_e_ataque()
    parte_6_conceitos_avancados()
    menu_interativo()


if __name__ == "__main__":
    main()
