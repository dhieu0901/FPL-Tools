-- Safe rollback: stop only the two VMF jobs. Other Supabase Cron jobs remain.
select cron.unschedule(jobid)
  from cron.job
 where jobname in ('vmf-fpl-probe', 'vmf-cron-history-cleanup');
