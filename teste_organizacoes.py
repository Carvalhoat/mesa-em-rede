from organizacoes import consultar_organizacoes


oferta = {
    "item": "pão",
    "quantidade": 25,
    "bairro": "Vila Mariana",
    "data_retirada": "2026-11-12",
    "horario_retirada": "09:00-10:00",
}

resultados = consultar_organizacoes(oferta)

esperados = {
    "org_demo_001": True,
    "org_demo_002": False,
    "org_demo_003": False,
}

assert {r["id"] for r in resultados} == set(esperados)

for resultado in resultados:
    assert resultado["compativel"] == esperados[resultado["id"]]

    print(f"\n{resultado['nome']}")
    print(
        "Situação:",
        "COMPATÍVEL" if resultado["compativel"] else "INCOMPATÍVEL",
    )

    for motivo in resultado["motivos"]:
        print(f"  + {motivo}")

    for impedimento in resultado["impedimentos"]:
        print(f"  - {impedimento}")

print("\nConsulta inicial: 3/3 classificações corretas.")

