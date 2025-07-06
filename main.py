import sys
import os
import requests
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTextBrowser, QStackedWidget,
                             QFrame, QSizePolicy, QSpacerItem, QProgressDialog, QMessageBox,
                             QComboBox, QScrollArea, QTextEdit)
from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QPalette, QBrush, QFont, QColor, QIcon, QTextCursor


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)




class GPTWorker(QThread):
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_key, api_url, prompt):
        super().__init__()
        self.api_key = api_key
        self.api_url = api_url
        self.prompt = prompt

    def run(self):
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": self.prompt}],
                "temperature": 0.7
            }

            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                self.response_received.emit(content)
            else:
                self.error_occurred.emit("未收到有效响应")

        except Exception as e:
            self.error_occurred.emit(f"API请求错误: {str(e)}")


class RouteWorker(QThread):
    finished = pyqtSignal(str, str, str)  # airway, file_path, file_name
    error = pyqtSignal(str)

    def __init__(self, dep, arr, plat="XPLANE12"):
        super().__init__()
        self.dep = dep
        self.arr = arr
        self.plat = plat

    def run(self):
        try:
            cycle = "2506"
            url_airway = f"https://route.hkrscoc.com/api.php?dep={self.dep}&arr={self.arr}&xt=FSINN&b=AIRAC{cycle}"
            url_file = f"https://route.hkrscoc.com/api.php?dep={self.dep}&arr={self.arr}&xt={self.plat}&b=AIRAC{cycle}"

            path_way = "way"
            path_file = "file"
            os.makedirs(path_way, exist_ok=True)
            os.makedirs(path_file, exist_ok=True)

            # 下载航路文件
            way_file_name = os.path.join(path_way, f"{self.dep}-{self.arr}-FSINN.spf")
            response = requests.get(url_airway)
            with open(way_file_name, "wb") as f:
                f.write(response.content)

            # 读取航路信息
            with open(way_file_name, "r") as f:
                cont = f.readlines()
            airway = cont[-2].split("=")[-1][1:-1]

            if not airway:
                self.error.emit("未找到该航线的航路数据")
                return

            # 下载航路文件
            file_name = f"{self.dep}-{self.arr}-{self.plat}.fms"
            file_path = os.path.join(path_file, file_name)
            response = requests.get(url_file)
            with open(file_path, "wb") as f:
                f.write(response.content)

            file_name_display = f"{self.dep}{self.arr}.fms"
            self.finished.emit(airway, file_path, file_name_display)
        except Exception as e:
            self.error.emit(f"获取航路时出错: {str(e)}")


class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)

        self.default_style = """
            QPushButton {
                padding: 12px 25px;
                font-size: 16px;
                color: white;
                background-color: #0078d7;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0066b4;
            }
        """
        self.setStyleSheet(self.default_style)

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)

    def mousePressEvent(self, event):
        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self.geometry().adjusted(2, 2, -2, -2))
        self.animation.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self.geometry().adjusted(-2, -2, 2, 2))
        self.animation.start()
        super().mouseReleaseEvent(event)


class AirportInfoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QuanQuan连飞平台 / QuanQuan Virtual Flight Platform")
        pathlogo2 = os.path.join("assets", "img", "applogo.png")
        print(pathlogo2)
        self.setWindowIcon(QIcon(resource_path(pathlogo2)))

        # GPT API配置
        self.gpt_api_url = "https://api.vveai.com/v1/chat/completions"
        self.gpt_api_key = "API KEY REDACTED (YOUR API KEY HERE)"

        screen_geometry = QApplication.desktop().availableGeometry()
        self.resize(int(screen_geometry.width() * 0.8), int(screen_geometry.height() * 0.8))

        main_widget = QWidget()
        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.background_label = QLabel(main_widget)
        self.background_label.setAlignment(Qt.AlignCenter)
        self.background_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.background_label.setScaledContents(True)
        self.background_label.lower()

        pathbg = os.path.join("assets", "img", "bg.png")
        self.set_background(resource_path(pathbg))
        #self.set_background(".//assets/img/bg.png")
        #self.setStyleSheet("background-image: url('bg.png');")
        self.create_navbar()

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setAttribute(Qt.WA_TranslucentBackground)

        self.create_home_page()
        self.create_route_planning_page()
        self.create_flight_info_page()
        self.create_register_page()
        self.create_gpt_page()  # 新增GPT页面

        self.main_layout.addWidget(self.stacked_widget)
        self.setCentralWidget(main_widget)

        self.show_home_page()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_background()

    def set_background(self, image_path):
        self.background_image = QPixmap(image_path)
        if self.background_image.isNull():
            self.background_image = QPixmap(self.size())
            self.background_image.fill(QColor(30, 30, 50))
        self.update_background()

    def update_background(self):
        if hasattr(self, 'background_image'):
            scaled_pixmap = self.background_image.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            self.background_label.setPixmap(scaled_pixmap)
            self.background_label.setGeometry(0, 0, self.width(), self.height())

    def create_navbar(self):
        navbar = QFrame()
        navbar.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 40, 220);
                border-bottom: 1px solid rgba(255, 255, 255, 30);
            }
        """)
        navbar.setFixedHeight(60)

        nav_layout = QHBoxLayout(navbar)
        nav_layout.setContentsMargins(20, 0, 20, 0)
        nav_layout.setSpacing(0)

        title_layout = QHBoxLayout()
        title_layout.setSpacing(10)

        icon_label = QLabel()
        pathlogo1 = os.path.join("assets", "img", "applogo.png")
        print(pathlogo1)
        icon_label.setPixmap(QIcon(resource_path(pathlogo1)).pixmap(24, 24))
        title_label = QLabel("QuanQuan连飞平台")
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
        """)

        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)

        self.home_btn = self.create_nav_button("🏠 主页")
        self.route_btn = self.create_nav_button("🛩️ 航路规划")
        self.info_btn = self.create_nav_button("🌐 连飞信息")
        self.register_btn = self.create_nav_button("📝 注册呼号")
        self.gpt_btn = self.create_nav_button("💬 AI助手")  # 新增GPT按钮

        self.home_btn.clicked.connect(self.show_home_page)
        self.route_btn.clicked.connect(self.show_route_page)
        self.info_btn.clicked.connect(self.show_flight_info_page)
        self.register_btn.clicked.connect(self.show_register_page)
        self.gpt_btn.clicked.connect(self.show_gpt_page)  # 连接GPT页面

        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        nav_layout.addLayout(title_layout)
        nav_layout.addSpacerItem(spacer)
        nav_layout.addWidget(self.home_btn)
        nav_layout.addWidget(self.route_btn)
        nav_layout.addWidget(self.info_btn)
        nav_layout.addWidget(self.register_btn)
        nav_layout.addWidget(self.gpt_btn)  # 添加GPT按钮到导航栏

        self.main_layout.addWidget(navbar)

    def create_nav_button(self, text):
        btn = QPushButton(text)
        btn.setStyleSheet("""
            QPushButton {
                color: white;
                font-size: 16px;
                padding: 10px 20px;
                border: none;
                background: transparent;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 30);
                border-bottom: 3px solid #4fc3f7;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 50);
            }
        """)
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def create_home_page(self):
        page = QWidget()
        page.setAttribute(Qt.WA_TranslucentBackground)
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("QuanQuan连飞平台\nQuanQuan Virtual Flight Platform")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 48px; 
            color: white; 
            font-weight: bold;
            margin-bottom: 10px;
        """)

        subtitle = QLabel("专业模拟飞行联机平台\nProfessional Flight Sim VFP")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 24px; 
            color: rgba(255, 255, 255, 180);
            margin-bottom: 50px;
        """)

        start_btn = AnimatedButton("开始使用")
        start_btn.clicked.connect(self.show_flight_info_page)

        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        layout.addWidget(title, 0, Qt.AlignCenter)
        layout.addWidget(subtitle, 0, Qt.AlignCenter)
        layout.addWidget(start_btn, 0, Qt.AlignCenter)
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.stacked_widget.addWidget(page)

    def create_route_planning_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 40)

        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 40, 180);
                border-radius: 10px;
                padding: 20px;
            }
        """)

        search_layout = QVBoxLayout(search_frame)

        departure_layout = QHBoxLayout()
        departure_label = QLabel("起飞机场:")
        departure_label.setStyleSheet("font-size: 16px; color: white;")
        self.departure_input = QLineEdit()
        self.departure_input.setPlaceholderText("输入起飞机场ICAO代码 (如 ZBAA)")
        self.departure_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                font-size: 16px;
                border-radius: 5px;
                background-color: rgba(255, 255, 255, 220);
                border: 1px solid rgba(255, 255, 255, 50);
            }
            QLineEdit:focus {
                border: 1px solid #4fc3f7;
            }
        """)
        departure_layout.addWidget(departure_label)
        departure_layout.addWidget(self.departure_input)

        arrival_layout = QHBoxLayout()
        arrival_label = QLabel("落地机场:")
        arrival_label.setStyleSheet("font-size: 16px; color: white;")
        self.arrival_input = QLineEdit()
        self.arrival_input.setPlaceholderText("输入落地机场ICAO代码 (如 ZSPD)")
        self.arrival_input.setStyleSheet(self.departure_input.styleSheet())
        arrival_layout.addWidget(arrival_label)
        arrival_layout.addWidget(self.arrival_input)

        platform_layout = QHBoxLayout()
        platform_label = QLabel("模拟平台:")
        platform_label.setStyleSheet("font-size: 16px; color: white;")

        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["XPLANE12", "XPLANE11", "XPLANE10", "PMDG"])
        self.platform_combo.setStyleSheet("""
            QComboBox {
                padding: 10px;
                font-size: 16px;
                border-radius: 5px;
                background-color: rgba(255, 255, 255, 220);
                border: 1px solid rgba(255, 255, 255, 50);
                min-width: 150px;
            }
            QComboBox:hover {
                background-color: rgba(255, 255, 255, 240);
            }
            QComboBox:focus {
                border: 1px solid #4fc3f7;
            }
            QComboBox::drop-down {
                border: 0px;
                padding-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(255, 255, 255, 240);
                selection-background-color: #4fc3f7;
                border-radius: 5px;
                border: 1px solid rgba(0, 0, 0, 30);
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 5px 10px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: rgba(79, 195, 247, 50);
            }
        """)

        platform_layout.addWidget(platform_label)
        platform_layout.addWidget(self.platform_combo)

        search_btn = AnimatedButton("规划航路")
        search_btn.clicked.connect(self.plan_route)

        search_layout.addLayout(departure_layout)
        search_layout.addLayout(arrival_layout)
        search_layout.addLayout(platform_layout)
        search_layout.addWidget(search_btn, 0, Qt.AlignRight)

        self.route_display = QTextBrowser()
        self.route_display.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(255, 255, 255, 220);
                border-radius: 10px;
                padding: 20px;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                margin-top: 20px;
                border: 1px solid rgba(0, 0, 0, 20);
            }
        """)

        layout.addWidget(search_frame)
        layout.addWidget(self.route_display)

        self.stacked_widget.addWidget(page)

    def create_flight_info_page(self):
        page = QWidget()
        page.setAttribute(Qt.WA_TranslucentBackground)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)

        main_card = QFrame()
        main_card.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 40, 180);
                border-radius: 15px;
                padding: 30px;
            }
        """)

        card_layout = QVBoxLayout(main_card)

        title = QLabel("📡 连飞平台信息")
        title.setStyleSheet("""
            font-size: 28px; 
            color: white; 
            font-weight: bold; 
            margin-bottom: 30px;
            border-bottom: 2px solid #4fc3f7;
            padding-bottom: 10px;
        """)

        grid_layout = QHBoxLayout()
        left_column = QVBoxLayout()
        right_column = QVBoxLayout()

        info_items_left = [
            ("🎤 TeamSpeak IP", "39688.cn", "#4fc3f7"),
            ("🛰️ 连飞服务器IP", "39688.cn", "#4fc3f7"),
            ("👨‍✈️ 平台总管", "1234", "#4fc3f7"),
        ]

        for label, value, color in info_items_left:
            item = self.create_info_item(label, value, color)
            left_column.addLayout(item)
            left_column.addSpacing(15)

        info_items_right = [
            ("🌐 注册网页", "39688.cn", "#4fc3f7"),
            ("💬 官方QQ群", "878365469", "#4fc3f7"),
            ("✅ 平台状态", "在线", "#4fc3f7")
        ]

        for label, value, color in info_items_right:
            item = self.create_info_item(label, value, color)
            right_column.addLayout(item)
            right_column.addSpacing(15)

        grid_layout.addLayout(left_column)
        grid_layout.addSpacing(40)
        grid_layout.addLayout(right_column)

        status_indicator = QFrame()
        status_indicator.setStyleSheet("""
            QFrame {
                background-color: rgba(50, 200, 50, 150);
                border-radius: 10px;
                padding: 15px;
                margin-top: 30px;
            }
        """)

        status_layout = QHBoxLayout(status_indicator)
        status_icon = QLabel("🟢")
        status_icon.setStyleSheet("font-size: 24px;")
        status_text = QLabel("服务器运行正常，欢迎加入连飞！")
        status_text.setStyleSheet("font-size: 18px; color: white;")

        status_layout.addWidget(status_icon)
        status_layout.addWidget(status_text)
        status_layout.addStretch()

        card_layout.addWidget(title)
        card_layout.addLayout(grid_layout)
        card_layout.addWidget(status_indicator)

        layout.addWidget(main_card)
        layout.addStretch()

        self.stacked_widget.addWidget(page)

    def create_register_page(self):
        page = QWidget()
        page.setAttribute(Qt.WA_TranslucentBackground)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)

        register_frame = QFrame()
        register_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 40, 180);
                border-radius: 15px;
                padding: 40px;
            }
        """)

        frame_layout = QVBoxLayout(register_frame)
        frame_layout.setAlignment(Qt.AlignCenter)

        title = QLabel("📝 呼号注册")
        title.setStyleSheet("""
            font-size: 28px; 
            color: white; 
            font-weight: bold; 
            margin-bottom: 30px;
        """)

        icon = QLabel("✈️")
        icon.setStyleSheet("font-size: 60px; margin-bottom: 20px;")

        web_view = QLabel()
        web_view.setAlignment(Qt.AlignCenter)
        web_view.setText("""
            <html>
                <body>
                    <p style='font-size: 18px; color: white; margin-bottom: 30px;'>
                        正在为您跳转到呼号注册页面...
                    </p>
                    <p>
                        <a href='https://39688.cn' style='color: #4fc3f7; font-size: 20px; text-decoration: none;'>
                            → 点击此处立即注册 ←
                        </a>
                    </p>
                </body>
            </html>
        """)
        web_view.linkActivated.connect(self.open_url)

        frame_layout.addWidget(icon, 0, Qt.AlignCenter)
        frame_layout.addWidget(title, 0, Qt.AlignCenter)
        frame_layout.addWidget(web_view, 0, Qt.AlignCenter)

        layout.addWidget(register_frame)
        self.stacked_widget.addWidget(page)

    def create_gpt_page(self):
        """创建GPT对话页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 20)

        # 聊天显示区域
        self.chat_display = QTextBrowser()
        self.chat_display.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(30, 30, 40, 180);
                border-radius: 10px;
                padding: 20px;
                color: white;
                font-size: 16px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
        """)
        self.chat_display.setOpenExternalLinks(True)

        # 添加欢迎消息
        welcome_msg = """
            <div style='color: #4fc3f7; font-weight: bold;'>AI助手:</div>
            <div style='margin-bottom: 15px;'>
                您好！我是您的飞行AI助手，可以回答关于模拟飞行、航路规划、飞行操作等各种问题。
                <br>请问有什么可以帮您的吗？
            </div>
        """
        self.chat_display.append(welcome_msg)

        # 输入区域
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 40, 180);
                border-radius: 10px;
                padding: 15px;
                margin-top: 20px;
            }
        """)

        input_layout = QVBoxLayout(input_frame)

        # 用户输入框
        self.user_input = QTextEdit()
        self.user_input.setPlaceholderText("输入您的问题...")
        self.user_input.setStyleSheet("""
            QTextEdit {
                padding: 12px;
                font-size: 16px;
                border-radius: 5px;
                background-color: rgba(255, 255, 255, 220);
                border: 1px solid rgba(255, 255, 255, 50);
                min-height: 80px;
            }
            QTextEdit:focus {
                border: 1px solid #4fc3f7;
            }
        """)

        # 发送按钮
        send_btn = AnimatedButton("发送")
        send_btn.clicked.connect(self.send_to_gpt)

        # 清空按钮
        clear_btn = AnimatedButton("清空对话")
        clear_btn.setStyleSheet("""
            QPushButton {
                padding: 12px 25px;
                font-size: 16px;
                color: white;
                background-color: #f44336;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        clear_btn.clicked.connect(self.clear_chat)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(send_btn)

        input_layout.addWidget(self.user_input)
        input_layout.addLayout(btn_layout)

        layout.addWidget(self.chat_display)
        layout.addWidget(input_frame)

        self.stacked_widget.addWidget(page)

    def send_to_gpt(self):
        """发送消息到GPT API"""
        user_message = self.user_input.toPlainText().strip()
        if not user_message:
            QMessageBox.warning(self, "输入错误", "请输入您的问题")
            return

        # 显示用户消息
        user_html = f"""
            <div style='color: #81c784; font-weight: bold; margin-top: 15px;'>您:</div>
            <div style='margin-bottom: 15px;'>{user_message}</div>
        """
        self.chat_display.append(user_html)
        self.user_input.clear()

        # 显示"思考中"消息
        #thinking_html = """
        #    <div style='color: #4fc3f7; font-weight: bold;'>AI助手:</div>
        #    <div style='margin-bottom: 15px;'>
        #        <i>思考中...</i>
        #    </div>
        #"""
        #self.chat_display.append(thinking_html)

        # 滚动到底部
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

        # 创建并启动GPT工作线程
        self.gpt_worker = GPTWorker(self.gpt_api_key, self.gpt_api_url, user_message)
        self.gpt_worker.response_received.connect(self.display_gpt_response)
        self.gpt_worker.error_occurred.connect(self.display_gpt_error)
        self.gpt_worker.start()

    def display_gpt_response(self, response):
        """显示GPT的回复"""
        # 移除"思考中"消息
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.BlockUnderCursor)
        cursor.removeSelectedText()

        # 添加实际回复
        response_html = f"""
            <div style='color: #4fc3f7; font-weight: bold;'>AI助手:</div>
            <div style='margin-bottom: 15px;'>{response}</div>
        """
        self.chat_display.append(response_html)

        # 滚动到底部
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def display_gpt_error(self, error_msg):
        """显示GPT错误"""
        # 移除"思考中"消息
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.BlockUnderCursor)
        cursor.removeSelectedText()

        # 添加错误消息
        error_html = f"""
            <div style='color: #ff5252; font-weight: bold;'>AI助手:</div>
            <div style='margin-bottom: 15px;'>
                抱歉，出现错误: {error_msg}
                <br>请稍后再试或检查您的网络连接。
            </div>
        """
        self.chat_display.append(error_html)

        # 滚动到底部
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def clear_chat(self):
        """清空聊天记录"""
        self.chat_display.clear()
        # 重新添加欢迎消息
        welcome_msg = """
            <div style='color: #4fc3f7; font-weight: bold;'>AI助手:</div>
            <div style='margin-bottom: 15px;'>
                您好！我是您的飞行AI助手，可以回答关于模拟飞行、航路规划、飞行操作等各种问题。
                <br>请问有什么可以帮您的吗？
            </div>
        """
        self.chat_display.append(welcome_msg)

    def create_info_item(self, label, value, color):
        layout = QHBoxLayout()

        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            font-size: 18px; 
            color: white; 
            min-width: 180px;
        """)

        value_widget = QLabel(value)
        value_widget.setStyleSheet(f"""
            font-size: 18px; 
            color: {color};
        """)

        if label == "🌐 注册网页":
            value_widget.setStyleSheet(f"""
                font-size: 18px; 
                color: {color}; 
                text-decoration: underline;
            """)
            value_widget.setCursor(Qt.PointingHandCursor)
            value_widget.mousePressEvent = lambda e: self.open_url("https://39688.cn")

        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        layout.addStretch()

        return layout

    def show_home_page(self):
        self.stacked_widget.setCurrentIndex(0)
        self.update_nav_buttons(self.home_btn)

    def show_route_page(self):
        self.stacked_widget.setCurrentIndex(1)
        self.update_nav_buttons(self.route_btn)

    def show_flight_info_page(self):
        self.stacked_widget.setCurrentIndex(2)
        self.update_nav_buttons(self.info_btn)

    def show_register_page(self):
        self.stacked_widget.setCurrentIndex(3)
        self.update_nav_buttons(self.register_btn)
        self.open_url("https://39688.cn")

    def show_gpt_page(self):
        """显示GPT页面"""
        self.stacked_widget.setCurrentIndex(4)
        self.update_nav_buttons(self.gpt_btn)

    def update_nav_buttons(self, active_button):
        for btn in [self.home_btn, self.route_btn, self.info_btn, self.register_btn, self.gpt_btn]:
            if btn == active_button:
                btn.setStyleSheet("""
                    QPushButton {
                        color: white;
                        font-size: 16px;
                        padding: 10px 20px;
                        border: none;
                        background-color: rgba(0, 120, 215, 150);
                        border-bottom: 3px solid #4fc3f7;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        color: white;
                        font-size: 16px;
                        padding: 10px 20px;
                        border: none;
                        background: transparent;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 255, 255, 30);
                        border-bottom: 3px solid #4fc3f7;
                    }
                """)

    def open_url(self, url):
        import webbrowser
        webbrowser.open(url)

    def plan_route(self):
        departure = self.departure_input.text().strip().upper()
        arrival = self.arrival_input.text().strip().upper()
        platform = self.platform_combo.currentText()

        if not departure or not arrival:
            QMessageBox.warning(self, "输入错误", "请输入起飞机场和落地机场的ICAO代码")
            return

        if len(departure) != 4 or len(arrival) != 4:
            QMessageBox.warning(self, "输入错误", "机场ICAO代码必须是4个字母")
            return

        progress = QProgressDialog("正在获取航路信息...", "取消", 0, 0, self)
        progress.setWindowTitle("请稍候")
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)
        progress.show()

        self.route_worker = RouteWorker(departure, arrival, platform)
        self.route_worker.finished.connect(lambda a, f, n: self.on_route_planning_finished(a, f, n, progress))
        self.route_worker.error.connect(lambda e: self.on_route_planning_error(e, progress))
        self.route_worker.start()

    def on_route_planning_finished(self, airway, file_path, file_name, progress):
        progress.close()

        result = f"{self.departure_input.text()} → {self.arrival_input.text()} 航路规划\n"
        result += "=" * 40 + "\n"
        result += f"航路: {airway}\n\n"
        result += f"航路文件已保存: {file_name}"

        self.route_display.setPlainText(result)
        QMessageBox.information(self, "成功", "航路规划完成！")

    def on_route_planning_error(self, error_msg, progress):
        progress.close()
        QMessageBox.critical(self, "错误", error_msg)
        self.route_display.setPlainText(f"获取航路失败: {error_msg}")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = AirportInfoApp()
    window.show()
    sys.exit(app.exec_())