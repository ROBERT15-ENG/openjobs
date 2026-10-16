CREATE TABLE IF NOT EXISTS user_privacy (
    user_id INTEGER PRIMARY KEY,
    marketing_opt_in INTEGER NOT NULL DEFAULT 0,
    analytics_opt_in INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
