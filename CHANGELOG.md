# Changelog

Todas as alterações relevantes deste projeto serão documentadas neste arquivo.

## [1.3.0] - 2026-11-09

### Added
- Backend de autocadastro de clientes por convite, com geração em `POST /registration-links`, validação em `GET /registration-links/{token}` e cadastro em `POST /registration-links/{token}/register`.
- Convites de uso único com validade de seis horas e armazenamento apenas do hash do token. Links inválidos, expirados ou utilizados retornam `410`.
- Persistência de convites no Supabase e função RPC para criar a cliente e consumir o convite na mesma transação, por meio da migration `004_create_registration_links.sql`. Sem credenciais, o fluxo utiliza memória e perde os dados ao reiniciar.
- Validação do formulário de autocadastro, com remoção de espaços nas extremidades, limites de nome e telefone, validação de e-mail e rejeição de campos extras. Dados inválidos ou contatos duplicados não consomem o convite.
- Autenticação administrativa por `ADMIN_API_TOKEN`, enviada como Bearer token, com suporte ao esquema `AdminToken` no Swagger.
- Migration `005_unique_client_contacts.sql` com índices únicos para impedir contatos duplicados, inclusive em gravações simultâneas. A migration aborta caso existam duplicidades, sem excluir ou mesclar registros.
- Testes de ciclo de vida dos convites, validação, concorrência em memória, integração HTTP, chamadas simuladas ao Supabase, autenticação administrativa e contatos duplicados.
- Documentação das variáveis `FRONTEND_URL` e `ADMIN_API_TOKEN`, aplicação das migrations e verificação manual da persistência no Supabase. A página de cadastro no frontend ainda precisa ser implementada.

### Changed
- Rotas de clientes, agendamentos, serviços, geração de convites e conexão com Google passam a exigir autenticação administrativa. Credenciais ausentes ou incorretas retornam `401`; ausência de configuração retorna `503`.
- Validação e cadastro por convite permanecem públicos, assim como o callback OAuth do Google, que mantém a validação de estado e cookie.
- Cadastro e atualização de clientes passam a retornar `409` para e-mail ou telefone já cadastrado, identificando o campo em conflito. A comparação ignora maiúsculas no e-mail e normaliza os dígitos do telefone, considerando a equivalência de números brasileiros com DDD e código `55`, preservando o formato original armazenado.
- Falhas de acesso ao armazenamento de convites retornam `503`.

## [1.2.0] - 2026-11-05

### Added
- Filtro de status em agendamentos: a listagem de agendamentos agora aceita o parâmetro `active_only`, permitindo filtrar apenas agendamentos ativos ou visualizar todo o histórico (incluindo os cancelados).

## [0.5.0] - 2026-11-05

### Added
- Implementação completa do módulo de Serviços (CRUD completo em `/servicos`), permitindo a gestão de tipos de atendimento, duração e status de atividade.
- Normalização do banco de dados: agendamentos agora utilizam `service_id` (Foreign Key) em vez de texto simples, vinculando-os a serviços reais.
- Regra de negócio de "Soft Delete" para serviços: deletar um serviço agora apenas o marca como inativo (`active=False`), preservando o histórico de agendamentos.
- Regra de negócio de "Soft Delete" para agendamentos: cancelar um agendamento agora apenas o marca como inativo (`active=False`), mantendo o histórico para a profissional.
- Validação de atividade em agendamentos: impedimento de a criação ou alteração de agendamentos utilizando serviços inativos.
- Lógica de Duração Automática: se a duração não for informada na criação do agendamento, o sistema utiliza automaticamente a duração padrão vinculada ao serviço selecionado.
- Implementação de tratamento de erros rigoroso para serviços (`ServiceDatabaseError`), seguindo o padrão de qualidade de Clientes e Agendamentos.
- Atualização do `init.sql` com script de limpeza total e recarregamento de cache do PostgREST (`notify pgrst`) para evitar erros de relacionamento no Supabase.
- Refatoração dos modelos de API para exigir apenas IDs (`client_id`, `service_id`) no corpo da requisição, removendo a necessidade de enviar objetos completos.
- Hidratação de dados no retorno de agendamentos: a API agora retorna os objetos completos de Cliente e Serviço após a criação/atualização.

## [0.4.0] - 2026-11-05

### Added
- Integração real com Google Calendar para uma conta/agenda por instalação, com criação, atualização e exclusão de eventos e envio de convites à cliente.
- Fluxo OAuth 2.0 nas rotas `/auth/google/connect` e `/auth/google/callback`, com validação de estado, vínculo ao navegador, PKCE e expiração da autorização pendente.
- Armazenamento local de tokens criptografados com Fernet, gravação atômica com permissões restritas e renovação automática do acesso.
- Consulta da resposta ao convite e recuperação de agendamentos sem evento associado pela rota de sincronização.
- Testes de autorização OAuth, criptografia, renovação de tokens e integração dos agendamentos com o calendário, com chamadas externas simuladas.
- Guia de configuração OAuth e das variáveis de ambiente no README, incluindo limites da integração e recuperação após falhas.
- Implementação de persistência real para agendamentos via API REST do Supabase (`SupabaseDatabase`), substituindo a simulação anterior.
- Suporte a operações CRUD completas para agendamentos no Supabase: criação, leitura, atualização e exclusão.
- Integração de tratamento de erros específico para agendamentos no Supabase utilizando `AppointmentDatabaseError`.
- Refatoração da infraestrutura de banco de dados para suportar múltiplos modelos de registro através da classe base `SupabaseRestDatabase`.

