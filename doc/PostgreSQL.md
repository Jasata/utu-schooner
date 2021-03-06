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
- [DBeaver](https://dbeaver.io/) _Free community edition - does it create ER diagrams? YES_  
  _File -> New -> DBeaver / ER Diagram -> (choose schemas and objects, name it, go)._
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


### Step 1 - Drop existing database

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
dropdb schooner
```

### Step 2 - Create new database

Note that the users and roles are not dropped, but their privileges are gone for the dropped database. Use _selected parts of_ `sql/database.create.sql` to create the database **as `postgresql` user**.

### Step 3 - Create data structures

As user `schooner` (in directory `sql/`), execute:
```shell
./create.sh
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

## Avoid VARCHAR

_"VARCHAR is a terrible type that exists in PostgreSQL only to comply with its associated terrible part of the SQL standard. If you don't care about multi-database compatibility, consider storing your data as TEXT and add a constraint to limits its length. Constraints you can change around without this table lock/rewrite problem, and they can do more integrity checking than just the weak length check."_

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


## PostgreSQL does not have partial unique constrains

Similar effect can be achieved with partial unique indexes:
```sql
CREATE TABLE test
(
    id        INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY,
    aid       INTEGER NOT NULL,
    cid       INTEGER NOT NULL,
    category  VARCHAR(8) NOT NULL DEFAULT 'draft',
    CONSTRAINT test_category_chk
        CHECK (category IN ('draft', 'accepted', 'rejected'))
);

-- Allow only single 'draft' for combination of aid, cid and category
CREATE UNIQUE INDEX test_category_draft_unq
    ON test (aid, cid, category)
    WHERE (category = 'draft');

INSERT INTO test (aid, cid, category)
VALUES  (1, 1, 'draft'),    (1, 2, 'draft'),    (2, 1, 'draft'),
        (1, 1, 'accepted'), (1, 2, 'accepted'), (2, 1, 'accepted'),
        (1, 1, 'accepted'), (1, 2, 'accepted'), (2, 1, 'accepted'),
        (1, 1, 'rejected'), (1, 2, 'rejected'), (2, 1, 'rejected'),
        (1, 1, 'rejected'), (1, 2, 'rejected'), (2, 1, 'rejected');

INSERT INTO test (aid, cid, category)
VALUES  (1, 1, 'draft');

ERROR:  duplicate key value violates unique constraint "test_category_draft_unq"
DETAIL:  Key (aid, cid, category)=(1, 1, draft) already exists.
```

Unique constraint has few drawbacks:
- Does not allow creating foreign keys referencing that particular unique field.
- Indexes cannot be deferred, which becomes a performance issue on large bulk inserts.
- `ON CONFLICT` clause cannot be used because it requires an actual constraint.

This is still a usable approach for "attribute" -type columns, like in the above example.

## N-to-N table connecting three tables (Y-link table)

_This is a related to the above discussion about partial unique indexes._

Oracle allows:
```sql
CREATE TABLE linked
(
    item_id       INTEGER NOT NULL,
    warehouse_id  INTEGER NULL,
    store_id      INTEGER NULL,
    PRIMARY KEY (item_id, warehouse_id, store_id),
    CONSTRAINT linked_one_location_chk
        CHECK (
            (warehouse_id IS NOT NULL AND store_id IS NULL)
            OR
            (warehouse_id IS NULL AND store_id IS NOT NULL)
        )
);
```

**PostgreSQL does not.** It will enforce `NOT NULL` on all PK columns. This may be "by-the-book" according to the standards, but from a systems architect point of view, Oracle is right not to follow this one.

In addition, there is an issue how NULL values are treated. Standard approach is that anything compared to NULL is always FALSE, but for the Oracle approach to work, this comparison must yield TRUE. So, even if PostgreSQL would not enforce NOT NULL primary key columns, it still would not work in PostgreSQL.

Using PostgreSQL, we have to resort to two partial indexes to achieve the same effect:
```sql
CREATE TABLE linked
(
    item_id       INTEGER NOT NULL,
    warehouse_id  INTEGER NULL,
    store_id      INTEGER NULL,
    CONSTRAINT linked_one_location_chk
      CHECK (
          (warehouse_id IS NOT NULL AND store_id IS NULL)
          OR
          (warehouse_id IS NULL AND store_id IS NOT NULL)
      )
);
CREATE UNIQUE INDEX linked_warehouse_unq
    ON linked (item_id, warehouse_id)
    WHERE store_id IS NULL;
CREATE UNIQUE INDEX linked_store_unq
    ON linked (item_id, store_id)
    WHERE warehouse_id IS NULL;
INSERT INTO linked
VALUES (1, NULL, 1), (1, 1, NULL), (2, NULL, 1), (2, 1, NULL);
INSERT INTO linked
VALUES (1, NULL, 2), (1, 2, NULL), (2, NULL, 2), (2, 2, NULL);
-- Duplicates fail
INSERT INTO linked VALUES (1, 1, NULL);
-- Three values fail
INSERT INTO linked VALUES (1, 1, 1);
```

It should be clear that this gets untenable very fast, if the number of columns grows...

## STRICT vs CALLED ON NULL INPUT

Use `STRICT` only if you really want the function / procedure to immediately return NULL, if any of the arguments is NULL. Otherwise, use `CALLED ON NULL INPUT`...

## PL/Python - Python Procedural Language

[PostgreSQL Documentation, Chapter 46](https://www.postgresql.org/docs/11/plpython.html)

To install PL/Python in a particular database, use `CREATE EXTENSION plpythonu` (but see also Section 46.1). If a language is installed into `template1`, all subsequently created databases will have the language installed automatically.

PL/Python is only available as an ???untrusted??? language, meaning it does not offer any way of restricting what users can do in it and is therefore named `plpythonu` (the `u` suffix). A trusted variant `plpython` might become available in the future if a secure execution mechanism is developed in Python. The writer of a function in untrusted PL/Python must take care that the function cannot be used to do anything unwanted, since it will be able to do anything that could be done by a user logged in as the database administrator. Only superusers can create functions in untrusted languages such as `plpythonu`.

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


