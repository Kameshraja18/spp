from __future__ import annotations

import os
from typing import Optional

from services.models.lstm_model import LSTMRiskModel, load_lstm
from services.models.rf_model import RFSeverityModel, load_rf

_lstm: Optional[LSTMRiskModel] = None
_rf: Optional[RFSeverityModel] = None


LSTM_PATH = os.getenv("LSTM_MODEL_PATH")
RF_PATH = os.getenv("RF_MODEL_PATH")


def get_lstm_model() -> Optional[LSTMRiskModel]:
    global _lstm
    if _lstm is None:
        _lstm = load_lstm(LSTM_PATH)
    return _lstm


def get_rf_model() -> Optional[RFSeverityModel]:
    global _rf
    if _rf is None:
        _rf = load_rf(RF_PATH)
    return _rf
