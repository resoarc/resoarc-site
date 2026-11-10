/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 */
import { defineApp } from '/assets/qaiuick/define.js';
import { spec } from './tickets.spec.js';

defineApp({ ...spec, baseline: '/assets/qaiuick-spec/baseline-tickets.json' });
