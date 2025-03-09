# AdoboPDFile.py
import sys
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QPushButton, QVBoxLayout, 
                            QWidget, QLabel, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, 
                            QToolBar, QSlider, QHBoxLayout)
from PyQt5.QtGui import QPixmap, QImage, QPalette, QColor, QWheelEvent, QPainter
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, QEvent
import logging

def hex_to_rgb(hex_color):
    """Convert hex color (e.g., '#FF0000') to RGB tuple (0-1 range)."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

class AdoboPDFile(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pdf_document = None
        self.current_page = 0
        self.start_pos = None
        self.end_pos = None
        self.tool_mode = None
        self.tool_color = None
        self.selected_button = None
        self.zoom_factor = 1.0
        self.last_pos = None
        self.drawing = False
        self.initUI()
        self.setup_logging()

    def initUI(self):
        # Window setup
        self.setWindowTitle("Adobo PDFile")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)

        # Main widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Toolbar at the top
        self.toolbar = QToolBar()
        self.toolbar.setFixedHeight(40)
        self.addToolBar(self.toolbar)

        # Navigation buttons
        self.prev_btn = QPushButton("<<")
        self.prev_btn.setFixedWidth(30)
        self.prev_btn.clicked.connect(self.prev_page)
        self.toolbar.addWidget(self.prev_btn)

        self.page_label = QLabel("Page 1")
        self.page_label.setFixedWidth(60)
        self.toolbar.addWidget(self.page_label)

        self.next_btn = QPushButton(">>")
        self.next_btn.setFixedWidth(30)
        self.next_btn.clicked.connect(self.next_page)
        self.toolbar.addWidget(self.next_btn)

        # Zoom buttons
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedWidth(30)
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.toolbar.addWidget(self.zoom_in_btn)

        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setFixedWidth(30)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.toolbar.addWidget(self.zoom_out_btn)

        self.zoom_reset_btn = QPushButton("1:1")
        self.zoom_reset_btn.setFixedWidth(40)
        self.zoom_reset_btn.clicked.connect(self.zoom_reset)
        self.toolbar.addWidget(self.zoom_reset_btn)

        # Tool buttons with selection tracking
        self.highlight_red = QPushButton("H Red")
        self.highlight_red.setFixedWidth(50)
        self.highlight_red.clicked.connect(lambda: self.set_tool(self.highlight_red, "highlight", "#ff9999"))
        self.toolbar.addWidget(self.highlight_red)

        self.highlight_green = QPushButton("H Green")
        self.highlight_green.setFixedWidth(50)
        self.highlight_green.clicked.connect(lambda: self.set_tool(self.highlight_green, "highlight", "#99ff99"))
        self.toolbar.addWidget(self.highlight_green)

        self.highlight_blue = QPushButton("H Blue")
        self.highlight_blue.setFixedWidth(50)
        self.highlight_blue.clicked.connect(lambda: self.set_tool(self.highlight_blue, "highlight", "#99ccff"))
        self.toolbar.addWidget(self.highlight_blue)

        self.pencil_red = QPushButton("P Red")
        self.pencil_red.setFixedWidth(50)
        self.pencil_red.clicked.connect(lambda: self.set_tool(self.pencil_red, "pencil", "#ff0000"))
        self.toolbar.addWidget(self.pencil_red)

        self.pencil_blue = QPushButton("P Blue")
        self.pencil_blue.setFixedWidth(50)
        self.pencil_blue.clicked.connect(lambda: self.set_tool(self.pencil_blue, "pencil", "#0000ff"))
        self.toolbar.addWidget(self.pencil_blue)

        # Debug button for hardcoded annotation
        self.test_btn = QPushButton("Test Annot")
        self.test_btn.setFixedWidth(60)
        self.test_btn.clicked.connect(self.add_test_annotation)
        self.toolbar.addWidget(self.test_btn)

        # File operation buttons
        self.open_btn = QPushButton("Open")
        self.open_btn.setFixedWidth(50)
        self.open_btn.clicked.connect(self.open_pdf)
        self.toolbar.addWidget(self.open_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.setFixedWidth(50)
        self.save_btn.clicked.connect(self.save_pdf)
        self.toolbar.addWidget(self.save_btn)

        # PDF Viewer
        self.graphics_view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        self.graphics_view.setMouseTracking(True)
        self.graphics_view.setRenderHint(QPainter.Antialiasing)
        self.graphics_view.setDragMode(QGraphicsView.NoDrag)
        self.graphics_view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.layout.addWidget(self.graphics_view, stretch=1)

        # Zoom slider at the bottom
        zoom_layout = QHBoxLayout()
        zoom_label = QLabel("Zoom:")
        zoom_layout.addWidget(zoom_label)
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(20)  # 0.2x
        self.zoom_slider.setMaximum(200)  # 2.0x
        self.zoom_slider.setValue(100)  # 1.0x
        self.zoom_slider.setTickInterval(10)
        self.zoom_slider.valueChanged.connect(self.zoom_slider_changed)
        zoom_layout.addWidget(self.zoom_slider)
        zoom_widget = QWidget()
        zoom_widget.setFixedHeight(30)
        zoom_widget.setLayout(zoom_layout)
        self.layout.addWidget(zoom_widget)

        # Status label
        self.status = QLabel("Ready")
        self.status.setFixedHeight(20)
        self.layout.addWidget(self.status)

        # Splash screen
        self.splash = QLabel("Adobo PDFile", self.central_widget)
        self.splash.setAlignment(Qt.AlignCenter)
        self.splash.setStyleSheet("font-size: 36px; color: black;")
        QTimer.singleShot(2000, self.fade_splash)

    def setup_logging(self):
        logging.basicConfig(filename='adobo_pdfile.log', level=logging.DEBUG)
        self.logger = logging.getLogger('AdoboPDFile')

    def fade_splash(self):
        self.splash.setStyleSheet("font-size: 36px; color: rgba(0, 0, 0, 0);")
        QTimer.singleShot(500, self.splash.hide)

    def set_tool(self, button, mode, color):
        if self.selected_button and self.selected_button != button:
            palette = self.selected_button.palette()
            palette.setColor(QPalette.Button, QColor(Qt.lightGray))
            self.selected_button.setPalette(palette)
            self.selected_button.setAutoFillBackground(True)

        self.selected_button = button
        palette = button.palette()
        palette.setColor(QPalette.Button, QColor(Qt.blue))
        button.setPalette(palette)
        button.setAutoFillBackground(True)

        self.tool_mode = mode
        self.tool_color = color
        self.status.setText(f"Tool: {mode} ({color})")
        self.logger.debug(f"Tool set: {mode}, color: {color}")
        self.drawing = False

    def open_pdf(self):
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
            if file_name:
                self.pdf_document = fitz.open(file_name)
                self.current_page = 0
                self.zoom_factor = 1.0
                self.zoom_slider.setValue(100)
                self.display_page()
                self.page_label.setText(f"Page {self.current_page + 1} of {len(self.pdf_document)}")
                self.status.setText(f"Opened: {file_name}")
        except Exception as e:
            self.logger.error(f"Error opening PDF: {str(e)}")
            self.show_debug_window(str(e))

    def display_page(self):
        if self.pdf_document and 0 <= self.current_page < len(self.pdf_document):
            try:
                page = self.pdf_document[self.current_page]
                zoom_matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
                pix = page.get_pixmap(matrix=zoom_matrix, annots=True)
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(img)
                self.scene.clear()
                self.scene.addItem(QGraphicsPixmapItem(pixmap))
                self.graphics_view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
                self.logger.debug(f"Displayed page {self.current_page} with zoom {self.zoom_factor}, page size: {page.rect}")
            except Exception as e:
                self.logger.error(f"Error displaying page: {str(e)}")
                self.show_debug_window(str(e))

    def add_test_annotation(self):
        if self.pdf_document:
            try:
                page = self.pdf_document[self.current_page]
                rect = fitz.Rect(100, 100, 200, 150)
                annot = page.add_highlight_annot(rect)
                rgb_color = hex_to_rgb("red")  # Convert to RGB tuple
                annot.set_colors(stroke=rgb_color)
                annot.update()
                self.logger.debug(f"Test annotation added at {rect} with color {rgb_color}")
                self.status.setText("Test annotation added")
                self.display_page()
            except Exception as e:
                self.logger.error(f"Error adding test annotation: {str(e)}")
                self.show_debug_window(str(e))

    def prev_page(self):
        if self.pdf_document and self.current_page > 0:
            self.current_page -= 1
            self.display_page()
            self.page_label.setText(f"Page {self.current_page + 1} of {len(self.pdf_document)}")

    def next_page(self):
        if self.pdf_document and self.current_page < len(self.pdf_document) - 1:
            self.current_page += 1
            self.display_page()
            self.page_label.setText(f"Page {self.current_page + 1} of {len(self.pdf_document)}")

    def zoom_in(self):
        self.zoom_factor *= 1.2
        self.zoom_slider.setValue(int(self.zoom_factor * 100))
        self.display_page()

    def zoom_out(self):
        if self.zoom_factor > 0.2:
            self.zoom_factor /= 1.2
            self.zoom_slider.setValue(int(self.zoom_factor * 100))
            self.display_page()

    def zoom_reset(self):
        self.zoom_factor = 1.0
        self.zoom_slider.setValue(100)
        self.display_page()

    def zoom_slider_changed(self):
        self.zoom_factor = self.zoom_slider.value() / 100.0
        self.display_page()

    def save_pdf(self):
        if self.pdf_document:
            try:
                file_name, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")
                if file_name:
                    self.pdf_document.save(file_name)
                    self.status.setText(f"Saved as: {file_name}")
            except Exception as e:
                self.logger.error(f"Error saving PDF: {str(e)}")
                self.show_debug_window(str(e))

    def mousePressEvent(self, event):
        if event.pos().y() > 40 and event.pos().y() < self.height() - 50:
            if self.pdf_document and event.button() == Qt.LeftButton and self.tool_mode:
                pos = self.graphics_view.mapToScene(event.pos().x(), event.pos().y() - 40)
                self.start_pos = fitz.Point(pos.x() / self.zoom_factor, pos.y() / self.zoom_factor)
                self.drawing = True
                page = self.pdf_document[self.current_page]
                page_rect = page.rect
                self.start_pos.x = max(0, min(self.start_pos.x, page_rect.width))
                self.start_pos.y = max(0, min(self.start_pos.y, page_rect.height))
                self.logger.debug(f"Mouse press at scene: ({pos.x()}, {pos.y()}), adjusted: ({self.start_pos.x}, {self.start_pos.y}), zoom: {self.zoom_factor}, page rect: {page_rect}")
                # Draw a dot on click
                if self.tool_mode == "highlight":
                    annot = page.add_circle_annot(fitz.Point(self.start_pos.x, self.start_pos.y), 2)
                    rgb_color = hex_to_rgb(self.tool_color)
                    annot.set_colors(stroke=rgb_color)
                    annot.update()
                    self.display_page()
            self.last_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.pos().y() > 40 and event.pos().y() < self.height() - 50 and self.drawing and self.tool_mode:
            if self.pdf_document and self.start_pos:
                pos = self.graphics_view.mapToScene(event.pos().x(), event.pos().y() - 40)
                self.end_pos = fitz.Point(pos.x() / self.zoom_factor, pos.y() / self.zoom_factor)
                page = self.pdf_document[self.current_page]
                page_rect = page.rect
                self.end_pos.x = max(0, min(self.end_pos.x, page_rect.width))
                self.end_pos.y = max(0, min(self.end_pos.y, page_rect.height))
                self.logger.debug(f"Mouse move to: ({self.end_pos.x}, {self.end_pos.y})")

    def mouseReleaseEvent(self, event):
        if event.pos().y() > 40 and event.pos().y() < self.height() - 50:
            if self.pdf_document and self.start_pos and self.tool_mode and self.drawing:
                pos = self.graphics_view.mapToScene(event.pos().x(), event.pos().y() - 40)
                self.end_pos = fitz.Point(pos.x() / self.zoom_factor, pos.y() / self.zoom_factor)
                page = self.pdf_document[self.current_page]
                page_rect = page.rect
                
                try:
                    # Clamp coordinates to page bounds
                    self.start_pos.x = max(0, min(self.start_pos.x, page_rect.width))
                    self.start_pos.y = max(0, min(self.start_pos.y, page_rect.height))
                    self.end_pos.x = max(0, min(self.end_pos.x, page_rect.width))
                    self.end_pos.y = max(0, min(self.end_pos.y, page_rect.height))

                    if self.tool_mode == "highlight":
                        rect = fitz.Rect(min(self.start_pos.x, self.end_pos.x), min(self.start_pos.y, self.end_pos.y),
                                       max(self.start_pos.x, self.end_pos.x), max(self.start_pos.y, self.end_pos.y))
                        if rect.is_empty() or not rect.is_valid or rect.width < 1 or rect.height < 1:
                            rect = fitz.Rect(self.start_pos.x, self.start_pos.y, self.start_pos.x + 10, self.start_pos.y + 10)
                            self.logger.debug("Fixed invalid/empty rect for highlight")
                        self.logger.debug(f"Final highlight rect: {rect}, page rect: {page_rect}")
                        annot = page.add_highlight_annot(rect)
                        if annot:
                            rgb_color = hex_to_rgb(self.tool_color)
                            annot.set_colors(stroke=rgb_color)
                            annot.update()
                            self.logger.debug(f"Highlight annot created: {annot}, color: {rgb_color}")
                        else:
                            self.logger.debug("Failed to create highlight annot")
                        self.status.setText("Highlighted area")
                    
                    elif self.tool_mode == "pencil":
                        if abs(self.start_pos.x - self.end_pos.x) < 1 and abs(self.start_pos.y - self.end_pos.y) < 1:
                            self.end_pos = fitz.Point(self.start_pos.x + 10, self.start_pos.y + 10)
                            self.logger.debug("Adjusted minimal pencil drag")
                        shape = page.new_shape()
                        shape.draw_line(self.start_pos, self.end_pos)
                        rgb_color = hex_to_rgb(self.tool_color)
                        shape.finish(color=rgb_color, width=2)
                        shape.commit()
                        self.logger.debug(f"Pencil line from ({self.start_pos.x}, {self.start_pos.y}) to ({self.end_pos.x}, {self.end_pos.y})")
                        self.status.setText("Line drawn")
                    
                    self.display_page()
                except Exception as e:
                    self.logger.error(f"Error applying tool: {str(e)} with start: {self.start_pos}, end: {self.end_pos}")
                    self.show_debug_window(str(e))
                self.start_pos = None
                self.end_pos = None
                self.drawing = False

    def wheelEvent(self, event):
        if self.pdf_document:
            delta = event.angleDelta().y()
            if delta > 0:  # Scroll up
                self.prev_page()
            elif delta < 0:  # Scroll down
                self.next_page()

    def event(self, event):
        if event.type() == QEvent.Gesture:
            for gesture in event.gestures():
                if gesture.gestureType() == Qt.PinchGesture:
                    pinch = gesture
                    scale_factor = pinch.scaleFactor()
                    if scale_factor != 1.0:
                        if scale_factor > 1:
                            self.zoom_factor *= scale_factor
                        else:
                            if self.zoom_factor > 0.2:
                                self.zoom_factor *= scale_factor
                        self.zoom_slider.setValue(int(self.zoom_factor * 100))
                        self.display_page()
                    return True
        return super().event(event)

    def show_debug_window(self, error_message):
        debug_window = QWidget()
        debug_window.setWindowTitle("Debug - Crash Report")
        debug_layout = QVBoxLayout()
        debug_label = QLabel(f"Application crashed!\nError: {error_message}")
        debug_layout.addWidget(debug_label)
        debug_window.setLayout(debug_layout)
        debug_window.show()

    def mouseMoveEvent(self, event):
        if hasattr(self, 'old_pos'):
            delta = event.globalPos() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPos()

def main():
    app = QApplication(sys.argv)
    try:
        window = AdoboPDFile()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logging.error(f"Application crashed: {str(e)}")

if __name__ == '__main__':
    main()