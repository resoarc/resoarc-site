/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 */
import { defineApp } from '/assets/qaiuick/define.js';
import { spec } from './inventory.spec.js';

defineApp({ ...spec, baseline: '/assets/qaiuick-spec/baseline-inventory.json' });
