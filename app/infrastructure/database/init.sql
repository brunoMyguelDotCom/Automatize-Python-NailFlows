-- Inicialização do banco NailFlows no PostgreSQL/Supabase.
-- Execute este arquivo completo no SQL Editor do projeto Supabase.
-- Alternativa às migrações 001 e 002 para uma instalação inicial.
-- Requer o papel service_role, fornecido pelo Supabase.
-- IF NOT EXISTS preserva tabelas existentes, mas não atualiza sua estrutura.

begin;

-- Cadastro de clientes.
create table if not exists public.clients (
    id uuid primary key default gen_random_uuid(),
    name text not null check (length(trim(name)) > 0),
    email text not null,
    phone text not null check (length(trim(phone)) > 0),
    created_at timestamptz not null default now()
);

-- Agendamentos: client contém os dados de contato do próprio agendamento.
-- O modelo atual não possui client_id ou vínculo com o cadastro de clientes.
-- sync_state contém google_event_id, status e last_synced quando disponíveis.
-- end_time é calculado pela aplicação a partir do início e da duração.
create table if not exists public.appointments (
    id uuid primary key default gen_random_uuid(),
    client jsonb not null,
    service text not null,
    start_time timestamptz not null,
    duration_minutes integer not null,
    sync_state jsonb not null default '{"status": "Pending"}'::jsonb
);

alter table public.clients enable row level security;
alter table public.appointments enable row level security;

-- Acesso pelo backend com chave secreta ou service_role.
-- Não são criadas políticas de acesso para usuários anônimos/autenticados.
grant select, insert, update, delete on public.clients to service_role;
grant select, insert, update, delete on public.appointments to service_role;

commit;
