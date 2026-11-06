-- Migração para adicionar a tabela de serviços e normalizar agendamentos.

begin;

-- 1. Criar a tabela de serviços
create table if not exists public.services (
    id uuid primary key default gen_//_random_uuid(),
    name text not null check (length(trim(name)) > 0),
    duration_minutes integer not null check (duration_minutes > 0),
    active boolean not null default true
);

-- 2. Habilitar RLS e dar permissões
alter table public.services enable row level security;
grant select, insert, update, delete on public.services to service_role;

-- 3. Normalizar a tabela de agendamentos
-- Adiciona a coluna service_id
alter table public.appointments add column if not exists service_id uuid;

-- (Opcional) Se houver dados, aqui seria necessária uma lógica de migração de texto para UUID.
-- Como estamos em dev, vamos forçar a obrigatoriedade após a limpeza dos dados.
alter table public.appointments alter column service_id set not null;
alter table public.appointments add constraint appointments_service_id_fkey
    foreign key (service_id) references public.services(id) on delete restrict;

-- Remove a coluna de texto antiga
alter table public.appointments drop column if exists service;

commit;
