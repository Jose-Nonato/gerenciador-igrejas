# Gerenciador de Igrejas

Sistema para gestão de igrejas (rol de membros, famílias, histórico eclesiástico e acesso por perfil).
Backend em `back/` (FastAPI + PostgreSQL) e frontend em `front/` (React + TypeScript + Vite).

## Backend

### Requisitos
- Python 3.14
- PostgreSQL acessível (o driver é o `pg8000`)

### Instalação
```bash
cd back
python -m venv .venv
.venv/Scripts/activate          # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
```

`requirements.txt` lista as dependências diretas; `requirements.lock.txt` guarda o
`pip freeze` completo do ambiente de desenvolvimento, para reproduzir versões exatas.

### Configuração (`back/.env`, nunca versionado)
| Variável | Obrigatória | Descrição |
|---|---|---|
| `DATABASE_URL` | sim | ex.: `postgresql+pg8000://usuario:senha@localhost:5432/gerenciador` |
| `AUTO_MIGRATE` | não | padrão `true`: aplica as migrações ao iniciar a API |
| `JWT_SECRET` | sim | segredo longo e aleatório |
| `JWT_ALGORITHM` | não | padrão `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | não | padrão 15 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | não | padrão 7 |
| `MAX_TENTATIVAS_LOGIN` | não | padrão 5 |
| `RESET_TOKEN_EXPIRE_HOURS` | não | padrão 24 |
| `FRONTEND_URL` | não | padrão `http://localhost:3000`; usada nos links de e-mail e como origem CORS |
| `CORS_ORIGINS` | não | origens extras permitidas, separadas por vírgula |
| `UPLOAD_DIR` | não | pasta das imagens dos comunicados, padrão `uploads` (relativa a `back/`; ignorada pelo git) |
| `MAX_IMAGEM_MB` | não | tamanho máximo de cada imagem, padrão 5 |
| `FUSO_HORARIO` | não | fuso do relógio da igreja para a agenda de conversas, padrão `America/Sao_Paulo` |
| `ATENDIMENTO_ANTECEDENCIA_HORAS` | não | antecedência mínima para pedir uma conversa, padrão 24 |
| `ATENDIMENTO_HORIZONTE_DIAS` | não | até quantos dias à frente se pode marcar, padrão 60 |
| `ATENDIMENTO_CANCELAMENTO_HORAS` | não | prazo mínimo para o membro cancelar uma conversa confirmada, padrão 12 |
| `ATENDIMENTO_MAX_PENDENTES` | não | pedidos aguardando resposta por membro, padrão 2 |
| `ATENDIMENTO_LEMBRETE_HORAS` | não | quantas horas antes da conversa sai o lembrete por e-mail, padrão 3 |
| `AGENDADOR_ATIVO` | não | padrão `true`: a API envia os lembretes das conversas sozinha; `false` para usar o script à parte |
| `AGENDADOR_INTERVALO_SEGUNDOS` | não | de quanto em quanto tempo o agendador roda, padrão 900 |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | não | sem `SMTP_HOST` os e-mails só são registrados no log |

### Banco de dados
O schema é gerenciado pelo Alembic. **Ao iniciar, a API aplica as migrações pendentes sozinha**
(`alembic upgrade head`), então basta subir o backend. Se a migração falhar, a API não sobe.

- Vários processos subindo juntos são seguros: um lock do Postgres faz um migrar por vez.
- Para desligar (ex.: migrar num passo de deploy à parte), defina `AUTO_MIGRATE=false` no `.env`.
- Rodar à mão continua funcionando: `cd back && alembic upgrade head`.
- Só migra para frente. Reverter (`alembic downgrade`) é sempre manual.

### Primeira igreja e administrador
```bash
cd back
python -m scripts.criar_igreja --nome "Igreja Presbiteriana X" --email admin@exemplo.com
```
A senha é pedida no terminal.

### Executar
```bash
cd back
uvicorn main:app --reload
```
Documentação interativa em `http://localhost:8000/docs`.

### Agenda de conversas e agendador embutido
Os e-mails de pedido, confirmação, recusa, remarcação e cancelamento saem na hora. O **lembrete**
de uma conversa confirmada (para o membro e para o oficial) sai pelo **agendador embutido na API**:
ao subir, a API passa a rodar a tarefa sozinha a cada `AGENDADOR_INTERVALO_SEGUNDOS` (padrão 900, ou
15 minutos), sem cron nem serviço à parte. Cada conversa é lembrada uma só vez, então vários
processos da API juntos não duplicam o e-mail.

Quem prefere agendar por fora (cron, Agendador de Tarefas do Windows) desliga o embutido com
`AGENDADOR_ATIVO=false` e roda, a partir de `back/`:
```bash
python -m scripts.enviar_lembretes
```
Os e-mails não levam o assunto da conversa, que é sigiloso. Sem `SMTP_HOST` eles só vão para o log.

### Testes
```bash
cd back
pytest
```
Os testes usam um banco próprio, `<banco>_test`, que é **recriado a cada execução**
(o banco de desenvolvimento não é tocado). O usuário do `DATABASE_URL` precisa poder criar bancos.

## Frontend
```bash
cd front
npm install
npm run dev      # http://localhost:3000
```
Veja [front/README.md](front/README.md). O backend precisa estar rodando em `http://localhost:8000` (ou ajuste `VITE_API_URL`).

## Arquitetura do backend
`views` (rotas) → `controllers` (regras de negócio) → `repositories` (acesso a dados),
com `models` (SQLAlchemy), `schemas` (Pydantic) e `core` (config, segurança, e-mail, middleware).
Todos os dados são isolados por igreja (`igreja_id`), e ações sensíveis vão para `log_auditoria`.

## Licença
Ver [LICENSE](LICENSE).
