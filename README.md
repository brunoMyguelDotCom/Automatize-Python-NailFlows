# NailFlows API

API para Nail Designers cadastrarem clientes e gerenciarem agendamentos. Clientes e agendamentos podem ser armazenados em memória ou no Supabase. A integração com Google Agenda pode ser simulada ou real (OAuth, uma conta por instalação).

## Primeiros Passos

### Pré-requisitos
- Python 3.9+
- Ferramenta de ambiente virtual (`venv` ou `conda`)

### Instalacao e Configuracao

1. **Clonar o repositório:**
   ```bash
   git clone <repository-url>
   cd "AUTOMATIZE - NailFlows"
   ```

2. **Criar e ativar o ambiente virtual:**
   ```bash
   # Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate

   # Windows
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Instalar as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configuração do Ambiente:**
   O arquivo [`.env.example`](.env.example) contém o modelo das variáveis. Se ainda não tiver um `.env`, copie o modelo:
   ```bash
   cp .env.example .env
   ```
   No PowerShell, use `Copy-Item .env.example .env`. Se já existir um `.env`, mantenha os valores atuais e adicione apenas os campos ausentes do modelo.

   Preencha `SUPABASE_URL` e `SUPABASE_SECRET_KEY` com os valores reais no `.env`. O nome legado `SUPABASE_KEY` também é aceito; `SUPABASE_SECRET_KEY` tem prioridade. Configuração parcial gera erro para evitar uso acidental do banco em memória. Para executar em memória, deixe essas duas variáveis vazias.

   Sem configuração, a API utiliza armazenamento em memória para desenvolvimento. Para usar o Supabase, configure as variáveis abaixo. Prepare as tabelas conforme as instruções abaixo antes de usar o cadastro de clientes:
   ```env
   # Configuração do Supabase
   SUPABASE_URL=seu_url_do_supabase_aqui
   SUPABASE_SECRET_KEY=sua_chave_secreta_do_backend_aqui

   # URL do frontend usada nos links de autocadastro
   FRONTEND_URL=http://localhost:3000

   # Configuração OAuth do Google Agenda
   GOOGLE_CLIENT_ID=seu_google_client_id
   GOOGLE_CLIENT_SECRET=seu_google_client_secret
   ```

   No PowerShell, antes de iniciar a API:
   ```powershell
   $env:SUPABASE_URL = "https://seu-projeto.supabase.co"
   $env:SUPABASE_SECRET_KEY = "sua_chave_secreta_do_backend_aqui"
   ```

   Você também pode criar um arquivo `.env` na raiz do projeto com essas variáveis. A aplicação carrega esse arquivo automaticamente, independentemente do diretório de execução, sem sobrescrever variáveis já definidas no ambiente do processo. Mantenha o arquivo fora do controle de versão. A tabela de clientes usa RLS e acesso pelo backend com uma chave secreta (`sb_secret_...`) ou a chave legada `service_role`. A chave permanece no backend. Consulte a [documentação de chaves do Supabase](https://supabase.com/docs/guides/api/api-keys).

### Executando a Aplicacao

O backend disponibiliza `POST /registration-links` para gerar um convite,
`GET /registration-links/{token}` para validá-lo e
`POST /registration-links/{token}/register` para cadastrar a cliente.
Configure `FRONTEND_URL` com a URL pública do frontend; o padrão de desenvolvimento
é `http://localhost:3000`. O link gerado aponta para `/cadastro/{token}` nesse frontend.
A página de cadastro ainda precisa ser implementada. Com as credenciais do
Supabase configuradas, os convites são salvos em `public.registration_links` e
o cadastro chama `POST /rest/v1/rpc/register_client_with_invitation`, criando a
cliente e consumindo o convite na mesma transação. Prepare primeiro a tabela
`public.clients` (migration 001) e execute a
[migration 004](app/infrastructure/database/migrations/004_create_registration_links.sql)
no SQL Editor do Supabase. Use uma chave secreta do backend ou a chave legada
`service_role`, que possuem as permissões necessárias. Sem credenciais, os
convites e as clientes ficam em memória e são perdidos ao reiniciar a API.
No cadastro por convite, espaços nas extremidades dos campos são removidos.
Nome deve ter entre 2 e 150 caracteres, telefone entre 8 e 30 e o e-mail deve
ser válido. Campos extras são rejeitados. Dados inválidos retornam `422`,
sem consumir o convite; links inválidos, expirados ou utilizados retornam `410`.
Falhas de acesso ao cadastro de clientes retornam `503`.
Cadastros e atualizações com e-mail ou telefone pertencente a outra cliente
retornam `409`, com `detail` e `field` (`email` ou `phone`). E-mails são comparados
sem diferenciar maiúsculas; telefones são comparados por dígitos, considerando
números brasileiros com DDD equivalentes à versão com código `55`.
O formato original dos contatos é preservado. Uma tentativa duplicada não
consome o convite: os dados podem ser corrigidos e reenviados.

