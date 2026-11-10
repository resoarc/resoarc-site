/** SPDX-FileCopyrightText: 2026 ResoArc Open Technology Project
 *  SPDX-License-Identifier: MIT
 */
import { defineApp } from '../../src/define.js';
import { spec } from './spec.js';

// The same spec as an in-memory app, with storage: 'sqlite'.
defineApp(spec);
