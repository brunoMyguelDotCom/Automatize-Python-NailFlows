# Changelog

Todas as alterações relevantes deste projeto serão documentadas neste arquivo.

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
- Refatoração dos modelos de domínio para separar `AppointmentCreate` de `Appointment`, garantindo que o `id` do agendamento seja tratado como somente leitura/gerado automaticamente no Swagger.
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
2. **Gestão de Agendamentos**: Criação, leitura, atualização, e exclusão de horários, com validações automáticas para impedir agendamentos em datas passadas ou a marcação de dois clientes no mesmo horário (sobreposição).
3. **Sincronização com Google Agenda (Mock)**: Ao criar ou atualizar um agendamento, o sistema simula a criação de um evento no Google Agenda.
4. **Rastreamento de Status**: O sistema consegue consultar (via mock) se o cliente confirmou, recusou ou está pendente no convite do Google Agenda, atualizando essa informação no banco de dados interno.
5. **Persistência Flexível**: Sem credenciais do Supabase, o sistema utiliza memória RAM. Com credenciais, o cadastro de clientes utiliza a API REST do Supabase; a persistência dos agendamentos permanece simulada.
