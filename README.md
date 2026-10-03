# Seminário #01 – Tema 09: bcrypt

**Versão final da apresentação:** `bcrypt_seminario.py` + `docs/bcrypt_slides_seminario.pdf` (9 slides). Divisão da fala e guia de estudo: `docs/guia_apresentacao_estudo.pdf`.

Isabela Sousa & Paulo Victor Almeida

bcrypt implementado **do zero em Python, sem nenhum `import`** (nem `os`, `hmac`, `hashlib` ou `time`).

## Como rodar

```bash
python bcrypt_seminario.py
```

Roda 6 partes de demonstração e abre um menu interativo (hash ao vivo, verificação, ataque de dicionário, limite de 72 bytes).

| Parte | Conteúdo |
|---|---|
| 1 | Blowfish e dígitos de π (calculados no código) |
| 2 | bcrypt passo a passo (custo 4) |
| 3 | Vetores de teste oficiais |
| 4 | Efeito do sal e do custo (cada +1 dobra o esforço) |
| 5 | Cadastro, login e ataque de dicionário |
| 6 | Limite de 72 bytes, byte nulo e comparação com scrypt/Argon2 |

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `bcrypt_completo.py` | **O trabalho** (arquivo único, sem imports) |
| `teste_contra_biblioteca.py` | Teste extra: compara com a lib oficial `bcrypt` (única que usa import) |
| `docs/slides_bcrypt.pdf` | Slides da apresentação (14) |
| `docs/infografico_bcrypt.pdf` | Infográfico "bcrypt por dentro" |
| `docs/resumo_bcrypt.pdf` | Resumo, roteiro da dupla, perguntas e respostas |
| `docs/*.html`, `docs/gerar_pdf.py` | Fontes dos PDFs |

## Algoritmo

1. Senha → UTF-8 + `\0`, truncada em 72 bytes
2. Estado Blowfish ← dígitos de π
3. `ExpandKey(sal, senha)`
4. Repetir 2^custo vezes: `ExpandKey(senha)` e `ExpandKey(sal)`
5. Cifrar 64× `OrpheanBeholderScryDoubt`
6. Saída: `$2b$CC$` + base64(sal, 22) + base64(hash, 31)

## Referências

- Provos & Mazières, *A Future-Adaptable Password Scheme* (USENIX 1999)
- Schneier, *Blowfish* (1993/94)
