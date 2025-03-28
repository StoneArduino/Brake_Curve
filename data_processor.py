import numpy as np
import os

class DataProcessor:
    @staticmethod
    def read_data_file(file_path):
        """
        Read time difference data from DATA file with special handling:
        - First 16 values are always read
        - After that, stop reading when a value is less than previous value (include that value)
        - Stop reading when encountering zero
        """
        try:
            print(f"\nDEBUG: Reading DATA file:")
            print(f"File path: {file_path}")
            
            with open(file_path, 'rb') as f:
                content = f.read()
                
                # Check for UTF-16 BOM
                if content.startswith(b'\xff\xfe'):
                    text = content.decode('utf-16-le')
                    print("Detected UTF-16 LE encoding")
                else:
                    text = content.decode('latin1')
                    print("Using latin1 encoding")
                
                # Process the text content
                raw_numbers = []
                line_count = 0
                
                # First read all valid numbers
                for line in text.split('\n'):
                    line_count += 1
                    try:
                        line = line.strip()
                        if line:  # Only check if line is not empty
                            value = int(line)
                            raw_numbers.append(value)
                    except ValueError:
                        continue
                
                # Apply the special filtering logic
                numbers = []
                if len(raw_numbers) >= 16:
                    # Always include first 16 values
                    numbers.extend(raw_numbers[:16])
                    
                    # Process remaining values
                    last_value = numbers[-1]
                    for i in range(16, len(raw_numbers)):
                        current_value = raw_numbers[i]
                        
                        # Stop if we encounter a zero
                        if current_value == 0:
                            break
                            
                        # Include current value and stop if it decreases
                        if current_value+50 < last_value:
                            numbers.append(current_value)
                            break
                        
                        numbers.append(current_value)
                        last_value = current_value
                else:
                    # If less than 16 values, process until zero or decrease
                    last_value = None
                    for value in raw_numbers:
                        if value == 0:
                            break
                        if last_value is not None and (value+50) < last_value:  #bugfix：有时前一个会比后一个大50
                            numbers.append(value)  # Include the decreasing value
                            break
                        numbers.append(value)
                        last_value = value
                
                print(f"DATA file processing summary:")
                print(f"Total lines: {line_count}")
                print(f"Raw values: {len(raw_numbers)}")
                print(f"Processed values: {len(numbers)}")
                if numbers:
                    print(f"First 16 values: {numbers[:16]}")
                    print(f"Last few values: {numbers[-5:]}")
                    print(f"Time range: {min(numbers)} - {max(numbers)} (0.0125ms units)")
                
                return np.array(numbers)
                
        except Exception as e:
            print(f"Error reading DATA file: {str(e)}")
            return None

    @staticmethod
    def read_cf1_file(file_path):
        """
        Read parameters from CF1 file
        Returns: Dictionary of parameters
        """
        params = {}
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                
                # Check for UTF-16 BOM
                if content.startswith(b'\xff\xfe'):
                    text = content.decode('utf-16-le')
                else:
                    text = content.decode('latin1')
                
                # Process the text content
                for line in text.split('\n'):
                    line = line.strip()
                    if line.startswith('P'):
                        parts = line.split(';')
                        if len(parts) >= 2 and parts[1].strip():
                            param_num = parts[0].strip()
                            try:
                                # Special handling for P0361
                                if param_num == 'P0361':
                                    # If P0361 is not found or is 0, use default value 4
                                    value = int(parts[1].strip())
                                    if value == 0:
                                        print("P0361 is 0, using default value 4")
                                        value = 4
                                    else:
                                        value = int(parts[1].strip())
                                else:
                                    value = int(parts[1].strip())
                                params[param_num] = value
                            except ValueError:
                                if param_num == 'P0361':
                                    print("P0361 not found or invalid, using default value 4")
                                    params[param_num] = 4
                                continue
                
                # If P0361 is still not set, set default value
                if 'P0361' not in params:
                    print("P0361 not found in file, using default value 4")
                    params['P0361'] = 4
                
                # Only print key parameters
                print("\nKey parameters found:")
                for key in ['P0251', 'P0360', 'P0361', 'P0544']:
                    print(f"{key}: {params.get(key, 'Not found')}")
                
                return params
        except Exception as e:
            print(f"Error reading CF1 file: {str(e)}")
            return None

    @staticmethod
    def calculate_distance_per_pulse(cf1_params):
        """Calculate distance per pulse in centimeters"""
        try:
            # Get parameters
            speed = cf1_params.get('P0251', 0)  # mm/s
            pulses = cf1_params.get('P0544', 0)  # Hz
            
            if pulses == 0:
                print("Error: P0544 cannot be zero")
                return 0
            
            if speed == 0:
                print("Error: P0251 cannot be zero")
                return 0
            
            # Check if P0544 has non-zero thousands digit
            thousands_digit = (pulses // 1000) % 10
            
            print(f"\nParameters for distance calculation:")
            print(f"P251 (Speed): {speed} mm/s")
            print(f"P544: {pulses}")
            
            if thousands_digit > 0:
                # Case 1: Use P0360 and P0361
                motor_speed = cf1_params.get('P0360', 0)  # rpm
                holes = cf1_params.get('P0361', 0)  # holes per rev
                
                if motor_speed == 0 or holes == 0:
                    print("Error: P0360 and P0361 cannot be zero when P0544 has non-zero thousands digit")
                    return 0
                
                print(f"P360 (Motor speed): {motor_speed} rpm")
                print(f"P361 (Holes per rev): {holes}")
                # Formula: P251 * 6 / (P360 * P361)
                distance = (speed * 6) / (motor_speed * holes)  # Result in cm
                print(f"Distance calculation (Case 1): ({speed}*6)/({motor_speed}*{holes}) = {distance:.3f} cm")
                
                # Remove duplicate calculation details
                return distance
            else:
                # Case 2: Direct calculation without P0360 and P0361
                distance = speed / pulses / 10  # Result in cm
                print(f"Distance calculation (Case 2): {speed}/{pulses}/10 = {distance:.3f} cm")
                return distance
            
        except Exception as e:
            print(f"Error calculating distance per pulse: {str(e)}")
            return 0

    @staticmethod
    def generate_brake_curve(data, cf1_params):
        """Generate brake curve data"""
        try:
            # Calculate distance per pulse
            distance_per_pulse = DataProcessor.calculate_distance_per_pulse(cf1_params)
            if distance_per_pulse <= 0:
                print("Error: Invalid distance per pulse")
                return {'x': np.array([]), 'y': np.array([])}
            
            # Convert time differences to speed
            times = np.array(data)  # units of 0.0125ms
            speeds = []  # mm/s
            total_time = 0
            time_points = []
            
            # Check if using Case 1 or Case 2
            thousands_digit = (cf1_params.get('P0544', 0) // 1000) % 10
            
            print("\nProcessing time differences:")
            print(f"Distance per pulse: {distance_per_pulse} cm")
            print(f"First few raw times: {times[:5]} (units of 0.0125ms)")
            
            for t in times:
                if t > 0:
                    # Convert time from 0.0125ms units to seconds
                    t_seconds = t * 0.0125 / 1000  # Convert to seconds
                    
                    if thousands_digit > 0:
                        # Case 1: Speed calculation
                        speed = (distance_per_pulse * 100) / t_seconds  # Convert to mm/s
                    else:
                        # Case 2: Speed calculation
                        speed = (distance_per_pulse * 100) / t_seconds  # Convert to mm/s
                    
                    if len(speeds) < 5:  # Debug first few calculations
                        print(f"Time: {t} units = {t_seconds*1000:.3f} ms")
                        print(f"Speed calculation: ({distance_per_pulse}*100)/({t_seconds}) = {speed:.3f} mm/s")
                else:
                    speed = 0
                
                speeds.append(speed)
                total_time += t * 0.0125 / 1000  # Add time in seconds
                time_points.append(total_time)
            
            print(f"\nCurve generation complete:")
            print(f"Total points: {len(speeds)}")
            print(f"Time range: {time_points[0]:.3f} - {time_points[-1]:.3f} seconds")
            print(f"Speed range: {min(speeds):.3f} - {max(speeds):.3f} mm/s")
            
            return {
                'x': np.array(time_points),
                'y': np.array(speeds)
            }
            
        except Exception as e:
            print(f"Error generating brake curve: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return {'x': np.array([]), 'y': np.array([])}

    @staticmethod
    def calculate_impact_points(time_diffs, threshold=2.0):
        """
        Calculate impact points according to rule 2
        Args:
            time_diffs: Array of time differences
            threshold: Threshold value for impact detection (default: 2.0)
        Returns:
            Dictionary containing:
            - impact_index: Index of impact point
            - non_zero_count: Count of non-zero data points
            - debug_info: Dictionary containing calculation details
        """
        try:
            if len(time_diffs) < 16:
                print("Not enough data points for impact detection")
                return None
                
            window_size = 16
            impact_index = None
            debug_info = {}
            
            # Count non-zero values
            non_zero_count = np.sum(time_diffs != 0)
            
            for i in range(len(time_diffs) - window_size + 1):
                window = time_diffs[i:i+window_size]
                
                # Stop if we encounter a zero
                if window[-1] == 0:
                    break
                
                # Calculate b values (b1 to b8)
                b_values = []
                for j in range(8):
                    b = window[j+8] - window[j]
                    b_values.append(b)
                
                # Calculate c values (c1 to c4)
                c_values = []
                for j in range(4):
                    if b_values[j] == 0:  # Avoid division by zero
                        c = 0
                    else:
                        c = b_values[j+4] / b_values[j]
                    c_values.append(c)
                
                # Check threshold condition
                above_threshold = sum(c > threshold for c in c_values)
                
                if above_threshold >= 3:
                    impact_index = i + 13  # data13 position in current window
                    
                    # Store debug information
                    debug_info = {
                        'window_data': window.tolist(),
                        'b_values': b_values,
                        'c_values': c_values,
                        'above_threshold_count': above_threshold
                    }
                    break
            
            if impact_index is not None:
                print(f"\nImpact Detection Details:")
                print(f"Impact detected at data point {impact_index + 1}")
                print(f"Window data: {debug_info['window_data']}")
                print(f"B values: {[f'b{i+1}={v:.3f}' for i, v in enumerate(debug_info['b_values'])]}")
                print(f"C values: {[f'c{i+1}={v:.3f}' for i, v in enumerate(debug_info['c_values'])]}")
                print(f"Values above threshold ({threshold}): {debug_info['above_threshold_count']}")
                print(f"Non-zero data points: {non_zero_count}")
                
                return {
                    'impact_index': impact_index,
                    'non_zero_count': non_zero_count,
                    'debug_info': debug_info
                }
            else:
                print("No impact point detected")
                return None
                
        except Exception as e:
            print(f"Error calculating impact points: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return None 