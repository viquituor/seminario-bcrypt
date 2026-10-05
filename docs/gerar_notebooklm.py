"""Gera docs/bcrypt_para_notebooklm.pdf: texto corrido, pensado para o NotebookLM."""

import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

L = dict(new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf = FPDF(format="A4")
pdf.set_auto_page_break(True, margin=18)
pdf.set_margins(20, 18, 20)
pdf.add_page()


def h1(t):
    pdf.set_font("Helvetica", "B", 20)
    pdf.multi_cell(0, 10, t, **L)
    pdf.ln(2)


def h2(t):
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 7, t, **L)
    pdf.ln(1)


def p(t):
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 5.8, t, **L)
    pdf.ln(2)


h1("bcrypt: como funciona o algoritmo de hash de senhas")
p("Documento de estudo para o Seminario 01 de Seguranca (Algoritmos de Criptografia), Tema 09: bcrypt. Autores do trabalho: Isabela Sousa e Paulo Victor Almeida. O objetivo deste texto e explicar, em linguagem simples e em ordem logica, o que e o bcrypt, por que ele existe, como o algoritmo funciona passo a passo e quais sao seus pontos fortes e limitacoes. Tambem descreve a implementacao feita pela dupla em Python puro, sem nenhum import.")

h2("1. O problema: como guardar senhas")
p("Qualquer sistema com login precisa verificar senhas. A pior solucao e guardar a senha em texto puro: se o banco de dados vazar, todas as senhas ficam expostas. A solucao correta e guardar apenas um hash da senha. Um hash e uma funcao de mao unica: dada a senha, e facil calcular o hash; dado o hash, nao existe forma pratica de recuperar a senha. No login, o sistema calcula o hash da senha digitada e compara com o hash guardado.")
p("O problema aparece quando o banco vaza. O atacante nao consegue desfazer o hash, mas pode chutar senhas: calcula o hash de milhoes de palavras comuns e compara com os hashes roubados. Esse ataque se chama forca bruta ou ataque de dicionario. Funcoes de hash de uso geral, como MD5 e SHA-256, foram projetadas para serem rapidas, e por isso um atacante com placas de video consegue testar bilhoes de palpites por segundo. Para senhas, e preciso o oposto: uma funcao lenta de proposito.")

h2("2. O que e o bcrypt")
p("O bcrypt e uma funcao de hash feita especificamente para senhas. Foi criado por Niels Provos e David Mazieres, apresentado em 1999 na conferencia USENIX no artigo 'A Future-Adaptable Password Scheme', e foi desenvolvido para o sistema operacional OpenBSD. Ele e baseado na cifra de bloco Blowfish, criada por Bruce Schneier em 1993. O bcrypt reaproveita a parte mais cara do Blowfish, a preparacao da chave, e a transforma em um mecanismo de lentidao ajustavel.")
p("O bcrypt tem tres ideias centrais. A primeira e o hash de mao unica: nao existe operacao de descriptografar. A segunda e o sal: um valor aleatorio de 16 bytes (128 bits) gerado para cada senha e guardado dentro do proprio hash. Gracas ao sal, a mesma senha gera hashes diferentes em contas diferentes, e as tabelas pre-calculadas chamadas rainbow tables deixam de funcionar. O sal nao e segredo. A terceira ideia e o custo: um numero N que faz o algoritmo repetir o trabalho 2 elevado a N vezes. Cada aumento de 1 no custo dobra o tempo de calculo. Assim, conforme os computadores ficam mais rapidos, basta aumentar o custo. A recomendacao atual e usar custo 12 ou mais, com minimo de 10.")

