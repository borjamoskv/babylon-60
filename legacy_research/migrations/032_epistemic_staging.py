UP = """
ALTER TABLE facts ADD COLUMN epistemic_status TEXT 
    NOT NULL DEFAULT 'staging'
    CHECK(epistemic_status IN ('staging', 'sealed', 'rejected'));

ALTER TABLE facts ADD COLUMN zk_proof TEXT;
ALTER TABLE facts ADD COLUMN sealed_at_epoch_ms BIGINT;

CREATE VIEW sealed_facts AS
SELECT * FROM facts WHERE epistemic_status = 'sealed';

-- Row Level Security: staging no legible
CREATE POLICY staging_unreadable ON facts
    FOR SELECT USING (epistemic_status != 'staging');
"""
