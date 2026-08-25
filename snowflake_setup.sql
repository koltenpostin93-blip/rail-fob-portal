-- ============================================================================
-- One-time setup: GitHub Git integration + Streamlit-in-Snowflake hosting
-- for rail-fob-portal (koltenpostin93-blip/rail-fob-portal, public, branch
-- master). Run this in a Snowsight worksheet as a role with
-- CREATE INTEGRATION / CREATE NETWORK RULE privileges (ACCOUNTADMIN, or a
-- custom role granted those specifically).
--
-- Before running: replace the REPLACE_ME_* placeholders. Never commit this
-- file back to the repo with real values filled in — the repo is public.
-- ============================================================================

USE ROLE ACCOUNTADMIN;

-- 1. Database/schema to hold this app (reuse across future app migrations —
--    add a schema per app rather than a new database each time).
CREATE DATABASE IF NOT EXISTS JSA_APPS;
CREATE SCHEMA IF NOT EXISTS JSA_APPS.RAIL_FOB;
USE DATABASE JSA_APPS;
USE SCHEMA RAIL_FOB;

-- 2. Warehouse to run the app on. XSMALL + short auto-suspend keeps this
--    close to free for a low-traffic internal tool.
CREATE WAREHOUSE IF NOT EXISTS APPS_WH
  WAREHOUSE_SIZE = XSMALL
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE;

-- 3. GitHub API integration — public repo, no auth/credentials needed.
--    API_ALLOWED_PREFIXES scopes this to your GitHub account; reuse it for
--    future repos under the same account instead of creating a new one.
CREATE OR REPLACE API INTEGRATION jsa_github_api
  API_PROVIDER = git_https_api
  API_ALLOWED_PREFIXES = ('https://github.com/koltenpostin93-blip')
  ENABLED = TRUE;

-- 4. Git repository object cloning rail-fob-portal into Snowflake.
CREATE OR REPLACE GIT REPOSITORY rail_fob_repo
  API_INTEGRATION = jsa_github_api
  ORIGIN = 'https://github.com/koltenpostin93-blip/rail-fob-portal.git';

-- Pull the current commit down; re-run this any time the repo updates
-- (there's a "Pull" button in Snowsight too, under the app's Files tab).
ALTER GIT REPOSITORY rail_fob_repo FETCH;

-- Sanity check — should list app.py, environment.yml, rail_data.py, etc.
LS @rail_fob_repo/branches/master/;

-- 5. Network rule allowing outbound access to the Supabase Postgres pooler
--    (the basis tracker's DB this app reads from).
CREATE OR REPLACE NETWORK RULE supabase_egress_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('aws-1-ca-central-1.pooler.supabase.com:5432');

-- 6. The DB connection string as a Snowflake secret — never plaintext in
--    code or in this file once filled in. Paste your real BASIS_DATABASE_URL
--    (from rail-fob-portal/.env locally) in place of REPLACE_ME below,
--    run it, then clear it from your worksheet/history if you're on a
--    shared account.
CREATE OR REPLACE SECRET rail_fob_db_secret
  TYPE = GENERIC_STRING
  SECRET_STRING = 'REPLACE_ME_WITH_YOUR_BASIS_DATABASE_URL';

-- 7. External access integration tying the network rule + secret together —
--    this is what CREATE STREAMLIT references to let the app dial out.
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION rail_fob_egress
  ALLOWED_NETWORK_RULES = (supabase_egress_rule)
  ALLOWED_AUTHENTICATION_SECRETS = (rail_fob_db_secret)
  ENABLED = TRUE;

-- 8. The Streamlit app itself, sourced directly from the Git repo clone.
--    SECRETS maps the Snowflake secret to the name rail_data.py looks up via
--    _snowflake.get_generic_secret_string("BASIS_DATABASE_URL").
CREATE OR REPLACE STREAMLIT rail_fob_sheet
  FROM @rail_fob_repo/branches/master/
  MAIN_FILE = 'app.py'
  QUERY_WAREHOUSE = APPS_WH
  EXTERNAL_ACCESS_INTEGRATIONS = (rail_fob_egress)
  SECRETS = ('BASIS_DATABASE_URL' = rail_fob_db_secret);

-- 9. Let your own role (or a team role) open the app if you're not already
--    using ACCOUNTADMIN day to day.
-- GRANT USAGE ON STREAMLIT rail_fob_sheet TO ROLE <your_role>;

-- Done — find the app under Projects > Streamlit in Snowsight, or grab its
-- shareable URL from SHOW STREAMLITS;
SHOW STREAMLITS LIKE 'rail_fob_sheet';
