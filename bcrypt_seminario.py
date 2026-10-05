"""
=============================================================================
 bcrypt em Python puro (SEM NENHUM IMPORT) - versao comentada para estudo
=============================================================================

O PROBLEMA QUE O BCRYPT RESOLVE
  Sites nunca devem guardar a senha em si, e sim um "hash" dela. Um hash e
  uma funcao de mao unica: dada a senha voce calcula o hash facilmente, mas
  dado o hash nao ha como voltar a senha. No login, o site calcula o hash da
  senha digitada e compara com o guardado.

  Se o banco de dados vazar, o atacante tenta "chutar" senhas: calcula o hash
  de milhoes de palavras e compara. Hashes comuns (SHA-256) sao RAPIDOS, entao
  ele testa bilhoes por segundo. O bcrypt e de proposito LENTO e AJUSTAVEL.

GLOSSARIO RAPIDO
  Hash ........ "impressao digital" irreversivel de um dado.
  Sal (salt) .. valor aleatorio gerado para cada senha e guardado junto do
                hash. Garante que a mesma senha gere hashes diferentes e
                inutiliza tabelas pre-calculadas (rainbow tables).
  Custo ....... numero N que faz o bcrypt repetir o trabalho 2^N vezes.
                Cada +1 DOBRA o tempo. Hoje se recomenda 12 ou mais.
  Blowfish .... cifra de bloco de 1993 (Bruce Schneier). O bcrypt a
                reaproveita, mas usa so sua parte de "preparar a chave".
  Feistel ..... estrutura de cifra: divide o bloco em duas metades e, em
                varias rodadas, mistura uma metade com a outra.
  Bloco ....... pedaco de 64 bits (duas palavras de 32 bits: esq e dir_).
  S-box ....... tabela de 256 numeros usada para embaralhar bits.

COMO RODAR:  python bcrypt_didatico.py
=============================================================================
"""

# Mascaras para simular inteiros de tamanho fixo. O Python tem inteiros
# ilimitados, mas o Blowfish trabalha com 32 bits. "& M32" descarta o que
# passar de 32 bits, o que equivale a fazer a conta "modulo 2^32".
M32 = 0xFFFFFFFF
M64 = 0xFFFFFFFFFFFFFFFF

# ---------------------------------------------------------------------
# PARTE A - OS DIGITOS DE PI (valores iniciais do Blowfish)
# ---------------------------------------------------------------------
# O Blowfish precisa de numeros iniciais que pareçam aleatorios, mas que
# ninguem possa acusar de esconder uma "porta dos fundos". Solucao: usar os
# digitos de PI, que todo mundo pode conferir. Aqui calculamos PI em vez de
# colar uma tabela gigante. Formula de Machin:
#       PI = 16*arctan(1/5) - 4*arctan(1/239)

