-- Idempotent Supabase Cron setup for the VMF synchronization job.
--
-- Before running this file, create exactly these two Supabase Vault secrets:
--   vmf_api_base_url  = https://<your-api-project>.vercel.app
--   vmf_cron_secret   = the same value as CRON_SECRET in the Vercel API project
--
-- Do not paste either secret into this tracked SQL file.
--
-- Cadence trade-off on the free plan: the rulebook targets a 60-second live
-- refresh, but every tick costs one Vercel function invocation and several FPL
-- requests. Five minutes keeps a full month inside the Hobby quota. Raise the
-- frequency for live Gameweeks only after checking the Vercel usage page.

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
-- pg_cron uses UTC. Every 5 minutes is 8,640 invocations in a 30-day month.
select cron.schedule(
  'vmf-fpl-sync',
  '*/5 * * * *',
  $job$
    select net.http_post(
      url := rtrim(
        (
          select decrypted_secret
            from vault.decrypted_secrets
           where name = 'vmf_api_base_url'
        ),
        '/'
      ) || '/api/cron/sync',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'Authorization', 'Bearer ' || (
          select decrypted_secret
            from vault.decrypted_secrets
           where name = 'vmf_cron_secret'
        )
      ),
      body := '{}'::jsonb,
      -- The job fans out to several FPL endpoints, so it needs more headroom
      -- than the read-only probe.
      timeout_milliseconds := 120000
    ) as request_id;
  $job$
);

-- The five-minute job is as fast as it can be: it re-reads every manager's
-- squad and entry history, a request each, so forty-six managers make it far
-- too heavy to run often. What a spectator actually watches - the match clock
-- and the points on it - costs two requests, so it gets its own schedule and
-- runs every minute. It is a no-op outside a Gameweek in play, and it takes
-- the same lock as the full sync, so the two never write over each other.
--
-- Every minute is as often as anything can usefully be read: FPL publishes
-- its live feed in bursts, not continuously, so a faster schedule would ask
-- for numbers that cannot have changed.
select cron.schedule(
  'vmf-fpl-live',
  '* * * * *',
  $job$
    select net.http_post(
      url := rtrim(
        (
          select decrypted_secret
            from vault.decrypted_secrets
           where name = 'vmf_api_base_url'
        ),
        '/'
      ) || '/api/cron/live-sync',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'Authorization', 'Bearer ' || (
          select decrypted_secret
            from vault.decrypted_secrets
           where name = 'vmf_cron_secret'
        )
      ),
      body := '{}'::jsonb,
      -- Two upstream reads and a rescore. It must finish well inside its own
      -- minute, so it is given far less rope than the full sync.
      timeout_milliseconds := 45000
    ) as request_id;
  $job$
);

-- The five-minute job compares player and team fields every tick, so a
-- transfer or a new arrival is already picked up there. What it never
-- revisits is each manager's own FPL entry, which the nightly audit reads so
-- that a team renamed mid-season is reported rather than going unnoticed.
--
-- 18:30 UTC is 01:30 in Asia/Bangkok: after midnight for the organisers, well
-- clear of FPL deadlines, and after the day's matches have finished.
select cron.schedule(
  'vmf-nightly-audit',
  '30 18 * * *',
  $job$
    select net.http_post(
      url := rtrim(
        (
          select decrypted_secret
            from vault.decrypted_secrets
           where name = 'vmf_api_base_url'
        ),
        '/'
      ) || '/api/cron/nightly-audit',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'Authorization', 'Bearer ' || (
          select decrypted_secret
            from vault.decrypted_secrets
           where name = 'vmf_cron_secret'
        )
      ),
      body := '{}'::jsonb,
      -- Forty manager lookups, so it needs the same headroom as the sync.
      timeout_milliseconds := 120000
    ) as request_id;
  $job$
);

-- Keep pg_cron history small on the 500 MB Free database. The minute job
-- alone writes 1,440 rows a day, so this matters more than it used to.
select cron.schedule(
  'vmf-cron-history-cleanup',
  '15 3 * * *',
  $job$
    delete from cron.job_run_details
     where end_time < now() - interval '7 days'
       and jobid in (
         select jobid
           from cron.job
          where jobname in (
            'vmf-fpl-sync',
            'vmf-fpl-live',
            'vmf-fpl-probe',
            'vmf-nightly-audit',
            'vmf-cron-history-cleanup'
          )
       );
  $job$
);
