-- Runs once on first start of the compose `db` service.
-- The test suite needs an isolated database so it can migrate and truncate
-- freely without touching learning history in `istari`.
CREATE DATABASE istari_test OWNER istari;
