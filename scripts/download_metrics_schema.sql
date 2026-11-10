-- SPDX-FileCopyrightText: 2026 ResoArc
-- SPDX-License-Identifier: MIT
-- Aggregate successful HTTP 200 GET requests for official /downloads/*.zip files only.
-- Privacy by design: no IP address, user agent, cookies, referrer, or event-level log.
CREATE TABLE IF NOT EXISTS downloads_daily (
  date_utc TEXT NOT NULL,
  asset TEXT NOT NULL,
  hits INTEGER NOT NULL DEFAULT 0 CHECK(hits >= 0),
  PRIMARY KEY (date_utc, asset)
);
CREATE INDEX IF NOT EXISTS idx_downloads_daily_asset ON downloads_daily(asset);
