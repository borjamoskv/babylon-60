{{
    config(
        materialized = "table",
        description = "Core integration layer. Calculates total Exergy yield and isolates high-signal interactions."
    )
}}

WITH base_extraction AS (
    SELECT * FROM {{ ref('stg_exergy_extraction') }}
),

-- Subquery for identifying sessions with optimal cognitive friction (Exergy > 80)
high_signal_sessions AS (
    SELECT session_id
    FROM base_extraction
    WHERE safe_friction_score > 80
),

exergy_aggregation AS (
    SELECT
        session_id,
        normalized_device,
        MAX(interaction_time) AS last_interaction,
        AVG(safe_friction_score) AS session_exergy_yield
    FROM base_extraction
    -- OPTIMIZACION C5-REAL APLICADA: Sustitución MANDATORIA de IN por EXISTS
    -- [EVITADO]: WHERE session_id IN (SELECT session_id FROM high_signal_sessions)
    WHERE EXISTS (
        SELECT 1 
        FROM high_signal_sessions 
        WHERE high_signal_sessions.session_id = base_extraction.session_id
    )
    GROUP BY session_id, normalized_device
)

SELECT * FROM exergy_aggregation
