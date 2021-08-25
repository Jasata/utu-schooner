#!/bin/bash
if [ "$(whoami)" != "schooner" ]; then
        echo "Script must be run as user: schooner"
        exit 255
fi

psql -d schooner -f core.module.sql
psql -d schooner -f email.module.sql
psql -d schooner -f assistant.module.sql
psql -d schooner -f DTEK0068-3002.sql
../enroller.py DTEK0068-3002 ../DTEK0068-3002.csv
psql -d schooner -f core.dev_data.sql
psql -d schooner -f email.dev_data.sql
psql -d schooner -f assistant.dev_data.sql
