CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL CHECK (length(trim(device_id)) > 0),
    schema_version TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    sensor_status TEXT NOT NULL
        CHECK (sensor_status IN ('online', 'offline', 'unknown')),
    classification_label TEXT
        CHECK (classification_label IS NULL OR classification_label IN (
            'Teacher Discussion', 'Student Conversation'
        )),
    classification_confident BOOLEAN NOT NULL,
    classification_observed_at TIMESTAMPTZ,
    classification_status TEXT NOT NULL
        CHECK (classification_status IN (
            'fresh', 'stale', 'unavailable', 'unknown', 'invalid_time'
        )),
    sound_level_value DOUBLE PRECISION,
    sound_level_unit TEXT
        CHECK (sound_level_unit IS NULL OR sound_level_unit = 'dB_SPL'),
    sound_level_calibrated BOOLEAN NOT NULL,
    sound_level_observed_at TIMESTAMPTZ,
    sound_level_status TEXT NOT NULL
        CHECK (sound_level_status IN (
            'fresh', 'stale', 'unavailable', 'unknown', 'invalid_time'
        )),
    warning_triggered BOOLEAN NOT NULL,
    warning_reason TEXT NOT NULL
);

CREATE INDEX idx_events_received_at
    ON events (received_at DESC, event_id);

CREATE INDEX idx_events_device_received_at
    ON events (device_id, received_at DESC, event_id);
