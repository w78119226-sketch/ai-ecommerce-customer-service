from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget


class PlatformsPage(QWidget):
    PLATFORMS = ("抖音 / 飞鸽", "千牛", "拼多多", "快手", "小红书", "网页客服", "微信小程序")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        box = QGroupBox("平台连接")
        form = QFormLayout(box)
        for name in self.PLATFORMS:
            form.addRow(name, QLabel("未配置"))
        layout = QVBoxLayout(self)
        layout.addWidget(box)
        layout.addStretch(1)
