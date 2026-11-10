-- Requer public.clients, criada pela migration 001.
begin;

create table if not exists public.registration_links (
    token_hash text primary key
        check (token_hash ~ '^[0-9a-f]{64}$'),
    created_at timestamptz not null default now(),
    expires_at timestamptz not null,
    used_at timestamptz,
    check (expires_at > created_at)
);

alter table public.registration_links enable row level security;
revoke all on table public.registration_links from public, anon, authenticated;
grant select, insert, update, delete
    on table public.registration_links to service_role;

-- O backend envia o SHA-256 do token, nunca o token original.
-- SECURITY INVOKER: execução exclusiva pelo backend com service_role.
create or replace function public.register_client_with_invitation(
    p_token_hash text,
    p_name text,
    p_email text,
    p_phone text
)
returns setof public.clients
language plpgsql
security invoker
set search_path = ''
as $$
declare
    v_link public.registration_links%rowtype;
    v_client public.clients%rowtype;
    v_now timestamptz;
begin
    select * into v_link
    from public.registration_links
    where token_hash = p_token_hash
    for update;

    if not found then
        raise exception using errcode = 'P0001', message = 'Link inválido';
    end if;

    if v_link.used_at is not null then
        raise exception using errcode = 'P0001', message = 'Link já utilizado';
    end if;

    -- Verifica a hora depois de obter o bloqueio, inclusive se houve espera.
    v_now := clock_timestamp();
    if v_now >= v_link.expires_at then
        raise exception using errcode = 'P0001', message = 'Link expirado';
    end if;

    if p_name is null or char_length(btrim(p_name)) not between 2 and 150
       or p_email is null or btrim(p_email) = ''
       or p_phone is null or char_length(btrim(p_phone)) not between 8 and 30 then
        raise exception using errcode = '22023', message = 'Dados de cadastro inválidos';
    end if;

    -- A validação completa do e-mail continua sendo feita pelo backend.
    insert into public.clients (name, email, phone)
    values (btrim(p_name), btrim(p_email), btrim(p_phone))
    returning * into v_client;

    update public.registration_links
    set used_at = v_now
    where token_hash = p_token_hash;

    return next v_client;
end;
$$;

revoke all on function public.register_client_with_invitation(text, text, text, text)
    from public, anon, authenticated;
grant execute on function public.register_client_with_invitation(text, text, text, text)
    to service_role;

commit;
