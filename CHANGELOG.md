# Changelog

Todas as alterações relevantes deste projeto serão documentadas neste arquivo.

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
1. **Gestão de Agendamentos**: Criação, leitura, atualização e exclusão de horários, com validações automáticas para impedir agendamentos em datas passadas ou a marcação de dois clientes no mesmo horário (sobreposição).
2. **Sincronização com Google Agenda (Mock)**: Ao criar ou atualizar um agendamento, o sistema simula a criação de um evento no Google Agenda.
3. **Rastreamento de Status**: O sistema consegue consultar (via mock) se o cliente confirmou, recusou ou está pendente no convite do Google Agenda, atualizando essa informação no banco de dados interno.
4. **Persistência Flexível**: O sistema verifica automaticamente as variáveis de ambiente; se as credenciais do Supabase não forem encontradas, ele utiliza memória RAM para salvar os dados, garantindo que o projeto seja executável imediatamente.
