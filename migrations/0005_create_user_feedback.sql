CREATE TABLE IF NOT EXISTS user_feedback (
    correlation_id UUID PRIMARY KEY REFERENCES ai_analyses (correlation_id) ON DELETE CASCADE,
    feedback_value TEXT NOT NULL CHECK (feedback_value IN ('ACCURATE', 'INACCURATE')),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
