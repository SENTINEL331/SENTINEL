
## v0.3

- Added Yahoo Finance integration
- Added historical data download
- Added CSV storage in data/raw
- Added automatic directory creation

## v0.5

- Added HistoryManager
- Separated data download from history management
- Added CSV loading
- Added latest-date detection
- Normalized Yahoo Finance data
- Improved project architecture

## v0.6

### Added
- Introduced the Feature Engine.
- Added a modular feature architecture.
- Added a Feature Registry for registering available features.
- Implemented the first market feature (Simple Moving Average).
- Added generic feature registration using `add_feature()`.
- Separated feature orchestration from feature calculations.

### Changed
- Refactored the Feature Engine into a plugin-style architecture.
- Moved SMA calculation into its own module.
- Improved separation of responsibilities between analytics components.

### Notes
This release marks Sentinel's transition from a data collection platform to an analytical platform.