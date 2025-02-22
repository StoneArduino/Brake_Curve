import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QPushButton, 
                            QVBoxLayout, QHBoxLayout, QWidget, QLabel, QGroupBox,
                            QSpinBox, QDoubleSpinBox, QStyle, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPalette, QColor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
from data_processor import DataProcessor

class BrakeCurveApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Escalator Brake Curve Analyzer')
        
        # Initialize SpinBox controls
        self.speed_spin = QSpinBox()
        self.motor_spin = QSpinBox()
        self.holes_spin = QSpinBox()
        self.pulses_spin = QSpinBox()
        
        # Initialize buttons
        self.data_btn = QPushButton("Select DATA File")
        self.cf1_btn = QPushButton("Select CF1 File")
        self.plot_btn = QPushButton("Generate Curve")
        self.animate_btn = QPushButton("Animate Curve")
        
        # Initialize labels
        self.data_label = QLabel("No file selected")
        self.cf1_label = QLabel("No file selected")
        self.calc_label = QLabel()
        self.calc_label.setWordWrap(True)
        
        # Initialize data
        self.data_file = None
        self.cf1_file = None
        self.data = None
        self.cf1_params = None
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_index = 0
        
        # Add threshold input
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 10.0)
        self.threshold_spin.setValue(2.0)
        self.threshold_spin.setSingleStep(0.1)
        
        # Add braking distance label
        self.braking_label = QLabel()
        self.braking_label.setWordWrap(True)
        self.braking_label.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                padding: 10px;
                border-radius: 4px;
                color: #1565C0;
                margin-top: 10px;
            }
        """)
        
        # Set window properties
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                border: 2px solid #2196F3;
                border-radius: 8px;
                margin-top: 1.5em;
                padding: 10px;
                font-weight: bold;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #1976D2;
                background-color: white;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QLabel {
                font-size: 12px;
                color: #333333;
            }
            QSpinBox {
                padding: 4px;
                border: 1px solid #BBDEFB;
                border-radius: 4px;
                min-width: 80px;
                background-color: #FFFFFF;
            }
            QSpinBox:hover {
                border-color: #2196F3;
            }
            QSpinBox:focus {
                border-color: #1976D2;
            }
        """)
        
        # Connect button signals
        self.data_btn.clicked.connect(self.select_data_file)
        self.cf1_btn.clicked.connect(self.select_cf1_file)
        self.plot_btn.clicked.connect(self.plot_curve)
        self.animate_btn.clicked.connect(self.toggle_animation)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Create left panel for controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(350)
        left_panel.setMinimumWidth(300)
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout()
        file_layout.setSpacing(10)
        
        # Add file selection widgets with better layout
        data_file_widget = QWidget()
        data_file_layout = QVBoxLayout(data_file_widget)
        data_file_layout.setSpacing(5)
        data_file_layout.addWidget(self.data_btn)
        data_file_layout.addWidget(self.data_label)
        
        cf1_file_widget = QWidget()
        cf1_file_layout = QVBoxLayout(cf1_file_widget)
        cf1_file_layout.setSpacing(5)
        cf1_file_layout.addWidget(self.cf1_btn)
        cf1_file_layout.addWidget(self.cf1_label)
        
        file_layout.addWidget(data_file_widget)
        file_layout.addWidget(cf1_file_widget)
        file_group.setLayout(file_layout)
        
        # Parameters group with better layout
        param_group = QGroupBox("Parameters")
        param_layout = QVBoxLayout()
        param_layout.setSpacing(15)
        
        # Create parameter widgets with consistent layout
        def create_param_widget(label_text, spin_box, default_value, value_range):
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            label = QLabel(label_text)
            label.setMinimumWidth(150)
            spin_box.setRange(*value_range)
            spin_box.setValue(default_value)
            spin_box.valueChanged.connect(self.update_parameters)
            layout.addWidget(label)
            layout.addWidget(spin_box)
            return widget
        
        # Create parameter widgets
        speed_widget = create_param_widget("P251 - Speed (mm/s):", self.speed_spin, 670, (0, 1000))
        motor_widget = create_param_widget("P360 - Motor Speed (rpm):", self.motor_spin, 1500, (0, 2000))
        holes_widget = create_param_widget("P361 - Holes per Rev:", self.holes_spin, 4, (1, 10))
        pulses_widget = create_param_widget("P544 - Pulses/s:", self.pulses_spin, 5017, (0, 10000))
        
        # Create threshold widget
        threshold_widget = create_param_widget(
            "Impact Threshold:", 
            self.threshold_spin, 
            2.0, 
            (0.1, 10.0)
        )
        param_layout.addWidget(speed_widget)
        param_layout.addWidget(motor_widget)
        param_layout.addWidget(holes_widget)
        param_layout.addWidget(pulses_widget)
        param_layout.addWidget(threshold_widget)
        param_layout.addWidget(self.braking_label)
        
        # Add calculated values display with better styling
        self.calc_label = QLabel()
        self.calc_label.setWordWrap(True)
        self.calc_label.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                padding: 10px;
                border-radius: 4px;
                color: #1565C0;
                margin-top: 10px;
            }
        """)
        param_layout.addWidget(self.calc_label)
        
        param_group.setLayout(param_layout)
        
        # Control buttons with better layout
        control_group = QGroupBox("Controls")
        control_layout = QVBoxLayout()
        control_layout.setSpacing(10)
        
        control_layout.addWidget(self.plot_btn)
        control_layout.addWidget(self.animate_btn)
        control_group.setLayout(control_layout)
        
        # Add groups to left panel
        left_layout.addWidget(file_group)
        left_layout.addWidget(param_group)
        left_layout.addWidget(control_group)
        left_layout.addStretch()
        
        # Create right panel for plot with better styling
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        # Create matplotlib figure with better styling
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.ax.set_xlabel('Time (s)', fontsize=10)
        self.ax.set_ylabel('Speed (m/s)', fontsize=10)
        self.ax.set_title('Brake Curve', fontsize=12, pad=15)
        
        right_layout.addWidget(self.canvas)
        
        # Add panels to main layout
        layout.addWidget(left_panel)
        layout.addWidget(right_panel, stretch=1)

    def select_data_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select DATA File", "", "DATA Files (*.data);;All Files (*)")
        if file_name:
            self.data_file = file_name
            self.data_label.setText(file_name.split('/')[-1])
            self.data = self.read_data_file()

    def select_cf1_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select CF1 File", "", "CF1 Files (*.CF1);;All Files (*)")
        if file_name:
            self.cf1_file = file_name
            self.cf1_label.setText(file_name.split('/')[-1])
            self.cf1_params = self.read_cf1_file()
            if self.cf1_params:
                self.speed_spin.setValue(self.cf1_params.get('P0251', 670))
                self.motor_spin.setValue(self.cf1_params.get('P0360', 1500))
                self.holes_spin.setValue(self.cf1_params.get('P0361', 4))
                self.pulses_spin.setValue(self.cf1_params.get('P0544', 5017))
                self.update_parameters()

    def update_parameters(self):
        if not self.cf1_params:
            self.cf1_params = {}
        self.cf1_params['P0251'] = self.speed_spin.value()
        self.cf1_params['P0360'] = self.motor_spin.value()
        self.cf1_params['P0361'] = self.holes_spin.value()
        self.cf1_params['P0544'] = self.pulses_spin.value()
        
        # Update calculated values display
        distance_per_pulse = (self.cf1_params['P0251']/10) * 60 / (self.cf1_params['P0360'] * self.cf1_params['P0361'])
        self.calc_label.setText(
            f"Calculated Values:\n"
            f"Distance per pulse: {distance_per_pulse:.6f} cm\n"
            f"Nominal speed: {self.cf1_params['P0251']/1000:.3f} m/s"
        )

    def plot_curve(self):
        try:
            # Check if data is available
            if self.data is None or self.cf1_params is None:
                print("Error: Missing data or parameters")
                return
            
            if len(self.data) == 0:
                print("Error: Empty data array")
                return
                
            print("\nPlotting curve with parameters:")
            print(f"P251 (Speed): {self.cf1_params.get('P0251')} mm/s")
            print(f"P360 (Motor Speed): {self.cf1_params.get('P0360')} rpm")
            print(f"P361 (Holes per Rev): {self.cf1_params.get('P0361')}")
            print(f"P544 (Pulses/s): {self.cf1_params.get('P0544')}")
            print(f"\nData points: {len(self.data)}")
            print(f"First few time differences: {self.data[:5]}")
            print(f"Last few time differences: {self.data[-5:]}")
                
            self.ax.clear()
            curve_data = self.generate_brake_curve(self.data, self.cf1_params)
            
            if curve_data['x'].size == 0 or curve_data['y'].size == 0:
                print("Error: No valid curve data generated")
                return
            
            self.ax.plot(curve_data['x'], curve_data['y'])
            self.ax.grid(True)
            self.ax.set_xlabel('Time (s)')
            self.ax.set_ylabel('Speed (m/s)')
            
            # Update title to show all parameters
            title = (f'Brake Curve\n'
                    f'P251: {self.cf1_params.get("P0251")} mm/s, '
                    f'P360: {self.cf1_params.get("P0360")} rpm\n'
                    f'P361: {self.cf1_params.get("P0361")}, '
                    f'P544: {self.cf1_params.get("P0544")}')
            
            # Calculate impact points
            impact_data = DataProcessor.calculate_impact_points(
                self.data, 
                self.threshold_spin.value()
            )
            
            if impact_data:
                impact_index = impact_data['impact_index']
                non_zero_count = impact_data['non_zero_count']
                
                # Draw impact line
                impact_time = curve_data['x'][impact_index]
                self.ax.axvline(x=impact_time, color='red', linestyle='--', label='Impact Point')
                
                # Calculate braking distance
                distance_per_pulse = DataProcessor.calculate_distance_per_pulse(self.cf1_params)
                braking_pulses = non_zero_count - impact_index
                braking_distance = braking_pulses * distance_per_pulse
                
                # Update braking distance display
                self.braking_label.setText(
                    f"Braking Analysis:\n"
                    f"Impact Point: Data #{impact_index + 1}\n"
                    f"Non-zero Data Points: {non_zero_count}\n"
                    f"Braking Distance: {braking_distance:.2f} cm"
                )
                
                # Update plot title
                title += f"\nImpact at {impact_time:.2f}s, Braking Distance: {braking_distance:.2f}cm"
            
            self.ax.set_title(title)
            self.ax.legend()
            self.canvas.draw()
            
            # Store curve data for animation
            self.curve_data = curve_data
            print("\nCurve statistics:")
            print(f"Time range: {curve_data['x'].min():.3f} - {curve_data['x'].max():.3f} s")
            print(f"Speed range: {curve_data['y'].min():.3f} - {curve_data['y'].max():.3f} m/s")
            print(f"Total points plotted: {len(curve_data['x'])}")
            
        except Exception as e:
            print(f"Error in plot_curve: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

    def toggle_animation(self):
        if self.animation_timer.isActive():
            self.animation_timer.stop()
            self.animate_btn.setText("Animate Curve")
        else:
            self.animation_index = 0
            self.animation_timer.start(50)  # 50ms interval
            self.animate_btn.setText("Stop Animation")

    def update_animation(self):
        if not hasattr(self, 'curve_data'):
            self.animation_timer.stop()
            return
            
        self.ax.clear()
        end_idx = min(self.animation_index + 10, len(self.curve_data['x']))
        self.ax.plot(self.curve_data['x'][:end_idx], self.curve_data['y'][:end_idx])
        self.ax.grid(True)
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Speed (m/s)')
        self.ax.set_title('Brake Curve')
        
        # Set fixed axis limits
        self.ax.set_xlim(0, max(self.curve_data['x']))
        self.ax.set_ylim(0, max(self.curve_data['y']) * 1.1)
        
        self.canvas.draw()
        
        self.animation_index = end_idx
        if end_idx >= len(self.curve_data['x']):
            self.animation_timer.stop()
            self.animate_btn.setText("Animate Curve")

    def read_data_file(self):
        return DataProcessor.read_data_file(self.data_file)
        
    def read_cf1_file(self):
        return DataProcessor.read_cf1_file(self.cf1_file)
        
    def generate_brake_curve(self, data, cf1_params):
        return DataProcessor.generate_brake_curve(data, cf1_params)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = BrakeCurveApp()
    window.show()
    sys.exit(app.exec_()) 