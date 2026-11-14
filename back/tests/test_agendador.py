import asyncio
import time

from fastapi.testclient import TestClient

from core.agendador import Agendador


def test_roda_repetidamente_e_sobrevive_a_falha():
    chamadas = []

    def tarefa():
        chamadas.append(1)
        if len(chamadas) == 1:
            raise RuntimeError("falha na primeira rodada")

    async def cenario():
        agendador = Agendador("teste", tarefa, intervalo_segundos=0.02, atraso_inicial_segundos=0)
        agendador.iniciar()
        agendador.iniciar()  # ligar duas vezes não cria dois laços
        await asyncio.sleep(0.3)
        await agendador.parar()
        parou_em = len(chamadas)
        await asyncio.sleep(0.1)
        return parou_em, len(chamadas)

    parou_em, depois = asyncio.run(cenario())
    assert parou_em >= 3  # a falha da primeira rodada não matou o laço
    assert depois == parou_em  # depois de parar, nada mais roda


def test_parar_sem_ter_iniciado():
    asyncio.run(Agendador("teste", lambda: None, 1).parar())


def test_api_liga_o_agendador_quando_ativo(monkeypatch):
    import main

    chamadas = []
    monkeypatch.setattr(main, "enviar_lembretes", lambda: chamadas.append(1) or 0)
    monkeypatch.setattr(main.settings, "AGENDADOR_ATIVO", True)
    monkeypatch.setattr(main.settings, "AGENDADOR_INTERVALO_SEGUNDOS", 0.02)

    with TestClient(main.app):
        time.sleep(0.3)
    assert len(chamadas) >= 2

    # ao desligar a API o agendador para
    total = len(chamadas)
    time.sleep(0.1)
    assert len(chamadas) == total


def test_api_nao_liga_o_agendador_quando_desligado(monkeypatch):
    import main

    chamadas = []
    monkeypatch.setattr(main, "enviar_lembretes", lambda: chamadas.append(1) or 0)
    monkeypatch.setattr(main.settings, "AGENDADOR_ATIVO", False)
    monkeypatch.setattr(main.settings, "AGENDADOR_INTERVALO_SEGUNDOS", 0.02)

    with TestClient(main.app):
        time.sleep(0.2)
    assert chamadas == []