def arctan_inverso(x, escala):
    """Calcula arctan(1/x) * escala usando a serie de Taylor, so com
    inteiros (multiplicamos por uma 'escala' enorme no lugar de usar
    decimais, para nao perder precisao)."""
    termo = escala // x              # primeiro termo da serie: 1/x
    soma, x2, n, sinal = termo, x * x, 3, -1
    while termo:                     # para quando o termo zera
        termo //= x2                 # proximo termo: divide por x^2
        soma += sinal * (termo // n) # alterna +, -, +, - ... (1/n)
        sinal, n = -sinal, n + 2     # n = 3, 5, 7, ...
    return soma


def tabelas_de_pi():
    """Devolve (P, S): o vetor P (18 numeros de 32 bits) e as 4 S-boxes
    (4 tabelas de 256 numeros de 32 bits), todos tirados dos digitos
    fracionarios de PI (a parte depois da virgula)."""
    bits = (18 + 1024) * 32          # total de bits de PI necessarios
    escala = 1 << (bits + 64)        # 64 bits extras evitam erro de arredondamento
    pi = 16 * arctan_inverso(5, escala) - 4 * arctan_inverso(239, escala)
    fracao = (pi - 3 * escala) >> 64 # tira o "3" de "3,1415..." e os bits extras
    # Fatia a fracao em palavras de 32 bits, da esquerda para a direita
    w = [(fracao >> (bits - 32 * (i + 1))) & M32 for i in range(18 + 1024)]
    return w[:18], [w[18 + 256 * k: 18 + 256 * (k + 1)] for k in range(4)]


P0, S0 = tabelas_de_pi()             # calculado uma unica vez ao iniciar

# ---------------------------------------------------------------------
# PARTE B - A CIFRA BLOWFISH
# ---------------------------------------------------------------------

class Estado:
    """O 'estado' da cifra = vetor P (18 subchaves) + 4 S-boxes. O bcrypt
    comeca de uma COPIA dos digitos de PI e vai modificando esse estado."""
    def __init__(self):
        self.P = list(P0)
        self.S = [list(c) for c in S0]


# Conta quantas cifragens de bloco foram feitas. Serve para medir o
# "esforco" sem usar a biblioteca `time` (e nao depende do seu computador).
contador = [0]


def funcao_f(S, x):
    """Funcao F do Blowfish: embaralha 32 bits. Quebra x em 4 bytes (a,b,c,d),
    consulta uma S-box para cada e combina:
        F(x) = ((S0[a] + S1[b]) XOR S2[c]) + S3[d]     (somas mod 2^32)
    Mexer em 1 bit de x muda o resultado inteiro (efeito avalanche)."""
    return ((((S[0][x >> 24] + S[1][(x >> 16) & 255]) & M32)
             ^ S[2][(x >> 8) & 255]) + S[3][x & 255]) & M32


def cifrar_bloco(est, esq, dir_, detalhar=False):
    """Cifra um bloco de 64 bits (duas metades de 32). Rede de Feistel de
    16 rodadas. Em cada rodada:
        1) esq = esq XOR subchave P[i]
        2) dir_ = dir_ XOR F(esq)
        3) troca as metades
    No fim ha um 'branqueamento' final com P[16] e P[17]."""
    contador[0] += 1
    P, S = est.P, est.S
    for i in range(16):
        esq ^= P[i]
        f = funcao_f(S, esq)
        dir_ ^= f
        esq, dir_ = dir_, esq
        if detalhar and i < 3:       # mostra so as 3 primeiras rodadas
            print(f"           rodada {i + 1:2d}: F = {f:08X} -> E = {esq:08X}  D = {dir_:08X}")
    if detalhar:
        print("           ... (rodadas 4 a 16) ...")
    esq, dir_ = dir_, esq            # desfaz a ultima troca
    return esq ^ P[17], dir_ ^ P[16]


def expandir_chave(est, chave, sal=None):
    """ExpandKey: a operacao CENTRAL (e cara) do bcrypt. 'Mistura' a chave
    (e opcionalmente o sal) dentro do estado:
      1) P[i] ^= palavras da chave (repetida em ciclo ate cobrir os 18 P).
      2) Cifra um bloco zerado; o resultado substitui P[0],P[1]. Cifra o
         resultado de novo -> P[2],P[3]... e depois as 4 S-boxes inteiras.
         Total: 9 + 512 = 521 cifragens por chamada.
      3) Se houver sal, ele entra por XOR no bloco ANTES de cada cifragem.
    Como cada cifragem depende do estado ja modificado, nao da para
    paralelizar nem pular etapas: e preciso fazer tudo em ordem."""
    pos = 0
    for i in range(18):              # passo 1: mistura a chave no vetor P
        w = 0
        for _ in range(4):           # monta uma palavra com 4 bytes da chave
            w = (w << 8) | chave[pos]
            pos = (pos + 1) % len(chave)   # volta ao inicio quando acaba
        est.P[i] ^= w

    # O sal tem 16 bytes = 4 palavras de 32 bits
    ws = [int.from_bytes(sal[i:i + 4], "big") for i in range(0, 16, 4)] if sal else None
    esq = dir_ = k = 0

    def passo(esq, dir_, k):         # uma cifragem, com sal se houver
        if ws:
            esq ^= ws[k % 4]
            dir_ ^= ws[(k + 1) % 4]
            k += 2
        e, d = cifrar_bloco(est, esq, dir_)
        return e, d, k

    for i in range(0, 18, 2):        # passo 2a: reescreve o vetor P
        esq, dir_, k = passo(esq, dir_, k)
        est.P[i], est.P[i + 1] = esq, dir_
    for caixa in est.S:              # passo 2b: reescreve as 4 S-boxes
        for i in range(0, 256, 2):
            esq, dir_, k = passo(esq, dir_, k)
            caixa[i], caixa[i + 1] = esq, dir_

# ---------------------------------------------------------------------
# PARTE C - BASE64 DO BCRYPT
# ---------------------------------------------------------------------
# O hash final e texto. Base64 transforma bytes em caracteres imprimiveis,
# mas o bcrypt usa um alfabeto PROPRIO (diferente do base64 padrao) e nao
# usa '=' de preenchimento. Cada 3 bytes viram 4 caracteres.

ALFABETO = "./ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


def b64_codificar(d):
    """Bytes -> texto. 16 bytes (sal) viram 22 chars; 23 bytes viram 31."""
    out, i = [], 0
    while i < len(d):
        c1 = d[i]; i += 1
        out.append(ALFABETO[c1 >> 2])            # 6 bits do 1o byte
        c1 = (c1 & 3) << 4                       # sobram 2 bits
        if i >= len(d):
            out.append(ALFABETO[c1]); break
        c2 = d[i]; i += 1
        out.append(ALFABETO[c1 | (c2 >> 4)])     # 2 bits + 4 bits do 2o
        c1 = (c2 & 15) << 2                      # sobram 4 bits
        if i >= len(d):
            out.append(ALFABETO[c1]); break
        c2 = d[i]; i += 1
        out.append(ALFABETO[c1 | (c2 >> 6)])     # 4 bits + 2 bits do 3o
        out.append(ALFABETO[c2 & 63])            # ultimos 6 bits do 3o
    return "".join(out)


def b64_decodificar(t, tamanho):
    """Texto -> bytes (inverso da funcao acima). Usado para recuperar o sal
    e o hash a partir da string guardada no banco de dados."""
    v = [ALFABETO.index(c) for c in t]           # cada char vira um valor 0..63
    out, i = bytearray(), 0
    while len(out) < tamanho and i + 1 < len(v):
        out.append(((v[i] << 2) | (v[i + 1] >> 4)) & 255)
        if len(out) >= tamanho or i + 2 >= len(v): break
        out.append(((v[i + 1] << 4) | (v[i + 2] >> 2)) & 255)
        if len(out) >= tamanho or i + 3 >= len(v): break
        out.append(((v[i + 2] << 6) | v[i + 3]) & 255)
        i += 4
    return bytes(out[:tamanho])

# ---------------------------------------------------------------------
# PARTE D - SAL ALEATORIO
# ---------------------------------------------------------------------
# Sem imports nao temos os.urandom, entao usamos o SplitMix64: um gerador
# pseudoaleatorio simples. A semente vem de enderecos de memoria (id()).
# ATENCAO: so serve para demonstracao! Em producao, use SEMPRE o gerador
# criptografico do sistema operacional (os.urandom / secrets).

_estado = (id(object()) ^ id([]) ^ hash((id({}), id(lambda: 0)))) & M64


def gerar_sal():
    """Sal de 16 bytes (128 bits), diferente a cada chamada."""
    global _estado
    out = bytearray()
    while len(out) < 16:
        _estado = (_estado + 0x9E3779B97F4A7C15) & M64
        z = _estado
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
        out.extend((z ^ (z >> 31)).to_bytes(8, "big"))
    return bytes(out[:16])

# ---------------------------------------------------------------------
# PARTE E - O ALGORITMO BCRYPT (junta tudo)
# ---------------------------------------------------------------------

# Texto fixo do bcrypt (24 bytes = 3 blocos de 64 bits). Sera cifrado 64
# vezes; o resultado vira o hash. Vem de uma citacao de Dante.
TEXTO = b"OrpheanBeholderScryDoubt"


def hash_bruto(senha, custo, sal, detalhar=False):
    """Executa os passos do bcrypt e devolve os 23 bytes do hash."""
    if isinstance(senha, str):
        senha = senha.encode("utf-8")            # texto -> bytes
    if b"\x00" in senha:                         # \0 e usado como terminador
        raise ValueError("senha nao pode ter byte nulo")
    if not 4 <= custo <= 31 or len(sal) != 16:
        raise ValueError("custo ou sal invalido")

    # PASSO 1: a chave e senha + byte \0, cortada em 72 bytes (18 palavras
    # do vetor P x 4 bytes). LIMITACAO: o que passar de 72 bytes e IGNORADO.
    chave = (senha + b"\x00")[:72]
    if detalhar:
        print(f"   [Passo 1] Chave = senha + \\0 (max 72 bytes) -> {len(chave)} bytes")

    # PASSO 2: estado inicial = digitos de PI
    est = Estado()
    if detalhar:
        print(f"   [Passo 2] Estado <- PI:              P[0] = {est.P[0]:08X}  P[1] = {est.P[1]:08X}")

    # PASSO 3: mistura sal e senha no estado
    expandir_chave(est, chave, sal)
    if detalhar:
        print(f"   [Passo 3] ExpandKey(sal, senha):     P[0] = {est.P[0]:08X}  P[1] = {est.P[1]:08X}")

    # PASSO 4: O CORACAO DO BCRYPT. Repete 2^custo vezes, alternando
    # senha e sal. E AQUI que esta a lentidao proposital.
    for _ in range(2 ** custo):
        expandir_chave(est, chave)
        expandir_chave(est, sal)
    if detalhar:
        print(f"   [Passo 4] Apos 2^{custo} = {2 ** custo} iteracoes:    P[0] = {est.P[0]:08X}  P[1] = {est.P[1]:08X}")

    # PASSO 5: cifra 64 vezes os 3 blocos do texto fixo com o estado final
    blocos = [[int.from_bytes(TEXTO[i:i + 4], "big"),
               int.from_bytes(TEXTO[i + 4:i + 8], "big")] for i in range(0, 24, 8)]
    for _ in range(64):
        for b in blocos:
            b[0], b[1] = cifrar_bloco(est, b[0], b[1])
    saida = b"".join(e.to_bytes(4, "big") + d.to_bytes(4, "big") for e, d in blocos)
    if detalhar:
        print(f"   [Passo 5] Apos 64 cifragens (hex):   {saida.hex().upper()}")
        print("             (24 bytes; o ultimo e descartado -> 23 bytes de hash)")
    return saida[:23]                            # historicamente descarta-se 1 byte


def gerar_hash(senha, custo=12, sal=None, detalhar=False):
    """PASSO 6: monta a string final guardada no banco:
         $2b$ CC $ <sal: 22 chars> <hash: 31 chars>      (60 chars no total)
       onde $2b$ e a versao do algoritmo e CC e o custo (ex.: 12).
    O sal e o custo ficam DENTRO do hash, por isso o login so precisa dele."""
    sal = sal or gerar_sal()
    if detalhar:
        print(f"   Custo = {custo} -> 2^{custo} = {2 ** custo} iteracoes | sal (hex) = {sal.hex()}")
    bruto = hash_bruto(senha, custo, sal, detalhar)
    resultado = f"$2b${custo:02d}${b64_codificar(sal)}{b64_codificar(bruto)}"
    if detalhar:
        print(f"   [Passo 6] Hash final: {resultado}")
    return resultado


def verificar_senha(senha, armazenado):
    """Login: le custo e sal do hash guardado, refaz o calculo com a senha
    digitada e compara. Nunca 'desfaz' o hash - so recalcula."""
    try:
        _, versao, custo, resto = armazenado.split("$")
        if versao not in ("2a", "2b", "2y") or len(resto) != 53:
            return False
        sal = b64_decodificar(resto[:22], 16)        # 22 primeiros chars = sal
        esperado = b64_decodificar(resto[22:], 23)   # 31 ultimos chars = hash
        novo = hash_bruto(senha, int(custo), sal)
    except (ValueError, IndexError):
        return False
    # Comparacao em TEMPO CONSTANTE: percorre todos os bytes sem parar no
    # primeiro erro. Um '==' normal para na 1a diferenca, e medindo o tempo
    # um atacante poderia descobrir quantos bytes acertou (timing attack).
    dif = 0
    for x, y in zip(novo, esperado):
        dif |= x ^ y
    return dif == 0

# ---------------------------------------------------------------------
# DEMONSTRACAO (roda ao executar o arquivo)
# ---------------------------------------------------------------------

CUSTO = 4      # Python puro e lento: use 4 a 6 na demo (producao: 12+)
def titulo(t):
    print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)


