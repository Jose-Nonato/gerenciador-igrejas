"""Agendador embutido na API: roda uma tarefa de tempos em tempos, sem cron nem serviço à parte.

Serve às rotinas que precisam de relógio e não de uma requisição (hoje, o lembrete por e-mail das
conversas confirmadas). A tarefa roda numa thread, para não travar o atendimento das requisições,
e uma falha nunca derruba o laço: é registrada no log e a próxima rodada tenta de novo.

Vários processos da API (workers, réplicas) podem ter cada um o seu agendador: as tarefas precisam
ser idempotentes. O lembrete é: trava a linha e marca o envio.
"""

import asyncio
import contextlib
import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class Agendador:
    def __init__(
        self,
        nome: str,
        tarefa: Callable[[], object],
        intervalo_segundos: float,
        atraso_inicial_segundos: float = 30,
    ) -> None:
        self.nome = nome
        self.tarefa = tarefa
        self.intervalo = intervalo_segundos
        self.atraso_inicial = atraso_inicial_segundos
        self._laco_task: asyncio.Task | None = None

    async def _laco(self) -> None:
        # Espera um pouco antes da primeira rodada: a API termina de subir (e migrar) primeiro
        await asyncio.sleep(self.atraso_inicial)
        while True:
            try:
                resultado = await asyncio.to_thread(self.tarefa)
                logger.info("Agendador '%s': rodada concluída (%s)", self.nome, resultado)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Agendador '%s': a rodada falhou; tentará de novo", self.nome)
            await asyncio.sleep(self.intervalo)

    def iniciar(self) -> None:
        if self._laco_task is None:
            self._laco_task = asyncio.create_task(self._laco(), name=f"agendador-{self.nome}")
            logger.info("Agendador '%s' ligado (a cada %s s)", self.nome, self.intervalo)

    async def parar(self) -> None:
        if self._laco_task is None:
            return
        self._laco_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._laco_task
        self._laco_task = None
