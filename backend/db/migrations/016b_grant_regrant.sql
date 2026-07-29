-- Migration 016b: re-grant styxproxy per-table perms on tables where ownership was reassigned
-- (styxproxy was the previous owner; after REASSIGN OWNED BY, it kept no GRANTs)

GRANT SELECT, INSERT, UPDATE, DELETE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public TO styxproxy;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO styxproxy;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO styxproxy;