Para ativar esse bloqueio no Supabase, execute a
[migration 005](app/infrastructure/database/migrations/005_unique_client_contacts.sql)
no SQL Editor após as migrations anteriores e reinicie a API atualizada.
Os índices únicos bloqueiam duplicidades inclusive em gravações simultâneas e
na função de cadastro por convite. Se já houver duplicidades, a migration aborta
sem excluir ou mesclar registros. O final do arquivo contém consultas para
localizá-las; revise os registros e resolva os conflitos antes de executar novamente.
Sem a migration 005, o banco Supabase ainda permite contatos duplicados.
As rotas de clientes, agendamentos, serviços, geração de convites e
`GET /auth/google/connect` exigem autenticação administrativa.
Configure no `.env` uma credencial exclusiva para o backend:

```env
ADMIN_API_TOKEN=cole_aqui_um_token_aleatorio_longo
```

Gere o valor com `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
Envie `Authorization: Bearer SEU_TOKEN` nas chamadas administrativas.
Em `/docs`, use **Authorize → AdminToken** e informe apenas o token.
Sem configuração, essas rotas retornam `503`; credenciais ausentes ou incorretas
retornam `401`. A validação do convite e o cadastro por token continuam públicos.
O callback OAuth do Google continua público e verifica o estado e o cookie do fluxo.
Para iniciar a conexão Google, um cliente administrativo deve enviar o cabeçalho
a `/auth/google/connect` e preservar o cookie recebido durante o redirecionamento.
Abrir diretamente essa URL na barra do navegador não envia o token administrativo.

Use HTTPS em produção. Essa credencial compartilhada é para integrações confiáveis:
não a inclua no código do frontend público, na URL ou nos links de convite.
O futuro painel web precisará de autenticação de usuários ou de um backend
intermediário que mantenha essa credencial no servidor. Para revogá-la,
altere `ADMIN_API_TOKEN` no ambiente e reinicie a API.

Inicie o servidor usando:
```bash
python main.py
```
A API estará disponível em `http://localhost:8000`.
A documentação interativa do Swagger pode ser acessada em `http://localhost:8000/docs`.

Para criar todas as tabelas em uma instalação inicial, execute o arquivo
[`app/infrastructure/database/init.sql`](app/infrastructure/database/init.sql)
completo no **SQL Editor** do painel do Supabase. O script executa a criação das
tabelas e a configuração de acesso em uma única transação.

**⚠️ IMPORTANTE: Atualização de Estrutura**
Se você já possuía tabelas criadas anteriormente, as mudanças recentes de normalização (substituição de JSON por colunas e introdução de chaves estrangeiras) exigem que você **apague as tabelas existentes** antes de rodar o `init.sql`. No SQL Editor do Supabase, execute:
```sql
drop table if exists public.appointments;
drop table if exists public.clients;
```
Em seguida, execute o `init.sql`. Isso é necessário pois `IF NOT EXISTS` não altera a estrutura de tabelas já criadas.

