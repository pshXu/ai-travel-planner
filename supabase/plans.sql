-- Supabase: plans 表与 RLS 策略
-- 复制到 Supabase SQL Editor 执行即可（一次性）。

create table if not exists public.plans (
  id bigint generated always as identity primary key,
  user_id uuid not null,
  title text not null,
  data_json text not null,
  params_json text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 索引（提高查询与排序性能）
create index if not exists plans_user_id_idx on public.plans (user_id);
create index if not exists plans_updated_at_idx on public.plans (updated_at desc);

-- 启用行级权限（RLS）
alter table public.plans enable row level security;

-- 仅允许用户访问自己的数据
drop policy if exists "select own" on public.plans;
create policy "select own" on public.plans
  for select using (auth.uid() = user_id);

drop policy if exists "insert own" on public.plans;
create policy "insert own" on public.plans
  for insert with check (auth.uid() = user_id);

drop policy if exists "update own" on public.plans;
create policy "update own" on public.plans
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "delete own" on public.plans;
create policy "delete own" on public.plans
  for delete using (auth.uid() = user_id);

-- 自动维护 updated_at
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists plans_updated_at on public.plans;
create trigger plans_updated_at
before update on public.plans
for each row execute function public.set_updated_at();