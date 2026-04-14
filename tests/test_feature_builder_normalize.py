from services.stream import feature_builder


def test_normalize_message_from_single_record():
    msg = {
        "road_segment_id": "S1",
        "timestamp": "2024-01-01T00:00:00Z",
        "avg_speed": 50,
        "flow": 100,
        "occupancy": 0.5,
        "congestion_index": 0.6,
        "rain_intensity": 0.1,
    }
    normalized = feature_builder._normalize_message(msg)
    assert "recent_sequence" in normalized
    assert normalized["recent_sequence"]
    assert normalized["road_segment_id"] == "S1"


def test_window_respects_maxlen():
    feature_builder._windows.clear()
    seg = "S2"
    for i in range(feature_builder.WINDOW_SIZE + 3):
        msg = {
            "road_segment_id": seg,
            "timestamp": f"2024-01-01T00:{i:02d}:00Z",
            "avg_speed": i,
            "flow": i,
            "occupancy": 0.1,
            "congestion_index": 0.2,
            "rain_intensity": 0.0,
        }
        enriched = feature_builder.build_features(msg)
    assert len(feature_builder._windows[seg]) == feature_builder.WINDOW_SIZE
    assert "rolling_avg_speed" in enriched
