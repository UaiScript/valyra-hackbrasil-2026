-- Em volume novo, cria só o banco dedicado. Em volume existente, executar este
-- arquivo com psql explicitamente; não remover o volume para reaplicar o init.
SELECT 'CREATE DATABASE valyra_test'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'valyra_test')
\gexec
