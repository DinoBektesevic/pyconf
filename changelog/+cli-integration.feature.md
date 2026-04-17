Added CLI integration. Every `Config` subclass now exposes `add_arguments`,
`from_args`, and `from_cli` for argparse, plus `click_options` and `from_click`
for click (optional). Flat-layout dot notation is used for nested sub-configs
(e.g. `--search.n-sigma`). A new `from_string` / `to_string` contract on
`ConfigField` drives both the CLI type conversions and cleaner display-table
rendering.