h2("3. Anatomia do hash de 60 caracteres")
p("Um hash bcrypt tem sempre 60 caracteres e esta no formato: cifrao, versao, cifrao, custo com dois digitos, cifrao, 22 caracteres de sal e 31 caracteres de hash. Exemplo: $2b$05$RJatSMavAUXuKMySN8WKfeOeoSNcdW5.UBnEOm9EnZpnpV64Fe0eq. Aqui '2b' e a versao do algoritmo, '05' e o custo (2 elevado a 5, ou seja, 32 repeticoes), 'RJatSMavAUXuKMySN8WKfe' e o sal de 16 bytes codificado em 22 caracteres e o restante e o hash de 23 bytes codificado em 31 caracteres. Como versao, custo e sal ficam dentro do proprio hash, o sistema de login consegue refazer o calculo usando apenas o hash armazenado e a senha digitada.")
p("A codificacao usa um base64 proprio do bcrypt, com o alfabeto de ponto, barra, letras maiusculas, letras minusculas e digitos, e sem o sinal de igual de preenchimento. A cada 3 bytes sao gerados 4 caracteres. Por isso 16 bytes de sal viram 22 caracteres e 23 bytes de hash viram 31 caracteres.")

h2("4. A base: a cifra Blowfish")
p("O Blowfish e uma cifra de bloco: cifra dados em blocos de 64 bits, vistos como duas metades de 32 bits, a esquerda e a direita. Usa uma estrutura chamada rede de Feistel, com 16 rodadas. Em cada rodada, a metade esquerda recebe um XOR com uma subchave, o resultado passa por uma funcao F e e combinado por XOR com a metade direita, e depois as duas metades trocam de lugar. No final ha um passo de branqueamento com duas subchaves extras.")
p("O estado interno do Blowfish tem duas partes: o vetor P, com 18 subchaves de 32 bits, e quatro S-boxes, que sao tabelas de 256 numeros de 32 bits cada, totalizando cerca de 4 KB. A funcao F divide uma palavra de 32 bits em quatro bytes a, b, c e d, consulta uma S-box para cada byte e combina os resultados: F(x) = ((S0[a] + S1[b]) XOR S2[c]) + S3[d], com somas modulo 2 elevado a 32.")
p("Os valores iniciais do vetor P e das S-boxes sao os digitos hexadecimais da parte fracionaria do numero pi. Por exemplo, P[0] vale 243F6A88. Usar pi mostra que nao ha nenhuma porta dos fundos escondida nos numeros, pois qualquer pessoa pode conferir. Na implementacao da dupla, esses digitos nao sao colados de uma tabela: sao calculados com a formula de Machin, pi = 16 arctan(1/5) - 4 arctan(1/239), usando apenas aritmetica de inteiros grandes.")
p("O ponto que interessa ao bcrypt: preparar uma chave no Blowfish e caro. A preparacao mistura a chave no vetor P e depois cifra blocos repetidamente para reescrever todo o vetor P e todas as S-boxes. Sao 9 cifragens para o vetor P e 512 para as quatro S-boxes, num total de 521 cifragens por preparacao.")

h2("5. O algoritmo do bcrypt passo a passo")
p("O bcrypt usa uma variante chamada Eksblowfish, de 'expensive key schedule Blowfish', ou seja, Blowfish com preparacao de chave cara. As entradas sao a senha (ate 72 bytes), um sal de 16 bytes e o custo. Os passos sao seis.")
p("Passo 1, preparar a senha: a senha e convertida em bytes UTF-8, recebe um byte nulo no final e e cortada em 72 bytes. O numero 72 vem do tamanho do vetor P: 18 palavras de 4 bytes. Tudo o que passar disso e ignorado.")
p("Passo 2, estado inicial: o vetor P e as quatro S-boxes sao carregados com os digitos de pi.")
p("Passo 3, misturar sal e senha: executa-se a operacao ExpandKey com o sal e a senha. Nela, cada palavra do vetor P recebe um XOR com palavras da chave (a chave e repetida em ciclo ate cobrir as 18 palavras). Depois cifra-se um bloco zerado; o resultado substitui P[0] e P[1]; cifra-se esse resultado para obter P[2] e P[3], e assim por diante, ate reescrever o vetor P e as quatro S-boxes. O sal, dividido em quatro palavras de 32 bits, entra por XOR no bloco antes de cada cifragem. Sao 521 cifragens.")
p("Passo 4, o coracao do algoritmo e onde esta a lentidao: repete-se 2 elevado ao custo vezes duas operacoes, primeiro ExpandKey apenas com a senha e depois ExpandKey apenas com o sal. Como cada cifragem depende do estado ja alterado pela anterior, nao e possivel paralelizar nem pular etapas.")
p("Passo 5, gerar a saida: o texto fixo de 24 bytes 'OrpheanBeholderScryDoubt', que forma 3 blocos de 64 bits, e cifrado 64 vezes com o estado final. O resultado tem 24 bytes, dos quais se descarta o ultimo, ficando 23 bytes.")
p("Passo 6, montar o hash: concatena-se o prefixo com a versao, o custo, o sal em base64 e os 23 bytes em base64, gerando a string de 60 caracteres que e guardada no banco.")
p("Contagem de trabalho: o numero total de cifragens Blowfish e (1 + 2 vezes 2 elevado ao custo) vezes 521, mais 192 das cifragens finais (64 repeticoes de 3 blocos). Com custo 4 sao 17.385 cifragens; com custo 5, 34.057; com custo 12, cerca de 4,3 milhoes.")

