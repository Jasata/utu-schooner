# PostgreSQL

This file exists because Schooner is the first medium-sized application that uses PostgreSQL database, and a collected findings / experiences document is a good idea.

## Python Connectors

[PostgreSQL Wiki - Python drivers](https://wiki.postgresql.org/wiki/Python)

Any driver that has had no updates in the past 2 years is ignored.

- [AIOPG](https://aiopg.readthedocs.io/en/stable/)  
  _for `asyncio` framework (not for us)_
- [psycopg3](https://www.psycopg.org/): [GitHub repo](https://github.com/psycopg/psycopg)  
  _Python3 driver is still in **active** development for first release version, but can be used. As of 2021-08-13, version 3 has not been released on the PyPI or made available in Debian repositories. See instructions below._
- [pg8000](https://github.com/tlocke/pg8000)  
  _Pure Python 3.6+ DP-API 2.0 driver for PostgreSQL 9.6+. Actively developed._
- [py-postgresql](https://github.com/python-postgres/fe)  
  _Not very actively developed._

**CHOICE:** psycopg3 - Popular and new. The fact that it is not yet released / stable is less of an issue than now choosing to learn and use an old, soon to be replaced, connector. _GitHub project for first release version was created in 2021-08-01._

### Psycopg3 Installation

[psycopg3.dev2 install documentation](https://www.psycopg.org/psycopg3/docs/basic/install.html)

Run as `root`:
```shell
    # pip3 install git+https://github.com/psycopg/psycopg.git#subdirectory=psycopg
```

## GUI options

- [pgAdmin](https://www.pgadmin.org/) **This seems to be the go-to solution.**
- [DBeaver](https://dbeaver.io/) _Free community edition - does it create ER diagrams?_
- [OmniDB](https://omnidb.org/)
- [HeidiSQL](https://www.heidisql.com/) _New, somewhat buggy, but developed for simplicity._


## Database versions & Installation

As of 2021-08-13, newest PostgreSQL versions are 13.4 (2021-08-12) and 14.0 (beta 3). Version available from Debian Buster repository:

| Package               | Notes                                                  |
|-----------------------|--------------------------------------------------------|
| `postgresql`          | Core server files. v.11.12 in Debian 10.10 (~55 MB).   |
| `postgresql-contrib`  | Extensions and additions that are distributed along with the PostgreSQL sources, but are not (yet) officially part of the PostgreSQL core.    |

```
# apt install postgresql
Get:1 http://deb.debian.org/debian buster/main amd64 postgresql-client-common all 200+deb10u4 [85.1 kB]
Get:2 http://deb.debian.org/debian buster/main amd64 postgresql-client-11 amd64 11.12-0+deb10u1 [1,409 kB]
Get:3 http://deb.debian.org/debian buster/main amd64 ssl-cert all 1.0.39 [20.8 kB]
Get:4 http://deb.debian.org/debian buster/main amd64 postgresql-common all 200+deb10u4 [225 kB]
Get:5 http://deb.debian.org/debian buster/main amd64 postgresql-11 amd64 11.12-0+deb10u1 [14.1 MB]
Get:6 http://deb.debian.org/debian buster/main amd64 postgresql all 11+200+deb10u4 [61.1 kB]
Get:7 http://deb.debian.org/debian buster/main amd64 sysstat amd64 12.0.3-2 [562 kB]
```

- PostgreSQL client authentication is defined in the configuration file named `/etc/postgresql/11/main/pg_hba.conf`.  
  _For local connections, PostgreSQL is set to use the peer authentication method._
- The `postgres` user is automatically created when PostgreSQL is installed. This user is the superuser for the PostgreSQL instance, and it is equivalent to the MySQL root user.  
  _To log in to the PostgreSQL server as `postgres`:_  
  `sudo su - postgres`
- PostgreSQL schemas are namespaces. Each schema belongs to only one database. PostgreSQL automatically creates a schema called `public` for every new database. All new objects that do not have schema specified, will be placed into the `public` schema.
- When an object is referred without schema, PostgreSQL searches for it using "a schema search path" (list of schemas to look in). First match will be used.

## Filesystem Locations

`/etc/postgresql-common/` for common (?) configuration files.  
`/etc/postgresql/11/...` for configuration files.  
`/var/lib/postgresql/11/main/...` for datafiles (see `/etc/postgres/11/main/postgresql.conf` : `data_directory = `).



## Usage

User `postgres` is the admin account for PostgreSQL:
```shell
# sudo -u postgres psql
```
...or assume `postgresql` user identity:
```shell
# sudo su - postgres
```

### Create Database
_All examples assume `psql` shell._

```sql
    createdb schooner;
```

```sql
    createuser schooner;
```
NOTE: This appears to be `CREATE ROLE` command.

```sql
    GRANT ALL PRIVILEGES ON DATABASE schooner TO schooner;
```

```sql
\c schooner;
```
NOTE: Current database is written in the `psql` prompt.

## Useful Commands

| Action           | Meta  | SQL                                       |
|------------------|-------|-------------------------------------------|
| List databases   | `\l+` | `SELECT datname FROM pg_database;`        |
| Select database  | `\c`  |                                           |
| List tables      | `\dt` |                                           |
| Current schema   |       | `SELECT current_schema();`                |
| List roles       | `\du` |                                           |

## PL/Python - Python Procedural Language

[PostgreSQL Documentation, Chapter 46](https://www.postgresql.org/docs/11/plpython.html)

To install PL/Python in a particular database, use `CREATE EXTENSION plpythonu` (but see also Section 46.1). If a language is installed into `template1`, all subsequently created databases will have the language installed automatically.

PL/Python is only available as an “untrusted” language, meaning it does not offer any way of restricting what users can do in it and is therefore named `plpythonu` (the `u` suffix). A trusted variant `plpython` might become available in the future if a secure execution mechanism is developed in Python. The writer of a function in untrusted PL/Python must take care that the function cannot be used to do anything unwanted, since it will be able to do anything that could be done by a user logged in as the database administrator. Only superusers can create functions in untrusted languages such as `plpythonu`.

Alternatively, look into [PL/pgSQL](https://www.postgresql.org/docs/11/plpgsql.html).