Como alternativa, execute os arquivos SQL de
`app/infrastructure/database/migrations` no **SQL Editor** do painel do Supabase,
em ordem de nome. Os scripts criam `clients` e `appointments` e configuram o
acesso pelo backend. Usam `CREATE TABLE IF NOT EXISTS`, sem apagar dados existentes.
A aplicação usa somente `SUPABASE_URL` e `SUPABASE_SECRET_KEY` para acessar a API REST e
não executa migrações na inicialização.

`IF NOT EXISTS` não atualiza colunas de tabelas já existentes; futuras alterações
precisam de scripts próprios. O CRUD de agendamentos usa a tabela `appointments` pela API REST do Supabase.
Falhas de persistência retornam HTTP `503`. O campo `end_time` é calculado pela
aplicação e não é enviado como coluna ao banco.

## Arquitetura

- **Camada de API**: Endpoints FastAPI.
- **Camada de Serviço**: Lógica de negócio, validações (sobreposição de horários e datas passadas).
- **Camada de Infraestrutura**: Interfaces mockáveis para Banco de Dados (Supabase/Memória) e Agenda (Google).

## Documentação da API

Abaixo estão os endpoints disponíveis. Para testar, utilize o Swagger UI em `/docs`.

### Clientes

| Método | Rota | Descrição |
| :--- | :--- | :--- |
| `POST` | `/clientes/` | Cadastrar uma cliente |
| `GET` | `/clientes/` | Listar as clientes cadastradas |
| `GET` | `/clientes/{id}` | Consultar uma cliente pelo ID |
| `PATCH` | `/clientes/{id}` | Atualizar parcialmente uma cliente |
### Clientes
...
| `DELETE` | `/clientes/{id}` | Excluir uma cliente do cadastro |

**Regra de Negócio - Deleção de Cliente:** 
Uma cliente **somente poderá ser excluída se não possuir agendamentos vinculados**. Caso existam agendamentos, a API retornará um erro informando que a cliente possui vínculos ativos. Para excluir a cliente, todos os seus agendamentos devem ser removidos primeiro.

Os nomes dos campos seguem o padrão em inglês já usado pela API:
...

| Campo | Significado | Enviado no cadastro? |
| :--- | :--- | :--- |
| `id` | Identificador UUID da cliente | Gerado pelo servidor |
| `name` | Nome da cliente | Obrigatório |
| `email` | E-mail da cliente | Obrigatório |
| `phone` | Número de telefone/WhatsApp | Obrigatório, como texto |
| `created_at` | Data e hora do cadastro | Gerada pelo servidor, em UTC |

Exemplo de corpo para `POST /clientes/`:

```json
{
  "name": "Maria Silva",
  "email": "maria@email.com",
  "phone": "+55 11 99999-9999"
}
```