### Changed
- Seleção entre calendário simulado e real pela variável `CALENDAR_BACKEND`.
- Execução local por `python main.py` restrita a `127.0.0.1`, com access log desativado para evitar registrar códigos OAuth nas URLs.
- Arquivos de tokens e credenciais Google adicionados ao `.gitignore`.

### Fixed
- Preservação do ID do evento e do estado de sincronização ao atualizar um agendamento.
- Registro da data da última sincronização ao consultar o status do convite.

## [0.3.0] - 2026-10-09

### Added

- Endpoints para cadastrar, listar, consultar, atualizar parcialmente e excluir clientes em `/clientes`.
- Modelos de cadastro, atualização e resposta com nome, e-mail, telefone/WhatsApp, UUID e data de cadastro em UTC.
- Serviço de clientes e armazenamento separado em memória ou pela API REST do Supabase.
- Migração SQL para a tabela de clientes no Supabase e tratamento de falhas de persistência com resposta `503`.
- Testes do CRUD, validações, preservação dos campos de cadastro e compatibilidade dos agendamentos.
- Documentação com exemplos de requisição, resposta e configuração do armazenamento.

## [0.2.0] - 2026-10-05
### Added
- Implementação de documentação Swagger/OpenAPI detalhada para todos os endpoints da API.
- Adição de metadados globais à aplicação (descrição, versão e contato).
- Descrições detalhadas e exemplos de valores para todos os campos dos modelos Pydantic.
- Refatoração dos modelos de domínio para separar `AppointmentCreate` de `Appointment`, garantindo que o `id` do agendamento seja tratado como somente leitura/gerados automaticamente no Swagger.
- Atualização do `README.md` com a tabela de endpoints e guia de uso da documentação interativa.
- Implementação de versionamento dinâmico: a versão da API agora é extraída automaticamente do CHANGELOG.md.

### Changed
- Atualização da lógica de `AppointmentService` para suportar os novos modelos de criação e atualização, mantendo a integridade dos dados de sincronização.
- Remoção de informações de contato de suporte nos metadados da API, adequando-a para uso interno.

## [0.1.1] - 2026-10-01
### Changed
- Substituição de todos os comandos `print` por um sistema de logs profissional utilizando a biblioteca `logging` do Python.
- Remoção de emojis de todo o código-fonte e mensagens de log para manter um padrão profissional.
- Implementação de lógica de fallback automático no `main.py`: o sistema agora detecta a ausência de credenciais do Supabase nas variáveis de ambiente e alterna automaticamente para o banco de dados em memória.

## [0.1.0] - 2026-10-01
### Added
- Estrutura inicial do projeto.
- Implementação de arquitetura em camadas (API, Serviço, Infraestrutura).
- Modelos de domínio para Cliente e Agendamento.
- Implementação de banco de dados em memória para prototipagem rápida.
- Integração mockada com Google Agenda para sincronização de eventos e consulta de status.
- Endpoints FastAPI para CRUD completo de agendamentos e sincronização manual.
- `.gitignore` para proteger credenciais sensíveis.
- README.md e CHANGELOG.md para documentação do projeto.

---

## Resumo Atual do Sistema
O código implementa atualmente o núcleo lógico de um sistema de agendamentos. Ele permite:

1. **Cadastro de Clientes**: Criação, leitura, atualização parcial e exclusão de clientes, com identificação e data de cadastro geradas pelo servidor.
2. **Gestão de Agendamentos**: Criação, leitura, atualização, e exclusão (lógica) de horários, com validações automáticas para impedir agendamentos em datas passadas, sobreposição de horários e uso de serviços inativos.
3. **Integração com Google Agenda**: Calendário simulado ou integração real via OAuth para uma conta por instalação, com criação, atualização e exclusão de eventos.
4. **Rastreamento de Status**: Consulta manual da resposta ao convite (confirmado, recusado, talvez ou pendente), com atualização do estado e da data de sincronização no banco interno.
5. **Persistência Flexível**: Sem credenciais do Supabase, o sistema utiliza memória RAM para clientes, agendamentos e convites. Com credenciais e migrations aplicadas, clientes, serviços, agendamentos e convites são persistidos no Supabase, com cadastro por convite realizado em uma transação via RPC.
6. **Autocadastro por Convite**: Geração de links de uso único com expiração em seis horas, validação pública e cadastro de clientes com bloqueio de contatos duplicados. A página de cadastro no frontend ainda está pendente.
7. **Proteção Administrativa**: Autenticação por Bearer token nas rotas administrativas e no início da conexão com Google Agenda.
