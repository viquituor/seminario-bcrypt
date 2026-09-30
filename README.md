# Seminário #01 – Tema 09: bcrypt

Implementação do **bcrypt do zero** (sem bibliotecas de criptografia), em Python, com nomes de funções e variáveis em português.

## Estrutura

| Arquivo | Conteúdo |
|---|---|
| `bcrypt_do_zero/constantes.py` | Calcula os dígitos de π que inicializam o Blowfish (vetor P e caixas S) |
| `bcrypt_do_zero/blowfish.py` | Cifra Blowfish (Feistel, 16 rodadas), `expandir_chave` e `expansao_custosa` (Eksblowfish) |
| `bcrypt_do_zero/bcrypt.py` | `gerar_hash`, `verificar_senha`, base64 do bcrypt |
| `main.py` | Demo interativa com o passo a passo |
| `testes.py` | Compara com a biblioteca oficial (usada só como gabarito) |
| `docs/resumo_bcrypt.pdf` | Resumo do tema + roteiro de apresentação para a dupla |

## Como rodar

```bash
python main.py          # menu interativo (sem dependências)
pip install bcrypt      # apenas para os testes
python testes.py
```

## Passos do algoritmo

1. Senha → UTF-8 + `\0`, truncada em 72 bytes.
2. Estado Blowfish ← dígitos de π (P: 18 palavras; S: 4×256 palavras).
3. `ExpandKey(sal, senha)`.
4. Repetir **2^custo** vezes: `ExpandKey(senha)` e `ExpandKey(sal)`.
5. Cifrar 64× o texto `OrpheanBeholderScryDoubt` (3 blocos de 64 bits).
6. Saída: `$2b$CC$` + base64(sal, 22 chars) + base64(hash, 31 chars).

## Referências

- Provos & Mazières, *A Future-Adaptable Password Scheme* (USENIX 1999)
- Schneier, *Description of a New Variable-Length Key, 64-Bit Block Cipher (Blowfish)* (1993)
