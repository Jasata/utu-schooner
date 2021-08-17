--
-- Schooner - Simple Course Management System
-- database.create.sql / Database creation statements (types, grants, etc.)
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-13  Initial version.
--  2021-08-17  Admin ('postgres') parts only.
--
-- Execute as 'postgres'

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

-- Developer role
CREATE ROLE schooner_dev WITH
NOSUPERUSER
NOCREATEDB
NOCREATEROLE
NOREPLICATION
NOBYPASSRLS
INHERIT
PASSWORD NULL;

-- EOF