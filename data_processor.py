import numpy as np
import os

class DataProcessor:
    @staticmethod
    def read_data_file(file_path):
        """
        Read time difference data from DATA file
        Returns: Array of time differences (unit: 0.0125ms)
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
                
                # Filter out consecutive duplicates
                numbers = []
                if raw_numbers:
                    numbers.append(raw_numbers[0])  # Keep first value
                    for i in range(1, len(raw_numbers)):
                        if raw_numbers[i] != raw_numbers[i-1]:  # Only keep if different from previous
                            numbers.append(raw_numbers[i])
                
                print(f"DATA file processing summary:")
                print(f"Total lines: {line_count}")
                print(f"Raw values: {len(raw_numbers)}")
                print(f"After removing duplicates: {len(numbers)}")
                if numbers:
                    print(f"First few time differences: {numbers[:5]}")
                    print(f"Last few time differences: {numbers[-5:]}")
                    print(f"Time range: {min(numbers)} - {max(numbers)} (0.0125ms units)")
                    print(f"Number of zero values: {sum(1 for x in numbers if x == 0)}")
                    print(f"Removed duplicate values: {len(raw_numbers) - len(numbers)}")
                
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
                                value = int(parts[1].strip())
                                params[param_num] = value
                            except ValueError:
                                continue
                
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
        """
        Calculate distance per pulse (cm)
        P251: Speed in mm/s
        P360: Motor speed in rpm
        P361: Number of holes per wheel revolution
        """
        try:
            p251 = cf1_params.get('P0251', 0)  # Speed in mm/s
            p360 = cf1_params.get('P0360', 1)  # Motor speed in rpm
            p361 = cf1_params.get('P0361', 1)  # Holes per revolution
            p544 = cf1_params.get('P0544', 0)  # Pulses per second
            
            print("\nParameters for distance calculation:")
            print(f"P251 (Speed): {p251} mm/s")
            print(f"P360 (Motor speed): {p360} rpm")
            print(f"P361 (Holes per rev): {p361}")
            print(f"P544: {p544}")
            
            # For P544 >= 1000, use P251*60/(P360*P361)
            # Convert mm/s to cm
            distance_per_pulse = (p251/10) * 60 / (p360 * p361)  # Result in cm
            
            print(f"Distance calculation: ({p251}/10) * 60 / ({p360} * {p361})")
            print(f"Distance per pulse: {distance_per_pulse:.6f} cm")
            return distance_per_pulse
            
        except Exception as e:
            print(f"Error calculating distance per pulse: {str(e)}")
            return 0

    @staticmethod
    def generate_brake_curve(time_diffs, cf1_params):
        """
        Generate brake curve according to rule 1
        time_diffs: Array of time differences (unit: 0.0125ms)
        """
        try:
            print("\nGenerating brake curve:")
            print(f"Input time_diffs shape: {time_diffs.shape}")
            print(f"First few time_diffs: {time_diffs[:5]}")
            
            if len(time_diffs) == 0:
                print("Error: Empty time differences array")
                return {'x': np.array([]), 'y': np.array([])}
            
            # Calculate distance per pulse (cm)
            distance_per_pulse = DataProcessor.calculate_distance_per_pulse(cf1_params)
            if distance_per_pulse == 0:
                print("Error: Invalid distance per pulse")
                return {'x': np.array([]), 'y': np.array([])}
            
            print(f"Distance per pulse: {distance_per_pulse:.6f} cm")
            
            # Calculate actual time differences (ms)
            time_diffs_ms = time_diffs * 0.0125
            print(f"Time differences range: {time_diffs_ms.min():.3f} - {time_diffs_ms.max():.3f} ms")
            
            # Calculate speeds (m/s)
            velocities = np.zeros_like(time_diffs_ms)
            non_zero_mask = time_diffs_ms > 0
            
            # Calculate speeds for non-zero time differences
            # Speed = distance(cm) / time(s)
            # Convert time from ms to s: divide by 1000
            # Convert distance from cm to m: divide by 100
            velocities[non_zero_mask] = (distance_per_pulse / 100) / (time_diffs_ms[non_zero_mask] / 1000)
            
            # Time differences of 0 automatically result in speed of 0
            print(f"Calculated velocities shape: {velocities.shape}")
            print(f"Speed range: {velocities.min():.3f} - {velocities.max():.3f} m/s")
            
            # Calculate time array (s)
            times = np.cumsum(time_diffs_ms) / 1000  # Convert to seconds
            print(f"Time range: {times.min():.3f} - {times.max():.3f} s")
            print(f"Total points in curve: {len(times)}")
            
            # Only remove inf/nan values, keep zeros
            mask = ~(np.isnan(times) | np.isnan(velocities) | np.isinf(times) | np.isinf(velocities))
            times = times[mask]
            velocities = velocities[mask]
            
            print("Successfully generated curve data")
            print(f"Final curve points: {len(times)}")
            print(f"Zero time points: {np.sum(time_diffs_ms == 0)}")
            print(f"Zero speed points: {np.sum(velocities == 0)}")
            
            return {
                'x': times,
                'y': velocities
            }
            
        except Exception as e:
            print(f"Error in generate_brake_curve: {str(e)}")
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
        """
        try:
            if len(time_diffs) < 16:
                print("Not enough data points for impact detection")
                return None
                
            window_size = 16
            impact_index = None
            
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
                    impact_index = i + 12  # data13 position in current window
                    break
            
            if impact_index is not None:
                print(f"Impact detected at data point {impact_index + 1}")
                print(f"Non-zero data points: {non_zero_count}")
                return {
                    'impact_index': impact_index,
                    'non_zero_count': non_zero_count
                }
            else:
                print("No impact point detected")
                return None
                
        except Exception as e:
            print(f"Error calculating impact points: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return None 