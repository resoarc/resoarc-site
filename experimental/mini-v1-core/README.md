# Mini Plugin v1.0 preparation: clean-room core

**Status: experimental 0.2.0-dev. Not a usable kintone plugin ZIP, not v1.0 and not released.**

The historical v0.1.1-beta sources and 18 signed archives have not been recovered; this implementation is independently written from the requested behavior, not a verified continuation of the historical build.

This directory contains dependency-free pure validation/transform functions and unit tests for the 18 planned mini plugins: input-template, reuse-reset, text-normalizer, field-help, save-navigation, mail-compose, list-aggregate, csv-export, attachment-count, table-row-tools, qr-code, record-toc, related-links, sticky-list, file-preview, lookup-suggest, postal-address and barcode-scan.

Run: `npm test --prefix experimental/mini-v1-core` (22 common-core tests plus 4 text-normalizer runtime tests). To generate the experimental text-normalizer plugin's independently packable source files, run `npm run build --prefix experimental/mini-v1-core`. Generated files are placed under `plugins/text-normalizer/out/src` and are NOT signed or released.

Only **text-normalizer** currently has a draft kintone PC/mobile create/edit save hook and accessible settings page. The other 17 functions have no application runtime. The generated text-normalizer source has not been installed in a tenant and is not a production-ready plugin. Outstanding work:
- Wire the other 17 features to kintone event APIs and accessible configuration screens, and harden the text-normalizer UI.
- Independently package and sign each plugin; verify runtime contents and provenance.
- Provide actual QR rendering (currently only validates the payload).
- Provide working lookup suggestions, file preview, postal service consent UI and BarcodeDetector acquisition, not just input validation.
- Test native PC/mobile edit/submit/permission scenarios in dedicated isolated test apps, repeatability and coexistence.
- Provide Japanese user documentation and performance/large-data tests.

Until all product-specific gates pass, every mini feature must remain `release_decision=hold` in the 29-item tracker. MIT license applies to this independently-authored experimental code.
