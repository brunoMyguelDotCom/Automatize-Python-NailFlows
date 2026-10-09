# NailFlows API

API para Nail Designers cadastrarem clientes e gerenciarem agendamentos. O cadastro de clientes pode ser armazenado em memória ou no Supabase; a integração dos agendamentos com Supabase e Google Agenda ainda é simulada.

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
   Sem configuração, a API utiliza armazenamento em memória para desenvolvimento. Para persistir clientes no Supabase, execute o arquivo `app/infrastructure/database/migrations/001_create_clients.sql` no SQL Editor do projeto e configure as variáveis de ambiente do processo:
   ```env
   # Configuração do Supabase
   SUPABASE_URL=seu_url_do_supabase_aqui
   SUPABASE_KEY=sua_chave_secreta_do_backend_aqui

   # Configuração do Google Agenda (para futura implementação real)
   GOOGLE_CLIENT_ID=seu_google_client_id
   GOOGLE_CLIENT_SECRET=seu_google_client_secret
   ```

   No PowerShell, antes de iniciar a API:
   ```powershell
   $env:SUPABASE_URL = "https://seu-projeto.supabase.co"
   $env:SUPABASE_KEY = "sua_chave_secreta_do_backend_aqui"
   ```

   A aplicação lê as variáveis de ambiente com `os.getenv`; um arquivo `.env` não é carregado automaticamente. Se utilizar esse arquivo com outra ferramenta, mantenha-o fora do controle de versão. A tabela de clientes usa RLS e acesso pelo backend com uma chave secreta (`sb_secret_...`) ou a chave legada `service_role`. A chave permanece no backend. Consulte a [documentação de chaves do Supabase](https://supabase.com/docs/guides/api/api-keys).

### Executando a Aplicacao

Inicie o servidor usando:
```bash
python main.py
```
A API estará disponível em `http://localhost:8000`.
A documentação interativa do Swagger pode ser acessada em `http://localhost:8000/docs`.

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
| `DELETE` | `/clientes/{id}` | Excluir uma cliente do cadastro |

Os nomes dos campos seguem o padrão em inglês já usado pela API:

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

| Método | Rota | Descrição | Parâmetros Principais |
| :--- | :--- | :--- | :--- |
| `POST` | `/agendamentos` | Registrar um novo agendamento | `client` (nome, email, tel), `service`, `start_time`, `duration_minutes` |
| `GET` | `/agendamentos` | Listar todos os agendamentos | Nenhum |
| `GET` | `/agendamentos/{id}` | Obter detalhes de um agendamento | `id` (Path) |
| `PATCH` | `/agendamentos/{id}` | Atualizar um agendamento existente | `id` (Path), Corpo do agendamento |
| `DELETE` | `/agendamentos/{id}` | Cancelar um agendamento | `id` (Path) |
| `POST` | `/agendamentos/{id}/sincronizar` | Forçar sincronização com o Google Agenda | `id` (Path) |

**Observação:** O campo `id` do agendamento é gerado automaticamente pelo sistema e não deve ser enviado na requisição de criação (`POST`).

## Testes

Instale as dependências de desenvolvimento e execute:

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Os testes verificam o CRUD de clientes, atualizações parciais, validações, campos gerados pelo servidor e compatibilidade com os agendamentos. As chamadas ao Supabase são simuladas nos testes, sem necessidade de credenciais ou acesso a um banco real.

## Aviso de Segurança
Credenciais sensíveis (`.env`) são gerenciadas via `.gitignore`. Nunca envie suas chaves para o repositório.
