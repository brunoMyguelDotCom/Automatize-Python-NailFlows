-- Execute após as migrations 001 e 004.
-- Se houver duplicidades, a migration aborta sem apagar ou mesclar clientes.
begin;

create or replace function public.normalize_client_phone(value text)
returns text
language sql
immutable
strict
parallel safe
set search_path = ''
as $$
    select case
        when length(digits) in (10, 11) then '55' || digits
        else digits
    end
    from (select regexp_replace(value, '[^0-9]', '', 'g') as digits) normalized;
$$;

-- As restrições também abrangem a RPC de convite e cadastros simultâneos.
create unique index if not exists clients_email_normalized_key
    on public.clients (lower(btrim(email)));

create unique index if not exists clients_phone_normalized_key
    on public.clients (public.normalize_client_phone(phone));

commit;

-- Para localizar duplicidades ANTES de executar a migration, rode separadamente:
-- select lower(btrim(email)) as email, array_agg(id) as client_ids, count(*)
-- from public.clients group by lower(btrim(email)) having count(*) > 1;
--
-- with contacts as (
--   select id, regexp_replace(phone, '[^0-9]', '', 'g') as digits from public.clients
-- ), normalized as (
--   select id, case when length(digits) in (10, 11) then '55' || digits
--                   else digits end as phone from contacts
-- )
-- select phone, array_agg(id) as client_ids, count(*)
-- from normalized group by phone having count(*) > 1;
