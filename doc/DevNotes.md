# Developer Notes

_This file exists for the sole purpose that I (author) revisit projects seldomly enough that I simply cannot remember all related commands or details every time. Thus, I am doing myself a service and writing some of this stuff down (and appending this as time goes...)._

## Shared development

- Ensure that all files under `/var/www/schooner.utu.fi` are set for group `www-data` and have group write permission (during development).
- Add collaborators to `www-data` group.  
  `usermod -a -G $USER www-data`
- File owner still needs to push changes to repo. This "intense collaboration mode" is obviously not recommended except for very few (2 or 3) who are in very active contact with each other ... and for only the initial stages, until features and code start to stabilize.

## Local Development Instance

_Local development instance is the preferred way, once the code has stabilized to a degree. These notes describe one possible way of setting it up._

- **A Raspberry Pi is assumed** as a local development box. Use model 3 or 4 (model 2 or earlier have VSC Remote-SSH issues).
- Masqueraded `schooner.utu.fi` via local DNS authority (at the time of writing: Raspberry#33, top shelf) **OR** edit `hosts` file of the development PC.
- Local user `pi` must be added to group `www-data` (`# usermod -a -G pi www-data`).
- Local user `pi` must own the www root (`chown -R pi.www-root /var/www/schooner.utu.fi`).
- **TODO** The installer (`setup.py`) needs to be finished. It should be used to create clean installs every once in a while. _For now, follow the documentation found in this folder..._

## Database Architecture

- Local user `schooner` (similar to `postgresql`) runs `cron` jobs (background tasks such as `hubbot`, `hubreg`, or `aplus`) and is locally authenticates when accessing the database.
- Local user `www-data` (Nginx worker processes execute as `www-data`) accesses database from Flask/Psycopg3 scripts and is also locally authenticated.

**Local system user `schooner`:**
```shell
adduser --system --no-create-home --shell /bin/bash --ingroup www-data --disabled-password --disabled-login schooner
```
_NOTE: `/sbin/nologin` gives a message ("This account is currently not available", set in `/etc/nologin.txt`). However, this prevents switcing to the user (`su - schooner`), which is necessary during development. Consider changing the shell when development needs no longer apply._

_NOTE2: User `www-data` login shell is `nologin` (`getent passwd www-data | cut -d: -f7`). If this causes issues for an Flash application, will be discovered soon..._

```SQL
-- Execute as postgres
CREATE USER schooner WITH
NOSUPERUSER
NOCREATEDB
NOCREATEROLE
NOREPLICATION
NOBYPASSRLS
INHERIT
LOGIN
PASSWORD NULL;
CREATE USER "www-data" WITH
NOSUPERUSER
NOCREATEDB
NOCREATEROLE
NOREPLICATION
NOBYPASSRLS
INHERIT
LOGIN
PASSWORD NULL;
CREATE DATABASE schooner WITH OWNER = schooner;
COMMENT ON DATABASE schooner IS
'Schooner - Simple course management system';
GRANT CONNECT ON DATABASE schooner TO "www-data";

-- reconnect here as schooner!
--REVOKE ALL ON DATABASE schooner FROM public;
--CREATE SCHEMA core AUTHORIZATION schooner;
--GRANT USAGE ON SCHEMA core to schooner_www;


```

Read also [Managing PostgreSQL Privileges](https://aws.amazon.com/blogs/database/managing-postgresql-users-and-roles/)

## Create PostgreSQL Developers

_These should be scripted later..._  
- Database `schooner`
- Role `www`
- Role `submission-robot` (used by background tasks that have write only INSERT privilege on submission -table, SELECT on others) - Sorry! Must be able to update `enrollee.github`!

_All new users/roles are by default granted the `public` role. This can become a problem if a truly read-only role is desired, as everyone can create objects to `public` schema. To fix this, the default create permission on the public schema can be revoked: `REVOKE CREATE ON SCHEMA public FROM public;`_

**Allowed characters for names**:
- Must begin with a letter [a-z].
- [`a-z`][`0-9`][`_`] are OK.  
  _Diacritical marks and dollar sign are allowed, but not recommended._  
- **NOTE:** Prefix `pg_` is reserved. Do not use.




Documentation [CREATE USER](https://www.postgresql.org/docs/12/sql-createuser.html)
```SQL
CREATE USER {name} WITH
NOCREATEDB
NOCREATEROLE
IN ROLE schooner_www, schooner_robot
PASSWORD '{password}'
VALID UNTIL '2022-01-01';
GRANT CONNECT ON DATABASE schooner TO {name};
```

## Logs

 - `/var/log/nginx/access.log`
 - `/var/log/uwsgi/app/vm.utu.fi.log`
 - `/var/www/vm.utu.fi/application.log`