def ler(prompt, padrao=""):
    """input() que nao quebra com Ctrl+C ou fim da entrada."""
    try:
        return input(prompt).strip() or padrao
    except (EOFError, KeyboardInterrupt):
        return padrao


def parte_1():
    """Gera um hash mostrando os 6 passos e confere a contagem de cifragens."""
    titulo("PARTE 1 - bcrypt passo a passo (senha 'abc', custo 4)")
    contador[0] = 0
    h = gerar_hash("abc", CUSTO, detalhar=True)
    # (1 + 2*2^custo) ExpandKey x 521 cifragens + 64 x 3 blocos finais
    print(f"\n Cifragens Blowfish: {contador[0]:,} (esperado: {2 * 521 * 2 ** CUSTO + 521 + 192:,})")
    print(f" Anatomia: $2b$ versao | {h[4:6]} custo | {h[7:29]} sal | {h[29:]} hash")


def parte_2():
    """Efeito do sal: mesma senha, hashes diferentes."""
    titulo("PARTE 2 - O sal: mesma senha, hashes diferentes")
    h1, h2 = gerar_hash("senha123", CUSTO), gerar_hash("senha123", CUSTO)
    print(" Senha usada nas duas vezes: 'senha123'")
    print(f" hash 1: {h1}")
    print(f" hash 2: {h2}")
    print(f" sal 1:  {h1[7:29]}")
    print(f" sal 2:  {h2[7:29]}")
    print(f" Hashes iguais? {h1 == h2} -> cada hash recebeu um sal aleatorio proprio.")
    print(" Os dois continuam validos: o login le o sal de dentro de cada hash.")
    print(f" verificar_senha('senha123', hash 1) = {verificar_senha('senha123', h1)}")
    print(f" verificar_senha('senha123', hash 2) = {verificar_senha('senha123', h2)}")


