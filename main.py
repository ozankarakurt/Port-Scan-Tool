import sys
import subprocess
import re
import time
import webbrowser

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLineEdit, QLabel,
    QStackedWidget, QProgressBar, QMessageBox, QFileDialog, QDialog
)

from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer

# =========================
# IP VALIDATION
# =========================
def is_valid_ip(ip):
    pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?:/[0-9]{1,2})?$"
    return re.match(pattern, ip)

# =========================
# AKICI İLERLEME THREAD'İ
# =========================
class ScanThread(QThread):
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

    def __init__(self, command):
        super().__init__()
        self.command = command
        self._running = True
        self.current_progress = 0

    def run(self):
        self.output_signal.emit(f"[INFO] İşlem başlatıldı: {' '.join(self.command)}\n")
        
        process = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        while self._running:
            line = process.stdout.readline()
            
            if line:
                self.output_signal.emit(line)
            
            if not line and process.poll() is not None:
                break
                
            if self.current_progress < 99:
                self.current_progress += 1
                self.progress_signal.emit(self.current_progress)
                time.sleep(0.08)

            if not self._running:
                process.terminate()
                self.output_signal.emit("\n[INFO] İşlem durduruldu.\n")
                return

        error = process.stderr.read()
        if error:
            self.output_signal.emit("\n[HATA]\n" + error)

        self.progress_signal.emit(100)
        self.output_signal.emit("\n[INFO] İşlem başarıyla tamamlandı.\n")

    def stop(self):
        self._running = False

