"""Envia por e-mail o lembrete das conversas confirmadas que estão perto de começar.

A API já faz isso sozinha, de tempos em tempos (veja AGENDADOR_ATIVO no README). Este script é
para quem prefere rodar fora da API, com cron ou o Agendador de Tarefas, e desliga o agendador
embutido (AGENDADOR_ATIVO=false):

    python -m scripts.enviar_lembretes   (a partir de back/)

Cada conversa é lembrada uma única vez, ATENDIMENTO_LEMBRETE_HORAS horas antes (padrão 3), então
rodar mais de uma vez no intervalo é seguro. Sem SMTP_HOST os e-mails só vão para o log.
"""

from controllers import AtendimentoController
from core.database import SessionLocal
from core.mailer import get_mailer
from repositories import AtendimentoRepository, AuditoriaRepository, MembroRepository


def executar() -> int:
    """Uma rodada de lembretes. Devolve quantas conversas foram lembradas."""
    with SessionLocal() as db:
        controller = AtendimentoController(
            AtendimentoRepository(db),
            MembroRepository(db),
            AuditoriaRepository(db),
            db,
            get_mailer(),
        )
        return controller.enviar_lembretes()


def main() -> int:
    print(f"{executar()} conversa(s) lembrada(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