Exemplo de resposta (`201 Created`):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Maria Silva",
  "email": "maria@email.com",
  "phone": "+55 11 99999-9999",
  "created_at": "2026-10-09T15:00:00Z"
}
```

Para alterar somente o número, envie `{"phone": "11988887777"}` ao `PATCH /clientes/{id}`. Os campos omitidos, o ID e a data de cadastro são preservados; um corpo vazio mantém os dados atuais. Nome e telefone não podem ser vazios ou conter apenas espaços, o e-mail deve ser válido e os campos enviados não podem ser nulos. Campos desconhecidos, incluindo `id` e `created_at` nos corpos de criação e atualização, são rejeitados.

Clientes inexistentes retornam `404`; dados inválidos e IDs que não são UUIDs retornam `422`. Falhas no acesso ao Supabase retornam `503`. Em memória, os dados são perdidos ao reiniciar a aplicação. No Supabase, o cadastro utiliza a [API REST de dados](https://supabase.com/docs/guides/api).

Os agendamentos continuam recebendo os dados de contato no campo `client`. O cadastro e a exclusão de clientes não criam, alteram ou excluem agendamentos automaticamente.

### 📅 Agendamentos

**Regra de Integridade:** 
Agendamentos dependem obrigatoriamente de uma cliente existente. Não é permitido criar ou alterar um agendamento para um `client_id` que não esteja cadastrado no sistema.

| Método | Rota | Descrição | Parâmetros Principais |
| :--- | :--- | :--- | :--- |
| `POST` | `/agendamentos` | Registrar um novo agendamento | `client_id` (UUID), `service`, `start_time`, `duration_minutes` |
| `GET` | `/agendamentos` | Listar todos os agendamentos | `start_date`, `end_date` (Opcionais) |
| `GET` | `/agendamentos/{id}` | Obter detalhes de um agendamento | `id` (Path) |
| `PATCH` | `/agendamentos/{id}` | Atualizar um agendamento existente | `id` (Path), Corpo do agendamento |
| `DELETE` | `/agendamentos/{id}` | Cancelar um agendamento | `id` (Path) |
| `POST` | `/agendamentos/{id}/sincronizar` | Forçar sincronizar com o Google Agenda | `id` (Path) |

**Exemplo de corpo para `POST /agendamentos`:**
```json
{
  "client_id": "550e8400-e29b-41d4-a716-446655440000",
  "service": "Alongamento em Gel",
  "start_time": "2026-11-10T14:00:00",
  "duration_minutes": 120,
  "sync_state": {
    "google_event_id": "ev_123456789",
    "status": "Pending",
    "last_synced": "2026-11-10T15:00:00Z"
  }
}
```

**Validações Importantes:**
- `start_time`: Deve ser uma data futura. Agendamentos no passado são rejeitados (`400 Bad Request`).
- `client_id`: Deve ser um UUID válido de uma cliente já cadastrada no sistema.

Datas com fuso horário são convertidas para UTC. Datas sem fuso, inclusive nos
filtros, são interpretadas no horário de `America/Sao_Paulo`.

**Observação:** O campo `id` do agendamento é gerado automaticamente pelo sistema e não deve ser enviado na requisição de criação (`POST`).

## Testes

Instale as dependências de desenvolvimento e execute:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Os testes verificam o CRUD de clientes, atualizações parciais, validações, campos gerados pelo servidor e compatibilidade com os agendamentos. As chamadas ao Supabase são simuladas nos testes, sem necessidade de credenciais ou acesso a um banco real.

Para executar somente os testes de convites:

```bash
python -m unittest discover -s tests -p 'test_registration*.py' -v
```

A cobertura inclui geração de links distintos, hash armazenado, validade de seis
horas, limite exato da expiração, reutilização, validação de formulário, falhas
ao salvar o convite ou a cliente e nova tentativa após falha. A concorrência é
verificada entre serviços e por HTTP: somente uma tentativa cadastra a cliente.
Esses testes usam o repositório em memória dentro de um único processo.
Um teste com subprocesso confirma que os convites em memória não sobrevivem ao
encerramento do processo. Isso documenta uma limitação, sem atestar persistência.
Os testes REST e RPC usam respostas simuladas e verificam os parâmetros, a
autenticação, a seleção do backend e os erros retornados pelo Supabase.
A persistência e a concorrência no PostgreSQL real ainda precisam ser verificadas
em um banco de testes com as migrations aplicadas.

Para verificar a persistência manualmente nesse banco: gere um convite com
`POST /registration-links` usando o token administrativo, guarde a URL e reinicie
a API mantendo as credenciais do mesmo projeto Supabase. A consulta
`GET /registration-links/{token}` deve continuar retornando `200`. Envie nome,
e-mail e telefone a `POST /registration-links/{token}/register`; a primeira
tentativa deve retornar `201` e a reutilização deve retornar `410`, inclusive
após outro reinício. Esse procedimento cria uma cliente no banco escolhido.
Se a requisição RPC sofrer timeout, consulte o estado do convite antes de tentar
novamente: a transação pode ter sido concluída mesmo sem a resposta chegar à API.

## Aviso de Segurança
Credenciais sensíveis (`.env`) são gerenciadas via `.gitignore`. Nunca envie suas chaves para o repositório.


## Conectar o Google Calendar

Esta versão conecta **uma conta/agenda por instalação**, com um único processo
Uvicorn. A conexão abre diretamente a autorização no Google, sem usuário/senha local.
Para múltiplas profissionais/contas serão necessários autenticação de usuários e
armazenamento de tokens por conta. As rotas de agendamentos ainda não exigem login;
use localmente até configurar autenticação e controle de acesso para publicação.

1. No Google Cloud, habilite Calendar API e configure o consentimento com seu e-mail
   como usuário de teste. Crie um cliente OAuth do tipo **Aplicativo da Web** e cadastre
   exatamente `http://localhost:8000/auth/google/callback` como URI de redirecionamento.
   Autorize o escopo `https://www.googleapis.com/auth/calendar.events`.