def parte_3():
    """Limite de 72 bytes: senhas diferentes depois do byte 72 sao a MESMA senha."""
    titulo("PARTE 3 - Limite de 72 bytes: senhas diferentes, mesmo hash")
    base = "A" * 72
    senha_a = base + "-final-um"
    senha_b = base + "-OUTRO-final"
    senha_c = "B" + base[1:] + "-final-um"       # difere no 1o byte (dentro dos 72)
    sal = gerar_sal()                            # mesmo sal para comparar de forma justa
    hash_a = gerar_hash(senha_a, CUSTO, sal)
    hash_b = gerar_hash(senha_b, CUSTO, sal)
    hash_c = gerar_hash(senha_c, CUSTO, sal)
    print(f" Senha A: 72 x 'A' + '-final-um'      ({len(senha_a)} bytes)")
    print(f" Senha B: 72 x 'A' + '-OUTRO-final'   ({len(senha_b)} bytes)")
    print(f" Senha C: 'B' + 71 x 'A' + '-final-um' ({len(senha_c)} bytes)")
    print(f" A e B sao diferentes? {senha_a != senha_b}  (so mudam DEPOIS do byte 72)")
    print(f" C e A sao diferentes? {senha_c != senha_a}  (mudam logo no 1o byte)")
    print(f"\n hash A: {hash_a}")
    print(f" hash B: {hash_b}")
    print(f" hash C: {hash_c}")
    print(f"\n hash A == hash B ? {hash_a == hash_b}  <- o bcrypt ignorou tudo depois do byte 72")
    print(f" hash A == hash C ? {hash_a == hash_c}  <- mudanca dentro dos 72 bytes altera o hash")
    entra = verificar_senha(senha_b, hash_a)
    print(f"\n Login na conta da senha A usando a senha B: {'ACEITO!' if entra else 'negado'}")
    print(" Consequencia: duas senhas diferentes valem o mesmo. Solucao: pre-hash da senha.")


