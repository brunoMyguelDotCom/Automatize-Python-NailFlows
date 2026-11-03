create table if not exists public.appointments (
    id uuid primary key default gen_random_uuid(),
    client_id uuid not null references public.clients(id) on delete restrict,
    service text not null,
    start_time timestamptz not null,
    duration_minutes integer not null,
    sync_google_event_id text,
    sync_status text not null default 'Pending',
    sync_last_synced timestamptz
);

alter table public.appointments enable row level security;

-- A tabela é acessada pelo backend com a chave secreta ou service_role.
grant select, insert, update, delete on public.appointments to service_role;
