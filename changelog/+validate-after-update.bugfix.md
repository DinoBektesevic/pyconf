Fixed `Config.validate()` not being called after `Config.update()`. Cross-field invariants defined in `validate()` are now enforced on programmatic updates, not only on deserialization.
