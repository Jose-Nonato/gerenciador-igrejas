from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    # Aplica `alembic upgrade head` ao iniciar a API. Desligue se as migrações rodam
    # em outra etapa (ex.: um passo de deploy) ou se o usuário do banco não pode alterar o schema.
    AUTO_MIGRATE: bool = True
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Segurança de senha
    MAX_TENTATIVAS_LOGIN: int = 5
    RESET_TOKEN_EXPIRE_HOURS: int = 24

    # Imagens enviadas (por enquanto em disco local, para testes). Caminho relativo é
    # resolvido a partir da pasta `back/`.
    UPLOAD_DIR: str = "uploads"
    MAX_IMAGEM_MB: int = 5

    # Agendamento de conversas com pastor e presbíteros. Os horários dos oficiais são do
    # relógio da igreja; no banco tudo fica em UTC.
    FUSO_HORARIO: str = "America/Sao_Paulo"
    ATENDIMENTO_ANTECEDENCIA_HORAS: int = 24
    ATENDIMENTO_HORIZONTE_DIAS: int = 60
    ATENDIMENTO_CANCELAMENTO_HORAS: int = 12
    ATENDIMENTO_MAX_PENDENTES: int = 2
    # Quantas horas antes da conversa o lembrete por e-mail é enviado
    ATENDIMENTO_LEMBRETE_HORAS: int = 3

    # Agendador embutido na API (hoje: lembretes por e-mail das conversas). Desligue se preferir
    # rodar `python -m scripts.enviar_lembretes` fora da API, ou em testes.
    AGENDADOR_ATIVO: bool = True
    AGENDADOR_INTERVALO_SEGUNDOS: float = 900

    # Links enviados por e-mail (convite e redefinição de senha)
    FRONTEND_URL: str = "http://localhost:3000"

    # Origens autorizadas a chamar a API pelo navegador, separadas por vírgula.
    # Vazio = só FRONTEND_URL.
    CORS_ORIGINS: str = ""

    @property
    def cors_origins(self) -> list[str]:
        extras = [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return list(dict.fromkeys([self.FRONTEND_URL.rstrip("/"), *extras]))

    # Sem SMTP_HOST os e-mails só são registrados no log (desenvolvimento)
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = "no-reply@gerenciador-igrejas.local"


settings = Settings()
