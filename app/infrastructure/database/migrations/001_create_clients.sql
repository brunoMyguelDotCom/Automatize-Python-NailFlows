create table if not exists public.clients (
    id uuid primary key default gen_random_uuid(),
    name text not null check (length(trim(name)) > 0),
    email text not null,
    phone text not null check (length(trim(phone)) > 0),
    created_at timestamptz not null default now()
);

alter table public.clients enable row level security;

-- A tabela é acessada pelo backend com a chave secreta ou service_role.
grant select, insert, update, delete on public.clients to service_role;
