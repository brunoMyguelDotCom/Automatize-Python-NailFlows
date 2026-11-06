-- Inicialização do banco NailFlows no PostgreSQL/Supabase.
-- Execute este arquivo completo no SQL Editor do projeto Supabase.
-- ATENÇÃO: Para garantir que as Foreign Keys sejam reconhecidas pelo PostgREST,
-- recomendamos deletar as tabelas existentes antes de rodar este script se estiver em ambiente de dev.

begin;

-- 1. Limpeza de tabelas existentes para evitar conflitos de cache de relacionamento (Opcional para Dev)
drop table if exists public.appointments cascade;
drop table if exists public.services cascade;
drop table if exists public.clients cascade;

-- 2. Cadastro de clientes.
create table public.clients (
    id uuid primary key default gen_random_uuid(),
    name text not null check (length(trim(name)) > 0),
    email text not null,
    phone text not null check (length(trim(phone)) > 0),
    created_at timestamptz not null default now()
);

-- 3. Cadastro de serviços.
create table public.services (
    id uuid primary key default gen_random_uuid(),
    name text not null check (length(trim(name)) > 0),
    duration_minutes integer not null check (duration_minutes > 0),
    active boolean not null default true
);

-- 4. Agendamentos: vinculado a um cliente e a um serviço.
create table public.appointments (
    id uuid primary key default gen_random_uuid(),
    client_id uuid not null references public.clients(id) on delete restrict,
    service_id uuid not null references public.services(id) on delete restrict,
    start_time timestamptz not null,
    duration_minutes integer not null,
    sync_google_event_id text,
    sync_status text not null default 'Pending',
    sync_last_synced timestamptz,
    active boolean not null default true
);

-- 5. Segurança e RLS
alter table public.clients enable row level security;
alter table public.services enable row level security;
alter table public.appointments enable row level security;

-- 6. Permissões para o service_role (usado pelo backend)
grant select, insert, update, delete on public.clients to service_role;
grant select, insert, update, delete on public.services to service_role;
grant select, insert, update, delete on public.appointments to service_role;

-- 7. Forçar recarregamento do cache do PostgREST
notify pgrst, 'reload schema';

commit;
