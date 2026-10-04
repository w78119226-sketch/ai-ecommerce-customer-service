from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QPushButton, QVBoxLayout, QWidget


class DashboardPage(QWidget):
    start_requested = Signal()
    stop_requested = Signal()
    logs_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.backend_status = QLabel("已停止")
        self.model_label = QLabel("DeepSeek")
        self.api_status = QLabel("未连接")
        self.store_count = QLabel("0")
        self.worker_count = QLabel("0")
        status_box = QGroupBox("运行状态")
        form = QFormLayout(status_box)
        form.addRow("后端状态", self.backend_status)
        form.addRow("当前模型", self.model_label)
        form.addRow("Decision API", self.api_status)
        form.addRow("已连接店铺", self.store_count)
        form.addRow("运行 Worker", self.worker_count)
        start = QPushButton("启动客服服务")
        stop = QPushButton("停止客服服务")
        logs = QPushButton("打开日志目录")
        start.clicked.connect(self.start_requested)
        stop.clicked.connect(self.stop_requested)
        logs.clicked.connect(self.logs_requested)
        actions = QGroupBox("操作")
        action_layout = QVBoxLayout(actions)
        for button in (start, stop, logs):
            action_layout.addWidget(button)
        layout = QVBoxLayout(self)
        layout.addWidget(status_box)
        layout.addWidget(actions)
        layout.addStretch(1)

    def set_state(self, status: str, api_ok: bool, provider: str) -> None:
        labels = {"running": "运行中", "starting": "启动中", "error": "异常", "stopped": "已停止"}
        self.backend_status.setText(labels.get(status, status))
        self.api_status.setText("正常" if api_ok else "未连接")
        self.model_label.setText("OpenClaw" if provider in {"agent", "openclaw"} else "DeepSeek")
