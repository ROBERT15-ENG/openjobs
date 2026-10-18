CREATE TABLE IF NOT EXISTS user_job_alerts (
  user_id INTEGER PRIMARY KEY,
  visa_sponsorship INTEGER NOT NULL DEFAULT 0,
  keywords TEXT,
  enabled INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT NOT NULL
);
