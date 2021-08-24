#!/bin/bash
if [ "$(whoami)" != "schooner" ]; then
        echo "Script must be run as user: schooner"
        exit 255
fi

psql -d schooner -f core.module.sql
psql -d schooner -f DTE20068-3002.sql
psql -d schooner -f core.dev_data.sql
psql -d schooner -f email.module.sql
psql -d schooner -f email.dev_data.sql
psql -d schooner -f assistant.module.sql
psql -d schooner -f assistant.dev_data.sql
