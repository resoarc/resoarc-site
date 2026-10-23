<!-- SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project -->
<!-- SPDX-License-Identifier: MIT -->
# Corporate PHP service interruption observatory

Source of the Cloudflare Cron/KV Worker backing /api/v1/outages/php.

* Three news RSS queries discover new unverified candidates every hour.
* The registered official notices are rechecked in rotating batches of eight per hour.
* Only clear full recovery or partial recovery phrases can promote a reported status.
* HTTP website reachability is independent from the official state: at most 24 HEAD requests each hour.
* There are no user-provided crawl destinations, logins or unconfirmed candidate crawls.
* Every record includes source, evidence tier and collection time.
* Latest snapshot and up to 30 days of aggregate history are stored in Cloudflare KV.
* Deploying this code requires an independently provisioned Cloudflare Worker and KV namespace.
* The editorially curated php_cases.json is not automatically modified by RSS candidates.
* This feed cannot capture every affected website, and is not proof of a PHP-caused outage.

## Automatic news discovery and fallbacks (2026-10-24)

* Cloudflare Cron queries Google News RSS every hour for Japanese PHP-related service stop/recovery announcements.
* When Google News declines Worker requests with HTTP 503, Bing News RSS is a fallback (verified HTTP 200).
* Search results remain unverified discovery candidates and never inflate the confirmed service-status counts.
* A read-only interval-limited path /v1/php/discovery/refresh rechecks fixed RSS sources; /v1/php/discovery/diagnostics reports their reachability.
* Known first-party incident notices are revisited in rotating groups. Only explicit recovery statements can promote reported suspended/partial statuses.
* No credentials, arbitrary crawl URLs, private operational assets, or user-controlled fetch targets are exposed.
