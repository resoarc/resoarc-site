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