2. Instale `pip install -r requirements.txt` com o ambiente virtual ativo.
3. Gere a chave de criptografia e copie para `GOOGLE_TOKEN_ENCRYPTION_KEY` no `.env`
   (não compartilhe o resultado):
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
4. Complete seu `.env`, preservando as configurações do Supabase:
   ```env
   CALENDAR_BACKEND=google
   GOOGLE_CLIENT_ID=seu_id_oauth
   GOOGLE_CLIENT_SECRET=seu_segredo_oauth
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
   GOOGLE_CALENDAR_ID=primary
   GOOGLE_TOKEN_ENCRYPTION_KEY=chave_de_criptografia_gerada
   GOOGLE_TOKEN_FILE=.secrets/google-token.enc
   ```
5. Inicie `python main.py`. Abra `http://localhost:8000/auth/google/connect` no navegador.
   Você será direcionado ao Google. Escolha a conta da agenda e permita acesso aos eventos. Mantenha o mesmo navegador
   e host (`localhost`) até concluir; o fluxo expira em dez minutos.
6. Após a mensagem de sucesso, use `/docs` para criar um agendamento futuro com e-mail
   de teste. Confira o evento na agenda, altere-o e depois exclua-o pela API.
   **Criação, alteração e exclusão enviam notificações Google à convidada.**
   A rota `/agendamentos/{id}/sincronizar` consulta a resposta ao convite (aceito,
   recusado, talvez ou pendente); ela também tenta reenviar alterações pendentes e
   criar o evento quando o agendamento ainda está sem ID do Google.

Os tokens são criptografados com Fernet, gravados atomicamente em arquivo com acesso
restrito ao usuário do processo e ignorados pelo Git. Guarde a chave de criptografia:
perdê-la exige autorizar novamente. O acesso é renovado automaticamente; revogação
ou expiração do refresh token exige repetir `/auth/google/connect`. Em modo de teste
externo, o Google pode expirar o refresh token em sete dias.

O banco e o Google não compartilham uma transação: uma falha Google retorna 503,
mas a criação/alteração pode já estar salva no banco. Consulte os agendamentos e use
`/sincronizar` com o ID existente para recuperar, evitando cadastrar novamente.
A verificação de sobreposição considera os agendamentos do NailsFlow, não eventos
criados diretamente no Google. Para servidor publicado, configure HTTPS, mantenha
um único worker nesta versão e não registre query strings do callback no proxy
(elas contêm o código OAuth). `python main.py` desativa o access log do Uvicorn.

`GOOGLE_ADMIN_KEY` não é mais utilizada e pode ser removida do `.env`. A rota de
conexão está acessível a quem alcança o servidor; em uma instalação pública, proteja
esse acesso antes de permitir a troca da conta Google conectada.
