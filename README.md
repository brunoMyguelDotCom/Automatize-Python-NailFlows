# NailFlows API

Sistema de automação para Nail Designers gerenciarem agendamentos com sincronização automática ao Google Agenda e persistência de dados no Supabase.

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
   pip install fastapi uvicorn "pydantic[email]"
   ```

4. **Configuração do Ambiente:**
   Crie um arquivo `.env` no diretório raiz (este arquivo está no `.gitignore` e não deve ser compartilhado):
   ```env
   # Configuração do Supabase
   SUPABASE_URL=seu_url_do_supabase_aqui
   SUPABASE_KEY=sua_chave_anon_do_supabase_aqui

   # Configuração do Google Agenda (para futura implementação real)
   GOOGLE_CLIENT_ID=seu_google_client_id
   GOOGLE_CLIENT_SECRET=seu_google_client_secret
   ```

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

## Endpoints

| Método | Rota | Descrição |
| :--- | :--- | :--- |
| `POST` | `/agendamentos` | Registrar um novo agendamento |
| `GET` | `/agendamentos` | Listar todos os agendamentos |
| `GET` | `/agendamentos/{id}` | Obter detalhes de um agendamento |
| `PATCH` | `/agendamentos/{id}` | Atualizar um agendamento existente |
| `DELETE` | `/agendamentos/{id}` | Cancelar um agendamento |
| `POST` | `/agendamentos/{id}/sincronizar` | Forçar sincronização com o Google Agenda |

## Aviso de Segurança
Credenciais sensíveis (`.env`) são gerenciadas via `.gitignore`. Nunca envie suas chaves para o repositório.
