--
-- Schooner - Simple Course Management System
-- admin.sql / Privileged users for SSO module
-- University of Turku / Faculty of Technology / Department of Computing
-- Jani Tammi <jasata@utu.fi>
--
--  2021-08-13  Initial version.
--
--
-- Instructs UI and API code to treat the user as Admin, if his/her SSO ID
-- is listed in this table (and it is of 'active' status). Inactive status
-- causes the user be treated as a regular user instead.
-- Admin privilege allows access to views that alter course data
-- (create new instances, add/modify assignments, etc.)
--
-- Teachers, assistants, etc. roles are recorded into the appropriate
-- joining/attached tables.
--
CREATE TABLE admin
(
    uid                 VARCHAR(10)     NOT NULL PRIMARY KEY,
    created             TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status              active_t        NOT NULL DEFAULT 'active'
);

