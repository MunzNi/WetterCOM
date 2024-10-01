#!/bin/sh
CRON_SCHEDULE=${CRON_SCHEDULE:-"0 * * * *"}
echo "$CRON_SCHEDULE /usr/local/bin/python /app/scrape.py >> /var/log/cron.log 2>&1" | crontab -
cron && tail -f /var/log/cron.log
