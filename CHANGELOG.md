# Changelog

Alterações relevantes do NailFlows API. A versão da aplicação é extraída da
primeira versão semântica encontrada neste arquivo.

## [1.4.0] - 2026-11-10

### Added

- Endpoint público `GET /servicos/keepalive`, que consulta a tabela `services` e
  retorna o status e a quantidade de serviços encontrados.
- Logs de diagnóstico para leitura do agendamento, exclusão no Google Calendar,
  atualização no Supabase, carregamento de credenciais e respostas HTTP do Google.

### Changed

- A documentação foi alinhada ao modelo atual de ambiente, Supabase, Render,
  autenticação administrativa, OAuth e keepalive.
- O cancelamento de agendamentos registra fases distintas e retorna uma mensagem
  específica quando a exclusão do evento Google falha.

### Fixed


## [1.3.0] - 2026-11-09

### Added

- Autocadastro de clientes por convite com geração em `POST /registration-links`,
  validação em `GET /registration-links/{token}` e cadastro em
  `POST /registration-links/{token}/register`.
- Convites de uso único com validade de seis horas e armazenamento apenas do hash.
- Persistência dos convites no Supabase por RPC transacional.
- Validação do formulário de autocadastro e rejeição de campos extras.
- Autenticação administrativa por `ADMIN_API_TOKEN` usando Bearer token.
- Migration `005_unique_client_contacts.sql` para impedir e-mails e telefones
  duplicados, inclusive em gravações simultâneas.
- Testes de convites, concorrência, integração HTTP, autenticação administrativa
  e duplicidade de contatos.

### Changed

- Clientes, agendamentos, serviços, geração de convites e conexão Google passaram
  a exigir autenticação administrativa.
- Validação e cadastro por convite continuam públicos, assim como o callback OAuth.
- Duplicidades de e-mail ou telefone retornam `409`, com identificação do campo.
- Falhas de acesso ao armazenamento de convites retornam `503`.

## [1.2.0] - 2026-11-05

### Added

- Filtro `active_only` na listagem de agendamentos.

## [0.5.0] - 2026-11-05

### Added

- CRUD de serviços em `/servicos` com duração e status de atividade.
- Normalização dos agendamentos para usar `service_id` como chave estrangeira.
- Soft delete de serviços e agendamentos por meio do campo `active`.
- Bloqueio de novos agendamentos para serviços inativos.
- Uso automático da duração padrão do serviço.
- Hidratação dos dados de cliente e serviço nos retornos de agendamentos.

### Changed

- Os corpos de agendamento usam `client_id` e `service_id`, em vez de objetos ou
  texto livre.
- `init.sql` passou a recriar as tabelas e recarregar o cache de schema do PostgREST.

## [0.4.0] - 2026-11-05

### Added

- Integração real com Google Calendar via OAuth 2.0 para uma agenda por instalação.
- PKCE, validação de estado, cookie de navegador e armazenamento criptografado do
  token OAuth.
- Persistência de agendamentos no Supabase via API REST.
- Criação, leitura, atualização e cancelamento lógico de agendamentos.
- Consulta de status de convites e sincronização manual com Google Calendar.

### Changed

- Seleção entre Google real e mock pela variável `CALENDAR_BACKEND`.
- Execução local com `python main.py` em `127.0.0.1:8000`.
- Arquivos de tokens Google protegidos pelo `.gitignore`.

### Fixed

- Preservação do ID do evento e do estado de sincronização ao atualizar agendamentos.
- Registro da data da última sincronização.

## [0.3.0] - 2026-10-09

### Added

- CRUD de clientes em `/clientes`.
- Validação de modelos, UUID e data de cadastro em UTC.
- Persistência de clientes em memória ou Supabase.
- Tratamento de falhas de persistência com `503`.

## [0.2.0] - 2026-10-05

### Added

- Documentação Swagger/OpenAPI detalhada.
- Metadados globais da aplicação e exemplos de modelos.
- Versionamento dinâmico a partir do `CHANGELOG.md`.

### Changed

- Separação entre modelos de criação e modelos completos de agendamento.

## [0.1.1] - 2026-10-01

### Changed

- Substituição de `print` pelo logger `nailflows`.
- Fallback para memória quando o Supabase não está configurado.

## [0.1.0] - 2026-10-01

### Added

- Estrutura inicial em camadas: API, domínio, serviços e infraestrutura.
- Modelos de clientes e agendamentos.
- Banco em memória e calendário Google mockado.
- Endpoints FastAPI e documentação inicial.
