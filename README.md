# NailFlows API

API FastAPI para cadastro de clientes, serviços e agendamentos de Nail Designers.
A aplicação pode usar memória para desenvolvimento ou Supabase para persistência.
A integração com Google Calendar pode ser simulada ou real, com uma agenda por
instalação do backend.

## Requisitos

- Python 3.10 a 3.13
- Um ambiente virtual Python
- Supabase, quando a persistência real for necessária
- Google Cloud OAuth, somente quando `CALENDAR_BACKEND=google`

## Instalação local

```bash
git clone <repository-url>
cd "AUTOMATIZE - NailFlows"
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate       # Windows PowerShell
python -m pip install -r requirements.txt
cp .env.example .env
```

No PowerShell, copie o modelo com `Copy-Item .env.example .env`.
Nunca versione `.env`; ele está protegido pelo `.gitignore`.

## Variáveis de ambiente

A aplicação carrega `.env` da raiz do projeto durante a inicialização local.
Em hospedagem, configure as variáveis no painel da plataforma; o arquivo `.env`
não é enviado ao repositório.

### Backend e Supabase

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SECRET_KEY=sb_secret_...
ADMIN_API_TOKEN=gere_um_token_longo_e_aleatorio
FRONTEND_URL=http://localhost:3000
```

`SUPABASE_SECRET_KEY` é a chave usada pelo backend para a API REST do Supabase.
O nome legado `SUPABASE_KEY` também é aceito, mas não deve ser usado em novas
instalações. `SUPABASE_URL` e `SUPABASE_SECRET_KEY` precisam ser configuradas
juntas; quando ambas estão vazias, a aplicação usa memória. Configuração parcial
interrompe a inicialização para evitar um fallback acidental.

Gere o token administrativo com:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

As variáveis `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_JWKS_URL`, `host`, `port`,
`database` e `user` não são usadas pelo código atual para acessar o banco.

### Google Calendar

Use o modo simulado localmente quando não precisar do Google:

```env
CALENDAR_BACKEND=mock
```

Para a integração real:

```env
CALENDAR_BACKEND=google
GOOGLE_CLIENT_ID=seu-client-id
GOOGLE_CLIENT_SECRET=seu-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
GOOGLE_CALENDAR_ID=primary
GOOGLE_TOKEN_ENCRYPTION_KEY=chave-Fernet-estavel
GOOGLE_TOKEN_FILE=.secrets/google-token.enc
```

Gere `GOOGLE_TOKEN_ENCRYPTION_KEY` com:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Não altere essa chave depois de autorizar a agenda. O token OAuth é salvo
criptografado em `GOOGLE_TOKEN_FILE`. Se o arquivo for perdido ou a chave mudar,
é necessário autorizar novamente em `/auth/google/connect`.

## Supabase

Para uma instalação nova em desenvolvimento, execute
[`app/infrastructure/database/init.sql`](app/infrastructure/database/init.sql)
inteiro no SQL Editor do Supabase. Esse arquivo remove e recria as tabelas, por
isso não deve ser executado em produção com dados existentes.

Para um banco existente, execute as migrations em ordem:

1. `001_create_clients.sql`
2. `002_create_appointments.sql`
3. `003_create_services.sql`
4. `004_create_registration_links.sql`
5. `005_unique_client_contacts.sql`

As migrations antigas usam `CREATE TABLE IF NOT EXISTS`, que não adiciona colunas
em tabelas já existentes. Confirme a estrutura de produção, principalmente após
a normalização de serviços e agendamentos:

```sql
select table_name, column_name, data_type
from information_schema.columns
where table_schema = 'public'
  and table_name in ('clients', 'services', 'appointments', 'registration_links')
order by table_name, ordinal_position;
```

Em uma tabela `appointments` antiga, a coluna de status pode precisar ser criada:

```sql
alter table public.appointments
add column if not exists active boolean not null default true;

grant select, insert, update, delete
on public.appointments
to service_role;

notify pgrst, 'reload schema';
```

O backend usa a chave secreta do Supabase para acessar as tabelas protegidas por
RLS. As migrations concedem as permissões ao papel `service_role`.

## Executar a API

Para executar a aplicação com o gate de testes:

```bash
python scripts/start.py
```

O comando executa toda a suíte antes de iniciar o Uvicorn. Se algum teste falhar,
o processo termina e a API não é disponibilizada. Localmente, a API fica em
`http://127.0.0.1:8000` e o Swagger em `http://127.0.0.1:8000/docs`.

