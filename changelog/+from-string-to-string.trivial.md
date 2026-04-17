Renamed internal `_from_env_str` to the public `from_string` on all
`ConfigField` subclasses. Added symmetric `to_string` for display. The display
table now renders `Path`, `Dict`, `Date`, `Time`, `DateTime`, and `MultiOptions`
values cleanly instead of using raw `repr`.
