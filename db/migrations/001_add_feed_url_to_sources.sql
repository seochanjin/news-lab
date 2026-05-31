alter table sources
add column if not exists feed_url text;

update sources
set feed_url = 'https://techcrunch.com/feed/'
where name = 'TechCrunch';

update sources
set enabled = true
where name = 'TechCrunch';

update sources
set enabled = false
where name in ('The Verge', 'Reuters');