Para iniciar somente o servidor, sem o gate, use `python main.py` apenas para
diagnóstico local. Em produção, não use esse caminho.

No Render, configure `PYTHON_VERSION=3.13.5` ou outra versão 3.13 disponível
na plataforma. Para Render ou outra plataforma que forneça a variável `PORT`, use:

```bash
python scripts/start.py
```

Configure também `SUPABASE_URL`, `SUPABASE_SECRET_KEY` e `ADMIN_API_TOKEN` no
painel da hospedagem. Não dependa de um `.env` local no servidor.

## Deploy no Render

Variáveis mínimas para persistência e autenticação:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SECRET_KEY=sb_secret_...
ADMIN_API_TOKEN=seu-token-administrativo
CALENDAR_BACKEND=mock
```

Para Google Calendar em produção:

```env
CALENDAR_BACKEND=google
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://seu-servico.onrender.com/auth/google/callback
GOOGLE_CALENDAR_ID=primary
GOOGLE_TOKEN_ENCRYPTION_KEY=chave-fixa
GOOGLE_TOKEN_FILE=/var/data/google-token.enc
```

O `GOOGLE_REDIRECT_URI` precisa ser exatamente igual ao URI autorizado no Google
Cloud, incluindo protocolo, domínio, caminho e ausência/presença de barra final.
O arquivo de token precisa ficar em armazenamento persistente; caso contrário,
um restart ou novo deploy pode exigir nova autorização.

Após alterar variáveis, faça um novo deploy/restart. Autorize a agenda pelo mesmo
domínio publicado, usando `/docs` com o token administrativo e executando
`GET /auth/google/connect`. O callback OAuth é público, mas valida o estado e o
cookie criado no início do fluxo.

## Autenticação administrativa

As rotas administrativas exigem:

```http
Authorization: Bearer SEU_ADMIN_API_TOKEN
```

No Swagger, clique em **Authorize → AdminToken** e informe somente o token, sem
escrever `Bearer`.

Rotas protegidas:

- `/clientes/*`
- `/agendamentos/*`
- `/servicos/*`, exceto `/servicos/keepalive`
- `POST /registration-links`
- `GET /auth/google/connect`

Sem `ADMIN_API_TOKEN`, as rotas retornam `503`. Sem header ou com token incorreto,
retornam `401`. Nunca coloque o token na URL, em links de convite ou no frontend
público.

## Endpoints

### Clientes

| Método | Rota | Descrição |
| --- | --- | --- |
| `POST` | `/clientes/` | Cadastra uma cliente |
| `GET` | `/clientes/` | Lista clientes |
| `GET` | `/clientes/{id}` | Consulta uma cliente |
| `PATCH` | `/clientes/{id}` | Atualiza parcialmente uma cliente |
| `DELETE` | `/clientes/{id}` | Exclui uma cliente |

Exemplo:

```json
{
  "name": "Maria Silva",
  "email": "maria@example.com",
  "phone": "+55 11 99999-9999"
}
```

E-mail e telefone duplicados retornam `409`. Dados inválidos retornam `422`.
Atualizações parciais preservam os campos omitidos. Dados são mantidos no Supabase
quando ele está configurado; no modo memória, são perdidos ao reiniciar.

### Serviços

| Método | Rota | Descrição |
| --- | --- | --- |
| `POST` | `/servicos/` | Cria um serviço |
| `GET` | `/servicos/` | Lista serviços; aceita `active_only=true` |
| `GET` | `/servicos/{id}` | Consulta um serviço |
| `PATCH` | `/servicos/{id}` | Atualiza nome, duração ou `active` |
| `DELETE` | `/servicos/{id}` | Inativa o serviço (`active=false`) |
| `GET` | `/servicos/keepalive` | Consulta a tabela de serviços e retorna a quantidade |

Para ativar ou inativar manualmente:

```json
{"active": false}
```

O keepalive é público, não exige token e consulta o Supabase. Uma resposta
`503` indica falha de configuração ou acesso ao banco.

### Agendamentos

| Método | Rota | Descrição |
| --- | --- | --- |
| `POST` | `/agendamentos/` | Cria um agendamento |
| `GET` | `/agendamentos/` | Lista agendamentos |
| `GET` | `/agendamentos/{id}` | Consulta um agendamento |
| `PATCH` | `/agendamentos/{id}` | Atualiza um agendamento |
| `DELETE` | `/agendamentos/{id}` | Cancela logicamente um agendamento |
| `POST` | `/agendamentos/{id}/sincronizar` | Sincroniza o status no Google |

Corpo de criação/atualização:

```json
{
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "service_id": "650e8400-e29b-41d4-a716-446655440000",
  "start_time": "2026-11-10T14:00:00",
  "duration_minutes": 120
}
```

`client_id` e `service_id` precisam existir. Se `duration_minutes` for omitido,
a duração do serviço será usada. Serviços inativos não podem ser usados em novos
agendamentos. Datas passadas e horários sobrepostos retornam `400`.

O `DELETE` é soft delete: não remove a linha e grava `active=false`. Quando o
agendamento possui evento Google, o evento é excluído antes da atualização do
Supabase. Se o Google não estiver autorizado ou falhar, a API retorna `503` e o
agendamento pode permanecer ativo; nesse caso, corrija o OAuth e tente novamente.

Para filtrar apenas ativos:

```text
GET /agendamentos/?active_only=true
```

Datas sem fuso são interpretadas como horário de `America/Sao_Paulo` e convertidas
para UTC. `end_time` é calculado pela aplicação e não é uma coluna do banco.

### Cadastro por convite

| Método | Rota | Autenticação | Descrição |
| --- | --- | --- | --- |
| `POST` | `/registration-links` | Admin | Gera convite |
| `GET` | `/registration-links/{token}` | Pública | Valida convite |
| `POST` | `/registration-links/{token}/register` | Pública | Cadastra cliente |

Convites expiram em seis horas, são de uso único e armazenam somente o hash do
token. Links inválidos, expirados ou usados retornam `410`.

### Google Calendar

| Método | Rota | Autenticação | Descrição |
| --- | --- | --- | --- |
| `GET` | `/auth/google/connect` | Admin | Inicia OAuth |
| `GET` | `/auth/google/callback` | Pública | Finaliza OAuth |

O callback não deve ser aberto isoladamente. O fluxo deve começar em
`/auth/google/connect` para que o estado e o cookie sejam criados.

## Keepalive

Para manter o serviço ativo e verificar o acesso ao Supabase, configure um cron
para chamar:

```text
https://seu-servico.onrender.com/servicos/keepalive
```

Use método `GET` e não envie `Authorization`. A rota consulta `services` e retorna
`{"status":"ok","services":N}`. Não use `/agendamentos/` como keepalive, pois
essa rota é protegida e exige token administrativo.

## Logs e diagnóstico

Os logs usam o logger `nailflows` e são enviados para stdout, portanto aparecem
nos logs do Render. O cancelamento de agendamentos registra fases específicas:

- `phase=database_read`
- `phase=google_delete`
- `phase=database_update`
- `phase=completed`

Falhas OAuth registram `phase=credentials_load`, tipo da exceção e caminho do
arquivo de token, sem registrar tokens ou segredos. A mensagem HTTP de falha do
Google é separada de falhas do Supabase.

## Testes

```bash
python -m unittest discover -s tests -v
```

O comando `python scripts/start.py` executa exatamente essa suíte antes de cada
inicialização. Durante os testes, `PYTHON_DOTENV_DISABLED=1` impede que o `.env`
local ou as credenciais de produção sejam carregados. Os testes usam memória e
chamadas HTTP simuladas; não devem acessar Supabase ou Google reais.

Para executar uma família específica:

```bash
python -m unittest discover -s tests -p 'test_registration*.py' -v
```

## Segurança

- Não versione `.env`, tokens Google ou arquivos em `.secrets`.
- Use HTTPS em produção.
- Mantenha `ADMIN_API_TOKEN` somente no backend ou em um serviço confiável de cron.
- Não registre headers `Authorization` nem códigos OAuth.
- Troque imediatamente qualquer token que tenha sido exposto em logs, terminal ou chat.
- Use uma única instância/worker quando o fluxo OAuth e o arquivo de token estiverem
  armazenados localmente.

## Estrutura

- `app/api`: rotas FastAPI e autenticação.
- `app/domain`: modelos e regras de domínio.
- `app/services`: regras de negócio.
- `app/infrastructure/database`: memória, Supabase e SQL.
- `app/infrastructure/calendar`: Google Calendar real ou mock.
- `tests`: testes unitários e de integração simulada.
