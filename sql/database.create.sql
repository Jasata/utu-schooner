--
-- Schooner - Simple Course Management System
-- database.create.sql / Database creation statements (types, grants, etc.)
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-13  Initial version.
--


--
--  2021-08-13  Initial structure.
--  2021-08-08  Redesign for simplicity and improved readability.
--
CREATE DATABASE schooner;
CREATE ROLE schooner;
GRANT ALL PRIVILEGES ON DATABASE schooner TO schooner;


-- https://www.postgresql.org/docs/9.1/datatype-enum.html
CREATE TYPE active_t AS ENUM ('active', 'inactive');