def cifragens_por_hash(custo):
    """Cifragens Blowfish para gerar UM hash: (1 + 2*2^custo) ExpandKey x 521 + 192."""
    return (1 + 2 * 2 ** custo) * 521 + 192


def forca_bruta_pin():
    """Forca bruta em PIN de 2 digitos: o atacante tenta 00, 01, 02... ate acertar.
    Depois projeta o esforco para PINs maiores e para o custo 12."""
    pin = ler("PIN de 2 digitos (padrao 07): ", "07")
    if len(pin) != 2 or not pin.isdigit():
        print(" Digite exatamente 2 digitos.")
        return
    alvo = gerar_hash(pin, CUSTO)
    print(f" Hash do PIN (custo {CUSTO}): {alvo}\n Atacante testando 00, 01, 02, ...")
    contador[0] = 0
    for n in range(100):
        palpite = f"{n:02d}"
        acertou = verificar_senha(palpite, alvo)
        if acertou or n % 10 == 0:
            print(f"   tentativa {n + 1:3d}: {palpite} -> {'ACERTOU!' if acertou else 'errou'}")
        if acertou:
            break
    gasto = contador[0]
    print(f"\n PIN descoberto em {n + 1} tentativa(s): {gasto:,} cifragens ({gasto // (n + 1):,} por tentativa).")
    print("\n Projecao do PIOR CASO (testar todas as combinacoes):")
    print(f"   {'PIN':10}{'combinacoes':>13}{'custo':>7}{'cifragens':>20}{'vs. agora':>14}")
    for nome, combos in (("2 digitos", 100), ("4 digitos", 10 ** 4), ("6 digitos", 10 ** 6)):
        for c in (CUSTO, 12):
            total = combos * cifragens_por_hash(c)
            print(f"   {nome:10}{combos:>13,}{c:>7}{total:>20,}{total / gasto:>13,.0f}x")
    print(" Moral: o esforco cresce com o tamanho da senha E com o custo (4 -> 12 = ~245x).")


def menu():
    """Menu para testar ao vivo na apresentacao."""
    while True:
        titulo("MENU: [1] Gerar hash  [2] Verificar senha  [3] Forca bruta em PIN  [0] Sair")
        op = ler(" Escolha: ", "0")
        if op == "1":
            try:
                gerar_hash(ler("Senha: ", "minhaSenha"), int(ler(f"Custo 4 a 8 [{CUSTO}]: ", str(CUSTO))), detalhar=True)
            except ValueError as erro:
                print(f" Erro: {erro}")
        elif op == "2":
            ok = verificar_senha(ler("Senha: "), ler("Hash ($2b$...): "))
            print(" Senha CORRETA" if ok else " Senha INCORRETA (ou hash invalido)")
        elif op == "3":
            forca_bruta_pin()
        elif op == "0":
            break


if __name__ == "__main__":
    parte_1(); parte_2(); parte_3()
    menu()
