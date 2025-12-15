import sys
import subprocess
import os
import json
import logging
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog, QScrollArea, QMessageBox,
    QStatusBar, QDialog, QTableWidget, QTableWidgetItem, QAbstractItemView
)
from PySide6.QtCore import Qt
from log_parser import parse_log

# --- Logger Setup ---
log_file = "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode='w', encoding='utf-8'),
        logging.StreamHandler() # Also print logs to console
    ]
)

class ReplacementsEditor(QDialog):
    """치환 규칙을 편집하기 위한 대화창"""
    def __init__(self, replacements_file, parent=None):
        super().__init__(parent)
        self.replacements_file = replacements_file
        self.setWindowTitle("치환 규칙 편집")
        self.setGeometry(200, 200, 600, 400)
        
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["원본", "치환될 문장"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.table)
        
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("행 추가")
        self.add_button.clicked.connect(self.add_row)
        button_layout.addWidget(self.add_button)
        
        self.delete_button = QPushButton("선택한 행 삭제")
        self.delete_button.clicked.connect(self.delete_row)
        button_layout.addWidget(self.delete_button)
        
        self.save_button = QPushButton("저장하고 닫기")
        self.save_button.clicked.connect(self.save_and_close)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        
        self.load_replacements()

    def load_replacements(self):
        logging.info(f"'{self.replacements_file}' 파일에서 치환 규칙을 로드합니다.")
        try:
            with open(self.replacements_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.table.setRowCount(len(data))
            for i, (key, value) in enumerate(data.items()):
                self.table.setItem(i, 0, QTableWidgetItem(key))
                self.table.setItem(i, 1, QTableWidgetItem(value))
            logging.info(f"{len(data)}개의 규칙을 로드했습니다.")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.table.setRowCount(0)
            logging.error(f"치환 규칙 파일을 로드할 수 없습니다: {e}")

    def add_row(self):
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)
        logging.info("치환 규칙 테이블에 새 행을 추가했습니다.")

    def delete_row(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "경고", "삭제할 행을 선택해주세요.")
            return
        
        for index in sorted([index.row() for index in selected_rows], reverse=True):
            self.table.removeRow(index)
        logging.info(f"{len(selected_rows)}개의 행을 삭제했습니다.")

    def save_and_close(self):
        logging.info(f"치환 규칙을 '{self.replacements_file}' 파일에 저장합니다.")
        data = {}
        for i in range(self.table.rowCount()):
            key_item = self.table.item(i, 0)
            value_item = self.table.item(i, 1)
            if key_item and value_item and key_item.text():
                data[key_item.text()] = value_item.text()
        
        try:
            with open(self.replacements_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logging.info(f"{len(data)}개의 규칙을 파일에 저장했습니다.")
            self.accept()
        except Exception as e:
            logging.error(f"파일 저장 실패: {e}")
            QMessageBox.critical(self, "오류", f"파일 저장에 실패했습니다: {e}")


class OrchestratorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        logging.info("애플리케이션 시작")
        self.setWindowTitle("번역 검수 및 수정 도구")
        self.setGeometry(100, 100, 900, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # --- 설정 ---
        self.target_file = None
        self.file_to_check = None # 가독성 처리된 파일 경로
        self.check_log_file = "language_check.log"
        self.translated_log_file = "language_proof_translated.log"
        self.replacements_file = "replacements.json"
        self.sentence_pairs = []

        # --- 위젯 ---
        self.setup_ui()

    def setup_ui(self):
        # Main action buttons
        top_layout = QHBoxLayout()
        self.select_file_button = QPushButton("1. 검수할 파일 선택")
        self.select_file_button.clicked.connect(self.select_and_run_check)
        top_layout.addWidget(self.select_file_button)

        self.apply_fix_button = QPushButton("2. 원본 파일에 수정 적용")
        self.apply_fix_button.clicked.connect(self.save_and_apply_fixes)
        self.apply_fix_button.setEnabled(False)
        top_layout.addWidget(self.apply_fix_button)
        self.main_layout.addLayout(top_layout)
        
        # Secondary action buttons
        secondary_layout = QHBoxLayout()
        self.edit_replacements_button = QPushButton("치환 규칙 편집")
        self.edit_replacements_button.clicked.connect(self.open_replacements_editor)
        secondary_layout.addWidget(self.edit_replacements_button)

        self.load_translated_log_button = QPushButton("수정본 로그 로드")
        self.load_translated_log_button.clicked.connect(self.load_translated_log)
        self.load_translated_log_button.setEnabled(False) # Initially disabled
        secondary_layout.addWidget(self.load_translated_log_button)
        self.main_layout.addLayout(secondary_layout)

        # Scroll area for results
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("준비. 시작할 파일을 선택해주세요.")

    def open_replacements_editor(self):
        logging.info("치환 규칙 편집기를 엽니다.")
        dialog = ReplacementsEditor(self.replacements_file, self)
        dialog.exec()
        logging.info("치환 규칙 편집기를 닫습니다.")
        self.status_bar.showMessage("치환 규칙 편집기 닫힘.", 3000)

    def select_and_run_check(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "대상 파일 선택", "", "로그 및 텍스트 파일 (*.log *.txt);;모든 파일 (*)")
        if not file_path:
            logging.warning("파일 선택이 취소되었습니다.")
            return

        self.target_file = file_path
        base_name = os.path.basename(self.target_file)
        logging.info(f"파일 선택됨: {self.target_file}")
        self.status_bar.showMessage(f"선택된 파일: {base_name}. 가독성 향상 처리 중...")

        self.file_to_check = self.target_file
        self.status_bar.showMessage("언어 검사를 실행합니다...")

        # 언어 검사 실행
        try:
            logging.info(f"'check_languages.py' 스크립트를 실행합니다. 대상: {self.file_to_check}")
            subprocess.run(["python", "check_languages.py", self.file_to_check], check=True, capture_output=True, text=True, encoding='utf-8')
            logging.info("언어 검사 스크립트 실행 완료.")
            self.status_bar.showMessage("언어 검사 완료. 결과를 로드합니다...")
            self.load_check_log()
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            error_message = e.stderr if hasattr(e, 'stderr') else str(e)
            logging.error(f"'check_languages.py' 실행 실패: {error_message}")
            QMessageBox.critical(self, "오류", f"'check_languages.py' 실행 실패:\n{error_message}")
            self.status_bar.showMessage("언어 검사 중 오류 발생.", 5000)

    def load_check_log(self):
        logging.info(f"'{self.check_log_file}' 파일에서 검수 결과를 로드합니다.")
        for i in reversed(range(self.scroll_layout.count())):
            layout_item = self.scroll_layout.takeAt(i)
            if layout_item.widget(): layout_item.widget().deleteLater()
            elif layout_item.layout():
                while layout_item.layout().count() > 0:
                    sub_item = layout_item.layout().takeAt(0)
                    if sub_item.widget(): sub_item.widget().deleteLater()

        self.sentence_pairs = []
        
        original_lines = parse_log(self.check_log_file)
        logging.info(f"로그 파일에서 {len(original_lines)}개의 항목을 찾았습니다.")

        if not original_lines:
            QMessageBox.warning(self, "정보", f"로그 파일 '{self.check_log_file}'을 찾을 수 없거나, 검출된 내용이 없습니다.")
            self.status_bar.showMessage("검수할 일본어 또는 중국어 문자가 없습니다.", 5000)
            self.apply_fix_button.setEnabled(False)
            self.load_translated_log_button.setEnabled(False)
            return

        for line in original_lines:
            original_text = line
            pair_layout = QHBoxLayout()
            original_label = QLabel(original_text)
            original_label.setTextFormat(Qt.PlainText)
            original_label.setWordWrap(True)
            translation_edit = QTextEdit()
            translation_edit.setPlainText(original_text)
            translation_edit.setMinimumHeight(40)
            pair_layout.addWidget(original_label, 1)
            pair_layout.addWidget(translation_edit, 1)
            self.scroll_layout.addLayout(pair_layout)
            self.sentence_pairs.append((original_label, translation_edit))
        
        self.apply_fix_button.setEnabled(True)
        self.load_translated_log_button.setEnabled(True)
        self.status_bar.showMessage(f"{len(self.sentence_pairs)}개의 검수 항목을 로드했습니다. 수정 후 버튼을 눌러주세요.")

    def load_translated_log(self):
        logging.info("수정본 로그 파일 로드를 시작합니다.")
        file_path, _ = QFileDialog.getOpenFileName(self, "수정본 로그 파일 선택", "", "로그 및 텍스트 파일 (*.log *.txt);;모든 파일 (*.txt)")
        if not file_path:
            logging.warning("수정본 로그 파일 선택이 취소되었습니다.")
            return

        parsed_lines = parse_log(file_path)

        if not parsed_lines:
            QMessageBox.critical(self, "오류", f"수정본 로그 파일을 읽는 중 오류가 발생했거나 파일 내용이 비어있습니다.")
            return

        if len(parsed_lines) != len(self.sentence_pairs):
            QMessageBox.warning(self, "경고", f"현재 표시된 항목({len(self.sentence_pairs)}개)과 불러온 로그의 항목({len(parsed_lines)}개) 수가 다릅니다. 일부만 적용될 수 있습니다.")
            logging.warning(f"항목 수 불일치: 현재 {len(self.sentence_pairs)}개, 로그 {len(parsed_lines)}개")

        for i, line in enumerate(parsed_lines):
            if i < len(self.sentence_pairs):
                _, translation_edit = self.sentence_pairs[i]
                translation_edit.setPlainText(line)
        
        self.status_bar.showMessage(f"'{os.path.basename(file_path)}' 파일에서 {len(parsed_lines)}개의 수정본을 로드했습니다.", 5000)
        logging.info(f"'{file_path}'에서 {len(parsed_lines)}개의 수정본을 로드하여 적용했습니다.")

    def save_and_apply_fixes(self):
        if not self.file_to_check:
            QMessageBox.critical(self, "오류", "대상 파일이 선택되지 않았습니다.")
            logging.error("수정 적용 실패: 대상 파일이 없습니다.")
            return

        logging.info(f"수정된 내용을 '{self.translated_log_file}' 파일에 저장합니다.")
        self.status_bar.showMessage("수정된 로그를 저장하는 중...")
        with open(self.translated_log_file, 'w', encoding='utf-8') as f:
            for _, translation_edit in self.sentence_pairs:
                translated_text = translation_edit.toPlainText().strip()
                f.write(f"{translated_text}\n")
        
        logging.info("수정된 로그 저장 완료. 원본 파일에 수정을 적용합니다.")
        self.status_bar.showMessage("수정된 로그 저장 완료. 원본 파일에 적용 중...")

        try:
            # 가독성 처리된 파일에 수정 스크립트 적용
            command = ["python", "fix_script.py", self.check_log_file, self.translated_log_file, self.file_to_check]
            logging.info(f"'fix_script.py'를 다음 인자와 함께 실행: {command}")
            subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
            
            output_filename = os.path.basename(self.file_to_check)
            QMessageBox.information(self, "성공", f"수정 사항이 성공적으로 적용되었습니다.\n결과가 '{output_filename}' 파일에 저장되었습니다.")
            logging.info(f"파일 수정 성공! 결과 파일: {output_filename}")
            self.status_bar.showMessage(f"'{output_filename}' 파일에 수정 사항 적용 완료.", 5000)
            
            # 상태 초기화
            self.target_file = None
            self.file_to_check = None
            self.apply_fix_button.setEnabled(False)
            self.load_translated_log_button.setEnabled(False)
            for i in reversed(range(self.scroll_layout.count())):
                layout_item = self.scroll_layout.takeAt(i)
                if layout_item.widget(): layout_item.widget().deleteLater()
                elif layout_item.layout():
                    while layout_item.layout().count() > 0:
                        sub_item = layout_item.layout().takeAt(0)
                        if sub_item.widget(): sub_item.widget().deleteLater()

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            error_message = e.stderr if hasattr(e, 'stderr') else str(e)
            logging.error(f"'fix_script.py' 실행 실패: {error_message}")
            QMessageBox.critical(self, "오류", f"'fix_script.py' 실행 실패:\n{error_message}")
            self.status_bar.showMessage("수정 적용 중 오류 발생.", 5000)

    def closeEvent(self, event):
        logging.info("애플리케이션 종료.")
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OrchestratorApp()
    window.show()
    sys.exit(app.exec())
