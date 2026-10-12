#!/bin/bash
# Health check alerting — sends email if any service is down
ADMIN_EMAIL="sonnyagent30@gmail.com"
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
ALERT_MSG=""

# Check API
if ! curl -sf http://127.0.0.1:8000/api/v1/health > /dev/null 2>&1; then
    ALERT_MSG="${ALERT_MSG}API is DOWN\n"
fi

# Check PostgreSQL
if ! sudo -u postgres psql -c "SELECT 1" > /dev/null 2>&1; then
    ALERT_MSG="${ALERT_MSG}PostgreSQL is DOWN\n"
fi

# Check Redis
if ! redis-cli ping > /dev/null 2>&1; then
    ALERT_MSG="${ALERT_MSG}Redis is DOWN\n"
fi

# Check Docker containers
for container in styxproxy-grafana styxproxy-loki styxproxy-n8n; do
    if ! docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        ALERT_MSG="${ALERT_MSG}Docker ${container} is DOWN\n"
    fi
done

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 85 ]; then
    ALERT_MSG="${ALERT_MSG}Disk usage ${DISK_USAGE}%\n"
fi

# Send alert if needed
if [ -n "$ALERT_MSG" ]; then
    echo -e "Styxproxy Health Alert - $TIMESTAMP\n\n$ALERT_MSG" | /usr/bin/sendmail "$ADMIN_EMAIL"
    echo "Alert sent"
else
    echo "All services healthy"
fi
