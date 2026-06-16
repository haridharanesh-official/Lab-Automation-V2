# Room Mapping Report

## Status
- **Zone mapping status**: Completed provisionally. 6 zones have been mapped using `tools/room_mapper.py`.
- **Validation results**: Validation images have been successfully generated displaying the centres, boundary tests, and difficult edge cases (seated, door overlap).
- **Tooling**: `tools/room_mapper.py` and `tools/validate_zone_mapping.py` are now fully functional and use standard OpenCV point-in-polygon tests to correctly assign detected coordinates to the defined zones.

## Note
The current configuration in `config/zones.json` is marked provisional. It must be tested with real person-position assignments once the physical cameras and people model are fully integrated.
