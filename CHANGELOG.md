# Changelog

Todas as alterações relevantes deste projeto serão documentadas neste arquivo.

## [0.3.0] - 2026-10-11
### Added
- Implementação de CORS (Cross-Origin Resource Sharing) para permitir requisições de navegadores (frontend).
- Filtros de data (`start_date` e `end_date`) no endpoint `GET /agendamentos`.
- Ordenação automática de agendamentos por horário de início (`start_time`) no `GET /agendamentos`.
- Exposição do campo calculado `end_time` (hora de término) no JSON de resposta dos agendamentos, facilitando a visualização no frontend.

### Changed
- Atualização do endpoint `GET /agendamentos` para suportar query parameters de filtragem.
- Refatoração do modelo `Appointment` para utilizar `@computed_field` do Pydantic para o campo `end_time`.

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
1. **Gestão de Agendamentos**: Criação, leitura, atualização, e exclusão de horários, com validações automativas para impedir agendamentos em datas passadas ou a marcação de dois clientes no mesmo horário (sobreposição).
2. **Sincronização com Google Agenda (Mock)**: Ao criar ou atualizar um agendamento, o sistema simula a criação de um evento no Google Agenda.
3. **Rastreamento de Status**: O sistema consegue consultar (via mock) se o cliente confirmou, recusou ou está pendente no convite do Google Agenda, atualizando essa informação no banco de dados interno.
4. **Persistência Flexível**: O sistema verifica automaticamente as variáveis de ambiente; se as credenciais do Supabase não forem encontradas, ele utiliza memória RAM para salvar os dados, garantindo que o projeto seja executável imediatamente.
