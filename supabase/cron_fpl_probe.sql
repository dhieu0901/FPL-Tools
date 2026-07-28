-- Idempotent Supabase Cron setup for the VMF API.
--
-- Before running this file, create exactly these two Supabase Vault secrets:
--   vmf_api_base_url  = https://<your-api-project>.vercel.app
--   vmf_cron_secret   = the same value as CRON_SECRET in the Vercel API project
--
-- Do not paste either secret into this tracked SQL file.

create extension if not exists pg_cron with schema pg_catalog;
create extension if not exists pg_net with schema extensions;

do $setup$
declare
  api_url_count integer;
  cron_secret_count integer;
begin
  select count(*)
    into api_url_count
    from vault.decrypted_secrets
   where name = 'vmf_api_base_url';

  select count(*)
    into cron_secret_count
    from vault.decrypted_secrets
   where name = 'vmf_cron_secret';

  if api_url_count <> 1 then
    raise exception
      'Expected exactly one Vault secret named vmf_api_base_url; found %',
      api_url_count;
  end if;

  if cron_secret_count <> 1 then
    raise exception
      'Expected exactly one Vault secret named vmf_cron_secret; found %',
      cron_secret_count;
  end if;
end
$setup$;

-- A named schedule is overwritten when this script is run again.
-- pg_cron uses UTC. Every 15 minutes is 2,880 invocations in a 30-day month.
select cron.schedule(
  'vmf-fpl-probe',
  '*/15 * * * *',
  $job$
    select net.http_post(
      url := rtrim(
        (
          select decrypted_secret
            from vault.decrypted_secrets
           where name = 'vmf_api_base_url'
        ),
        '/'
      ) || '/api/cron/fpl-probe',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'Authorization', 'Bearer ' || (
          select decrypted_secret
            from vault.decrypted_secrets
           where name = 'vmf_cron_secret'
        )
      ),
      body := '{}'::jsonb,
      -- Leave room for a Vercel cold start in addition to the 15-second
      -- upstream FPL timeout configured by the API.
      timeout_milliseconds := 30000
    ) as request_id;
  $job$
);

-- Keep pg_cron history small on the 500 MB Free database.
select cron.schedule(
  'vmf-cron-history-cleanup',
  '15 3 * * *',
  $job$
    delete from cron.job_run_details
     where end_time < now() - interval '7 days'
       and jobid in (
         select jobid
           from cron.job
          where jobname in ('vmf-fpl-probe', 'vmf-cron-history-cleanup')
       );
  $job$
);
