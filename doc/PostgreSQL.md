# PostgreSQL

_This file exists because Schooner is the first medium-sized application that uses PostgreSQL database, and a collected findings / experiences document is a good idea._

## PostgreSQL Basics

- PostgreSQL cluster/server contains one or more databases. Users / roles are shared across the server, but no data is scared across databases (PostgreSQL does not allow querying across multiple databases!). Connections are limited to specified databases.
- A database can contain one or more named schemas (namespaces) that contain tables and other objects (without name-colliding). Data can be queried across multiple schemas. [(see documentation)](https://www.postgresql.org/docs/8.1/ddl-schemas.html).
- Instead of users and roles, PostgreSQL has only roles. A role that have been granted a login privilege is analogous to a user in other database engines.

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

_Nowhere can I find any information **why** would I want to install `postgresql-contrib`. Instead, all sources just install it with an obscure reference to "useful additional" things. In this project, the package will not be installed, unless an actual reason is found to do so._

Installed packages:
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

Some basics about PostgreSQL:
- PostgreSQL client authentication is defined in the configuration file named `/etc/postgresql/11/main/pg_hba.conf`.  
  _For local connections, PostgreSQL is set to use the peer authentication method._
- The `postgres` user is automatically created when PostgreSQL is installed. This user is the superuser for the PostgreSQL instance, and it is equivalent to the MySQL root user.  
  _Assume `postgres` identity:_  `sudo su - postgres`
- PostgreSQL schemas are namespaces. Each schema belongs to only one database. PostgreSQL automatically creates a schema called `public` for every new database. All new objects that do not have schema specified, will be placed into the `public` schema.
- When an object is referred without schema, PostgreSQL searches for it using "a schema search path" (list of schemas to look in). First match will be used.

## Filesystem Locations

`/etc/postgresql-common/` for common (?) configuration files.  
`/etc/postgresql/11/...` for configuration files.  
`/var/lib/postgresql/11/main/...` for datafiles (see `/etc/postgres/11/main/postgresql.conf` : `data_directory = `).

## Enable Remote Connections

**NOTE:** PostgreSQL uses TCP port 5432.

`/etc/postgresql/12/main/postgresql.conf`:
```conf
listen_addresses = '*'
```
`/etc/postgresql/12/main/pg_hba.conf`:
```conf
# TYPE    DATABASE  USER      ADDRESS     METHOD
host      all       all       0.0.0.0/0   md5
```
_The above is super-lazy and should be more specific.. Maybe later._  

Open `ufw` port:
```shell
ufw allow 5432/tcp
```
Restart PostgreSQL server:
```shell
systemctl restart postgresql.service
```

If user `postgres` access is to be used from a remote, the role needs to be given a password.

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

| Action               | `psql`      | SQL                                                     |
|----------------------|-------------|---------------------------------------------------------|
| List databases       | `\l+`       | `SELECT datname FROM pg_database;`                      |
| Connect to database  | `\c`        |                                                         |
| List tables          | `\dt [schema.]` |                                                         |
| Current schema       |             | `SELECT current_schema();`                              |
| List schmas          | `\dn`       | `SELECT schema_name FROM information_schema.schemata;`  |
| List roles           | `\du`       |                                                         |
| DROP user            |             | `DROP OWNED BY {user}; DROP USER {user};`               |
| List functions       | `\dt [schema.]` |  |
| List sequences       | `\ds [schema.]` |  |

## Recreating the Database

Drop all connections prior to dropping the database (execute as `postgres`):
```sql
SELECT    pg_terminate_backend(pg_stat_activity.pid)
FROM      pg_stat_activity
WHERE     pg_stat_activity.datname = 'schooner'
          AND
          pid <> pg_backend_pid();
DROP DATABASE schooner;
```

**NOTE:** There is an easier way. As local user `postgres`:
```shell

```

# PostgreSQL Features

This section makes some notes about some of the PostgreSQL features, their problems and/or their usage, based on our experiences.

## Do NOT Use SERIAL -types ("auto increment")

Special kind of stupid infected PostgreSQL developers in v.8.2. With these column types, the implicit sequence **is not accessible** to anyone except the object owner, and need to have permissions explicitly granted:
```sql
GRANT USAGE, SELECT ON email_email_id_seq TO "www-data";
```
_However, for me, this did NOT solve the permission errors... All these tables remained unusable!_

Unsurprisingly, since version 10, a replacement has been provided:
```sql
email_id            INTEGER         GENERATED ALWAYS AS IDENTITY,
```
This **works**, and should be used instead. Syntax is: `GENERATED { ALWAYS | BY DEFAULT } AS IDENTITY [ ( sequence_options ) ]` where
- `ALWAYS` will use the sequence _always_, except if the INSERT statement specifies `OVERRIDING SYSTEM VALUE`. 
- `BY DEFAULT` allows user-specified value to take precedence.

**IMPORTANT! `AS IDENTITY` DOES NOT MAKE THE COLUMN AUTOMATICALLY PRIMARY KEY!**

## Unsigned Integers

PostgreSQL has none. Use of `DOMAIN` is suggested:
```sql
CREATE DOMAIN uint AS INT4
   CONSTRAINT uint_not_negative_chk
   CHECK (VALUE IS NULL OR VALUE >= 0);
```
But that doesn't seem to work as adverticed:
```sql
SELECT (-1::uint);
 ?column? 
----------
       -1
(1 row)
```
**Our solution:** We will use table constraints to enforce intended value ranges.


## PL/Python - Python Procedural Language

[PostgreSQL Documentation, Chapter 46](https://www.postgresql.org/docs/11/plpython.html)

To install PL/Python in a particular database, use `CREATE EXTENSION plpythonu` (but see also Section 46.1). If a language is installed into `template1`, all subsequently created databases will have the language installed automatically.

PL/Python is only available as an “untrusted” language, meaning it does not offer any way of restricting what users can do in it and is therefore named `plpythonu` (the `u` suffix). A trusted variant `plpython` might become available in the future if a secure execution mechanism is developed in Python. The writer of a function in untrusted PL/Python must take care that the function cannot be used to do anything unwanted, since it will be able to do anything that could be done by a user logged in as the database administrator. Only superusers can create functions in untrusted languages such as `plpythonu`.

Alternatively, look into [PL/pgSQL](https://www.postgresql.org/docs/11/plpgsql.html).

# Schooner Database

## Schema Modules

Structure for database (`schooner`) has been split into schemas:

- `core`, containing course instance data (grading system, assignments) and enrollee data (limited personal details and submissions to assignments).
- `email`, which consists of message templates and set/queued messages.
- `assistant`: structures to manage evaluation work queues.
- _Rule and Conditions_. Yet-to-be started portion, which will model conditions that can prevent progressing in the course until certain tasks or score criteria have been satisfied. (This will be 2022 addition)

## Users / Roles

_In PostgreSQL, USER is just a ROLE with a connect privilege._

- `schooner` USER  
  Owner of the database and objects. Used by `cron` jobs. Local authentication (no need for passwords).
- `www-data` USER  
  Used by uWSGI (Flask middleware). Has limited privileges.
- `schooner_dev` ROLE  
  Developer role that should have all privileges to all Schooner schemas and objects (if not, fix it!).


