"""
Testes: compara a nossa implementacao com a biblioteca oficial `bcrypt`.
A biblioteca e usada SOMENTE aqui, como "gabarito". O codigo do trabalho
(pasta bcrypt_do_zero/) nao importa nenhuma biblioteca de criptografia.

Uso:  pip install bcrypt   (so para os testes)
      python testes.py
"""

import os

from bcrypt_do_zero import gerar_hash, verificar_senha
from bcrypt_do_zero.bcrypt import codificar_base64, decodificar_base64
from bcrypt_do_zero.constantes import P_INICIAL, S_INICIAL

try:
    import bcrypt as gabarito
except ImportError:
    gabarito = None


def teste_constantes_pi():
    # Valores publicados no paper do Blowfish
    assert P_INICIAL[0] == 0x243F6A88 and P_INICIAL[1] == 0x85A308D3
    assert P_INICIAL[17] == 0x8979FB1B
    assert S_INICIAL[0][0] == 0xD1310BA6 and S_INICIAL[3][255] == 0x3AC372E6
    print("OK  constantes de PI (P e S) batem com o paper do Blowfish")


def teste_base64():
    for n in (1, 2, 3, 15, 16, 23):
        dados = os.urandom(n)
        assert decodificar_base64(codificar_base64(dados), n) == dados
    print("OK  base64 do bcrypt (ida e volta)")


def teste_contra_biblioteca():
    if gabarito is None:
        print("--  biblioteca bcrypt nao instalada: pulando comparacao")
        return
    casos = [("abc", 4), ("", 4), ("senha123", 5), ("Sen@ha_Forte!2024", 6),
             ("a" * 100, 4), ("acentuação-ção", 4)]
    for senha, custo in casos:
        sal_texto = gabarito.gensalt(rounds=custo)
        esperado = gabarito.hashpw(senha.encode(), sal_texto)
        # extrai o sal (22 chars) do gabarito e usa no nosso
        sal = decodificar_base64(sal_texto.decode().split("$")[3], 16)
        obtido = gerar_hash(senha, custo, sal)
        assert obtido == esperado.decode(), (senha, obtido, esperado)
    print(f"OK  {len(casos)} hashes IDENTICOS aos da biblioteca oficial")


def teste_verificacao():
    h = gerar_hash("minhaSenha", 4)
    assert verificar_senha("minhaSenha", h)
    assert not verificar_senha("minhasenha", h)
    if gabarito is not None:
        assert verificar_senha("x", gabarito.hashpw(b"x", gabarito.gensalt(4)).decode())
    print("OK  verificacao de senha (certa, errada e hash da biblioteca)")


def teste_sal_diferente():
    assert gerar_hash("igual", 4) != gerar_hash("igual", 4)
    print("OK  mesma senha + sais diferentes = hashes diferentes")


if __name__ == "__main__":
    teste_constantes_pi()
    teste_base64()
    teste_contra_biblioteca()
    teste_verificacao()
    teste_sal_diferente()
    print("\nTodos os testes passaram.")