h2("6. Exemplo pratico")
p("No exemplo do trabalho, a senha 'senhaeu' e processada com custo 5. A chave tem 8 bytes (a senha mais o byte nulo). O primeiro valor do vetor P comeca em 243F6A88 (digitos de pi), passa a 74F1E7CD depois de misturar sal e senha, e chega a 03CCDF0A depois das 32 repeticoes. Ao final, 64 cifragens do texto fixo produzem os bytes que, em base64, formam o hash. No total sao 34.057 cifragens Blowfish. Trocar uma unica letra da senha muda o hash por completo.")
p("No login, o sistema le o custo e o sal de dentro do hash guardado, refaz o calculo com a senha digitada e compara o resultado com o hash esperado. Nunca ha descriptografia: o sistema apenas recalcula e compara.")

h2("7. Por que o bcrypt e seguro")
p("O bcrypt nao impede o atacante de chutar senhas; ele torna cada palpite caro. O sal unico por senha obriga o atacante a atacar cada usuario separadamente e inutiliza rainbow tables. O custo acompanha a evolucao do hardware. As etapas em sequencia impedem paralelizacao dentro de um unico hash. Alem disso, a verificacao deve comparar o hash calculado com o esperado em tempo constante: em vez de parar no primeiro byte diferente, percorre todos os bytes, para que o tempo de resposta nao revele quantos bytes o atacante acertou, o que seria um ataque de temporizacao (timing attack).")
p("Importante: o bcrypt nao salva uma senha fraca. Senhas como '123456' ou 'password' caem em qualquer dicionario. O bcrypt apenas encarece cada tentativa.")

h2("8. Limitacoes")
p("A primeira limitacao e o limite de 72 bytes: duas senhas que sejam iguais nos primeiros 72 bytes geram o mesmo hash, pois o restante e ignorado. Uma solucao comum e aplicar um pre-hash na senha antes do bcrypt. A segunda e que o byte nulo nao pode aparecer na senha, pois ele e usado como terminador. A terceira e o uso de pouca memoria, cerca de 4 KB fixos. Isso torna o bcrypt mais exposto a ataques com GPUs e circuitos dedicados do que algoritmos que exigem muita memoria. Tambem e importante usar um custo adequado: custos muito baixos, como 6 a 8, sao considerados inseguros hoje.")

h2("9. Comparacao com scrypt e Argon2id")
p("O scrypt, de 2009, e o Argon2id, de 2015 (vencedor da competicao Password Hashing Competition), tambem sao funcoes lentas para senhas, mas exigem quantidades configuraveis de memoria, o que dificulta ataques com GPU e ASIC. No scrypt o custo e configurado por N, r e p; no Argon2id, por tempo, memoria e numero de threads. A OWASP aceita o bcrypt com custo 10 ou mais, o scrypt com N igual a 2 elevado a 17 e o Argon2id com 19 MiB de memoria e 2 iteracoes, e considera o Argon2id a primeira escolha para sistemas novos. O bcrypt continua amplamente usado e suportado em todas as linguagens, em uso desde 1999.")

