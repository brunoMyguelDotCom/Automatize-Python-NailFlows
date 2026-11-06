# Changelog

Todas as alterações relevantes deste projeto serão documentadas neste arquivo.

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

## [0.4.0] - 2026-11-03

### Added
- Implementação de persistência real para agendamentos via API REST do Supabase (`SupabaseDatabase`), substituindo a simulação anterior.
- Suporte a operações CRUD completas para agendamentos no Supabase: criação, leitura, atualização e exclusão.
- Integração de tratamento de erros específico para agendamentos no Supabase utilizando `AppointmentDatabaseError`.
- Refatoração da infraestrutura de banco de dados para suportar múltiplos modelos de registro através da classe base `SupabaseRestDatabase`.

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
3. **Sincronização com Google Agenda (Mock)**: Ao criar ou atualizar um agendamento, o sistema simula a criação de um evento no Google Agenda.
4. **Rastreamento de Status**: O sistema consegue consultar (via mock) se o cliente confirmou, recusou ou está pendente no convite do Google Agenda, atualizando essa informação no banco de dados interno.
5. **Persistência Flexível**: Sem credenciais do Supabase, o sistema utiliza memória RAM. Com credenciais, a gestão de clientes, serviços e agendamentos utiliza a API REST do Supabase.
