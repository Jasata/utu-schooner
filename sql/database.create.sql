--
-- Schooner - Simple Course Management System
-- database.create.sql / Database creation statements (types, grants, etc.)
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-13  Initial version.
--  2021-08-17  Admin ('postgres') parts only.
--  2021-08-19  Minor fix and formatting.
--
-- Execute as 'postgres'

CREATE USER schooner
WITH
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS
    INHERIT
    LOGIN
    PASSWORD NULL;

CREATE USER "www-data"
WITH
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS
    INHERIT
    LOGIN
    PASSWORD NULL;

-- Developer role
CREATE ROLE schooner_dev
WITH
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS
    INHERIT
    PASSWORD NULL;

-- Dev users
CREATE USER tumipo
WITH
    PASSWORD 'Furb13';
CREATE USER jasata
WITH
    PASSWORD 'T0kkur1';

GRANT schooner_dev TO tumipo;
GRANT schooner_dev TO jasata;

--
-- Database
--
CREATE DATABASE schooner
WITH
    OWNER = schooner;

COMMENT ON DATABASE schooner IS
'Schooner - Simple course management system';


GRANT CONNECT ON DATABASE schooner TO "www-data";
GRANT CONNECT ON DATABASE schooner TO schooner_dev;


-- EOF