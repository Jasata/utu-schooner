#!/bin/bash
#       Black        0;30     Dark Gray     1;30
#       Red          0;31     Light Red     1;31
#       Green        0;32     Light Green   1;32
#       Brown/Orange 0;33     Yellow        1;33
#       Blue         0;34     Light Blue    1;34
#       Purple       0;35     Light Purple  1;35
#       Cyan         0;36     Light Cyan    1;36
#       Light Gray   0;37     White         1;37
RED='\033[0;31m'
NC='\033[0m' # No Color

if [ "$(whoami)" != "schooner" ]; then
        echo "Script must be run as user: schooner"
        exit 255
fi

psql -d schooner -f system.module.sql
psql -d schooner -f core.module.sql
psql -d schooner -f email.module.sql
psql -d schooner -f assistant.module.sql
psql -d schooner -f DTEK0068-3002.sql
printf "${RED}Executing enroller.py${NC}\n"
../enroller.py --map nettiopsu DTEK0068-3002 csv/DTEK0068-3002.csv
psql -d schooner -f core.dev_data.sql
psql -d schooner -f email.dev_data.sql
psql -d schooner -f assistant.dev_data.sql
