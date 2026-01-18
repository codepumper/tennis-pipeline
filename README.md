# Workflow

client goes to endpoint

https://www.sofascore.com/api/v1/sport/tennis/scheduled-events/2026-01-18

the endpoint returns all scheduled tennis events for the date 2026-01-18 in JSON format. we need to select the relevant events for our pipeline, so we filter only the events that has tournament.name equal to "Australian Open, Melbourne, Australia"
then extract all match ids from the filtered events.

add rate limiting to avoid overwhelming the server, e.g., wait 1 second between requests.
```sh
docker exec -it prefect-server prefect gcl create sofascore-api --limit 1 --slot-decay-per-second 0.1
```

set prefect backend to localhost
```sh
prefect config set PREFECT_API_URL="http://localhost:5200/api"
```