# =========================
# ANA PENCERE
# =========================
class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("PORT TARAMA KONTROL PANELİ")
        self.setGeometry(100, 100, 1250, 750)
        
        self.history = []
        self.all_reports = "" 
        self.thread = None

        self.setStyleSheet("""
            QWidget { background-color: #050505; color: #ff3b3b; font-family: Consolas; }
            QPushButton { background-color: rgba(20,20,20,0.8); border: 1px solid #ff3b3b; border-radius: 8px; padding: 15px; font-size: 18px; font-weight: bold; color: white; }
            QPushButton:hover { background-color: #ff3b3b; color: black; }
            QLineEdit { background-color: #111; border: 1px solid #ff3b3b; border-radius: 5px; padding: 15px; font-size: 20px; color: #00ff99; }
            QTextEdit { background-color: #000; border: 1px solid #333; color: #00ff99; font-size: 14px; }
            QProgressBar { border: 1px solid #ff3b3b; text-align: center; color: white; height: 20px; border-radius: 10px; }
            QProgressBar::chunk { background-color: #ff3b3b; border-radius: 9px; }
            QLabel { color: #ff3b3b; }
        """)

        self.stack = QStackedWidget()
        
        # Sayfalar
        self.splash_page = QWidget() # Açılış Ekranı
        self.menu_page = QWidget()
        self.home_page = QWidget()
        self.scan_page = QWidget()
        self.ip_page = QWidget()
        self.report_page = QWidget()

        self.stack.addWidget(self.splash_page)
        self.stack.addWidget(self.menu_page)
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.scan_page)
        self.stack.addWidget(self.ip_page)
        self.stack.addWidget(self.report_page)

        self.create_splash()
        self.create_menu()
        self.create_home()
        self.create_scan_display()
        self.create_ip()
        self.create_report_display()

        layout = QVBoxLayout()
        layout.addWidget(self.stack)
        self.setLayout(layout)

        # Uygulama açıldığında Splash ekranını göster ve 3 sn sonra menüye geç
        QTimer.singleShot(3000, lambda: self.safe_transition(self.menu_page))

    # =========================
    # ARAYÜZ TASARIMLARI
    # =========================

    def create_splash(self):
        layout = QVBoxLayout(self.splash_page)
        layout.setAlignment(Qt.AlignCenter)
        
        logo = QLabel("OZAN KARAKURT\nCYBER SECURITY SUITE")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("font-size: 45px; font-weight: bold; letter-spacing: 5px;")
        layout.addWidget(logo)

        self.splash_label = QLabel("Sistem dosyaları yükleniyor...")
        self.splash_label.setAlignment(Qt.AlignCenter)
        self.splash_label.setStyleSheet("font-size: 18px; color: gray; margin-top: 20px;")
        layout.addWidget(self.splash_label)

        self.splash_bar = QProgressBar()
        self.splash_bar.setFixedWidth(500)
        self.splash_bar.setMaximum(0) # Sonsuz yükleme animasyonu
        layout.addWidget(self.splash_bar, alignment=Qt.AlignCenter)

    def safe_transition(self, target_page):
        """Sayfalar arası yumuşak geçiş simülasyonu"""
        self.stack.setCurrentWidget(target_page)

    def create_menu(self):
        layout = QVBoxLayout(self.menu_page)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("ANA KONTROL PANELİ")
        title.setStyleSheet("font-size:35px; font-weight:bold; margin-bottom: 30px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        btns = [
            ("PORT TARAMA ÜNİTESİ", lambda: self.safe_transition(self.home_page)),
            ("AĞ KEŞİF (IP BULMA)", lambda: self.safe_transition(self.ip_page)),
            ("TARAMA RAPORLARI", self.update_and_show_reports),
            ("YAPIMCI BİLGİSİ", self.show_dev)
        ]

        for text, func in btns:
            btn = QPushButton(text)
            btn.setFixedWidth(500)
            btn.clicked.connect(func)
            layout.addWidget(btn, alignment=Qt.AlignCenter)

    def create_home(self):
        layout = QVBoxLayout(self.home_page)
        
        back_btn = QPushButton("← ANA MENÜ")
        back_btn.setFixedWidth(150)
        back_btn.clicked.connect(lambda: self.safe_transition(self.menu_page))
        layout.addWidget(back_btn)

        title = QLabel("HEDEF IP ANALİZİ")
        title.setStyleSheet("font-size:28px; font-weight:bold; margin: 10px 0;")
        layout.addWidget(title)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Hedef IP veya Alan Adı girin (örn: 192.168.1.1)")
        layout.addWidget(self.ip_input)

        grid = QVBoxLayout()
        tarama_tipleri = [
            ("HIZLI PORT TARAMA (1-100)", ["nmap", "-p", "1-100"]),
            ("TAM PORT TARAMA (1-65535)", ["nmap", "-p-"]),
            ("SERVİS VE VERSİYON ANALİZİ", ["nmap", "-sV"]),
            ("İŞLETİM SİSTEMİ TESPİTİ", ["nmap", "-O"])
        ]

        for text, cmd in tarama_tipleri:
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, c=cmd: self.start_scan(c))
            grid.addWidget(btn)
        
        layout.addLayout(grid)

    def create_scan_display(self):
        layout = QVBoxLayout(self.scan_page)
        
        nav = QHBoxLayout()
        back = QPushButton("← DURDUR VE GERİ")
        back.clicked.connect(self.stop_and_back)
        
        clear = QPushButton("EKRANI TEMİZLE")
        clear.clicked.connect(lambda: self.scan_output.clear())
        
        hist = QPushButton("GEÇMİŞİ GÖR")
        hist.clicked.connect(self.show_history)

        nav.addWidget(back)
        nav.addWidget(clear)
        nav.addWidget(hist)
        layout.addLayout(nav)

        self.scan_progress = QProgressBar()
        layout.addWidget(self.scan_progress)

        self.scan_output = QTextEdit()
        self.scan_output.setReadOnly(True)
        layout.addWidget(self.scan_output)

    def create_report_display(self):
        layout = QVBoxLayout(self.report_page)
        
        bar = QHBoxLayout()
        back = QPushButton("← ANA MENÜ")
        back.clicked.connect(lambda: self.safe_transition(self.menu_page))
        
        save = QPushButton("💾 RAPORU DOSYAYA YAZ (.txt)")
        save.clicked.connect(self.export_to_file)
        
        bar.addWidget(back)
        bar.addWidget(save)
        layout.addLayout(bar)

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        layout.addWidget(self.report_text)

    def create_ip(self):
        layout = QVBoxLayout(self.ip_page)
        
        back = QPushButton("← ANA MENÜ")
        back.setFixedWidth(150)
        back.clicked.connect(lambda: self.safe_transition(self.menu_page))
        layout.addWidget(back)

        self.net_input = QLineEdit()
        self.net_input.setPlaceholderText("Ağ Bloğu Girin (örn: 192.168.1.0/24)")
        layout.addWidget(self.net_input)

        self.ip_output = QTextEdit()
        self.ip_output.setReadOnly(True)
        layout.addWidget(self.ip_output)

        btn = QPushButton("AĞI TARA VE CİHAZLARI BUL")
        btn.clicked.connect(self.scan_network)
        layout.addWidget(btn)

    # =========================
    # KONTROL MANTIKLARI
    # =========================

    def stop_and_back(self):
        self.stop_scan()
        self.safe_transition(self.home_page)

    def start_scan(self, cmd_base):
        ip = self.ip_input.text().strip()
        if not is_valid_ip(ip):
            QMessageBox.critical(self, "Hata", "Lütfen geçerli bir IP adresi girin!")
            return

        full_cmd = cmd_base + [ip]
        self.history.append(f"[{time.strftime('%H:%M:%S')}] {ip} -> {' '.join(cmd_base)}")
        
        self.scan_output.clear()
        self.scan_progress.setValue(0)
        self.safe_transition(self.scan_page)

        self.thread = ScanThread(full_cmd)
        self.thread.output_signal.connect(self.handle_scan_output)
        self.thread.progress_signal.connect(self.scan_progress.setValue)
        self.thread.start()

    def handle_scan_output(self, text):
        self.scan_output.append(text)
        self.all_reports += text

    def scan_network(self):
        net = self.net_input.text().strip()
        if not is_valid_ip(net):
            QMessageBox.warning(self, "Hata", "Geçersiz ağ adresi!")
            return

        self.ip_output.clear()
        self.thread = ScanThread(["nbtscan", net])
        self.thread.output_signal.connect(lambda t: (self.ip_output.append(t), setattr(self, 'all_reports', self.all_reports + t)))
        self.thread.start()

    def stop_scan(self):
        if self.thread and self.thread.isRunning():
            self.thread.stop()

    def update_and_show_reports(self):
        self.report_text.setText(self.all_reports if self.all_reports else "Veritabanında kayıtlı rapor bulunamadı.")
        self.safe_transition(self.report_page)

    def export_to_file(self):
        content = self.report_text.toPlainText()
        if not content.strip() or "bulunamadı" in content:
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Raporu Kaydet", "siber_analiz.txt", "Metin Dosyası (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    def show_history(self):
        QMessageBox.information(self, "Tarama Geçmişi", "\n".join(self.history) if self.history else "Geçmiş temiz.")

    def show_dev(self):
        dev_dialog = QDialog(self)
        dev_dialog.setWindowTitle("YAPIMCI")
        dev_dialog.setFixedSize(400, 300)
        dev_dialog.setStyleSheet("background-color: #050505; color: #ff3b3b; border: 1px solid #ff3b3b;")
        
        layout = QVBoxLayout()
        l1 = QLabel("OZAN KARAKURT")
        l1.setAlignment(Qt.AlignCenter)
        l1.setStyleSheet("font-size: 24px; font-weight: bold; border: none;")
        layout.addWidget(l1)

        l2 = QLabel("Cyber Security Student & Developer")
        l2.setAlignment(Qt.AlignCenter)
        l2.setStyleSheet("color: gray; border: none;")
        layout.addWidget(l2)

        lbtn = QPushButton("LinkedIn Profilini Görüntüle")
        lbtn.setStyleSheet("background-color: #0077b5; color: white; border: none; margin: 10px;")
        lbtn.clicked.connect(lambda: webbrowser.open("https://www.linkedin.com/in/ozan-karakurt-6a36bb39a/"))
        layout.addWidget(lbtn)
        
        close = QPushButton("Kapat")
        close.clicked.connect(dev_dialog.close)
        layout.addWidget(close)
        
        dev_dialog.setLayout(layout)
        dev_dialog.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())