h2("10. A implementacao da dupla em Python puro")
p("O programa bcrypt_seminario.py implementa o bcrypt do zero, sem nenhum import, ou seja, sem os, hashlib, hmac, time ou qualquer biblioteca. Ele tem cinco blocos. O bloco A calcula os digitos de pi com a formula de Machin. O bloco B implementa o Blowfish: a classe Estado, a funcao F, a cifragem de bloco com 16 rodadas de Feistel e a funcao expandir_chave, que e a operacao central. O bloco C implementa o base64 do bcrypt, com as funcoes de codificar e decodificar. O bloco D gera o sal aleatorio com um gerador pseudoaleatorio simples chamado SplitMix64, semeado com enderecos de memoria; isso serve apenas para demonstracao, pois em producao se usa o gerador criptografico do sistema operacional. O bloco E junta tudo nas funcoes hash_bruto, gerar_hash e verificar_senha.")
p("Para medir o esforco sem a biblioteca time, o programa conta quantas cifragens de bloco foram executadas. A verificacao da senha compara os bytes em tempo constante com um acumulador de XOR. A demonstracao tem tres partes: mostra os seis passos do bcrypt com custo 4; mostra o efeito do sal, com a mesma senha gerando dois hashes diferentes; e demonstra o limite de 72 bytes, em que duas senhas diferentes apos o byte 72 geram o mesmo hash. Depois ha um menu para gerar hash, verificar senha e fazer um ataque de forca bruta em um PIN de dois digitos, que mede quantas cifragens o atacante gasta e projeta o esforco para PINs maiores e para o custo 12. Para conferir a correcao, o hash gerado pelo programa foi validado em um site gerador de bcrypt e vice-versa. Como o Python puro e lento, a demonstracao usa custo 4.")

h2("11. Resumo em dez pontos")
for i, t in enumerate([
    "bcrypt e uma funcao de hash feita para senhas, criada em 1999 por Provos e Mazieres, baseada no Blowfish.",
    "Hash e de mao unica: o login recalcula e compara; nunca descriptografa.",
    "Funcoes rapidas como SHA-256 e MD5 sao ruins para senhas porque permitem bilhoes de palpites por segundo.",
    "O sal tem 16 bytes aleatorios por senha e fica dentro do hash; derrota rainbow tables.",
    "O custo N faz o trabalho se repetir 2 elevado a N vezes; cada +1 dobra o tempo; recomendado 12 ou mais.",
    "O hash tem 60 caracteres: versao, custo, sal de 22 caracteres e hash de 31 caracteres.",
    "O Blowfish usa rede de Feistel de 16 rodadas, vetor P de 18 subchaves e 4 S-boxes inicializados com digitos de pi.",
    "O algoritmo tem 6 passos; o laço de 2 elevado ao custo repeticoes de ExpandKey e onde esta a lentidao.",
    "Limitacoes: senha maxima de 72 bytes, byte nulo proibido, pouca memoria (4 KB) comparado a scrypt e Argon2id.",
    "Senha fraca continua fraca: o bcrypt so encarece cada palpite.",
], 1):
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 5.8, f"{i}. {t}", **L)
    pdf.ln(1)

h2("Referencias")
p("PROVOS, N.; MAZIERES, D. A Future-Adaptable Password Scheme. USENIX Annual Technical Conference, 1999. SCHNEIER, B. Description of a New Variable-Length Key, 64-Bit Block Cipher (Blowfish), 1993. OWASP Password Storage Cheat Sheet. Auth0: Hashing in Action: Understanding bcrypt.")

saida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bcrypt_para_notebooklm.pdf")
pdf.output(saida)
print("PDF gerado em", saida)
