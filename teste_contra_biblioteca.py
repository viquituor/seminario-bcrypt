"""
Teste EXTRA (fora do trabalho): compara bcrypt_completo.py com a biblioteca
oficial `bcrypt` em varios casos. Os imports ficam so aqui; o trabalho
(bcrypt_completo.py) continua sem nenhum import.

    pip install bcrypt
    python teste_contra_biblioteca.py
"""
import bcrypt as gabarito

from bcrypt_completo import decodificar_base64, gerar_hash, verificar_senha

casos = [("abc", 4), ("", 4), ("senha123", 5), ("Sen@ha_Forte!2024", 6),
         ("a" * 100, 4), ("acentuação-ção", 4), ("x" * 72, 4), ("x" * 71, 4)]
for senha, custo in casos:
    sal_texto = gabarito.gensalt(rounds=custo)
    esperado = gabarito.hashpw(senha.encode(), sal_texto).decode()
    sal = decodificar_base64(sal_texto.decode().split("$")[3], 16)
    obtido = gerar_hash(senha, custo, sal)
    assert obtido == esperado, (senha, obtido, esperado)
    assert verificar_senha(senha, esperado)
    assert not verificar_senha(senha + "!", esperado) or len(senha.encode()) >= 72
print(f"OK: {len(casos)} hashes identicos aos da biblioteca oficial")
