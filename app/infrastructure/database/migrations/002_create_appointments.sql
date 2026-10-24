create table if not exists public.appointments (
    id uuid primary key default gen_random_uuid(),
    client jsonb not null,
    service text not null,
    start_time timestamptz not null,
    duration_minutes integer not null,
    sync_state jsonb not null default '{"status": "Pending"}'::jsonb
);

alter table public.appointments enable row level security;

grant select, insert, update, delete on public.appointments to service_role;
