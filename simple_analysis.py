import os
import re
from collections import defaultdict
import statistics

LOG_FILE = 'batch_07_20_17_31.log'
assert os.path.exists(LOG_FILE), "Log file does not exist."

def parse_log_file(log_file):
    """Parse the log file and extract test case results."""
    with open(log_file, 'r') as f:
        contents = f.read().strip()
    
    # Split by test case headers
    test_sections = contents.split('# ---------- ')[1:]  # Skip the first empty section
    last, summary = test_sections[-1].split('# Summary: ')
    test_sections[-1] = last.strip()  # Clean up the last section
    total_cases = int(re.search(r'(\d+) testcases processed', summary).group(1))
    failures = int(re.search(r'(\d+) failures', summary).group(1))
    assert total_cases == len(test_sections), "Mismatch between total cases and parsed sections"
    
    results = []
    for section in test_sections:
        lines = section.strip().split('\n')
        if not lines:
            continue
            
        # Extract test case name from first line
        test_name = lines[0].replace(' ----------', '').strip()
        
        # Initialize result dict
        result = {
            'test_name': test_name,
            'success': False,
            'user_cycles': None,
            'gen_time': None,
            'verify_time': None,
            'proof_size': None,
            'segments': None,
            'decision': None,
            'expected_decision': None,
            'inputs': {}
        }
        
        # Parse the content
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
                
            # Parse inputs
            if line.startswith('Parsed inputs:'):
                inputs_str = line.replace('Parsed inputs: Inputs { ', '').replace(' }', '')
                if inputs_str.strip():
                    # Parse input fields
                    input_pairs = re.findall(r'(\w+): ([^,}]+)', inputs_str)
                    for key, value in input_pairs:
                        # Clean up the value (remove quotes)
                        value = value.strip('"').strip("'")
                        result['inputs'][key] = value
            
            # Parse performance metrics
            elif line.startswith('Number of segments:'):
                result['segments'] = int(line.split(':')[1].strip())
            elif line.startswith('User cycles:'):
                result['user_cycles'] = int(line.split(':')[1].strip())
            elif line.startswith('Proof size:'):
                size_str = line.split(':')[1].strip().replace(' bytes', '')
                result['proof_size'] = int(size_str)
            elif line.startswith('Gen time elapsed:'):
                time_str = line.split(':')[1].strip().replace('s', '')
                result['gen_time'] = float(time_str)
            elif line.startswith('Verify time elapsed:'):
                time_str = line.split(':')[1].strip().replace('ms', '')
                result['verify_time'] = float(time_str)
            elif line.startswith('Permit decision:'):
                decisions = line.split(':')[1].strip().split('/')
                result['decision'] = decisions[0].strip()
                result['expected_decision'] = decisions[1].strip()
                result['success'] = result['decision'] == result['expected_decision']
        
        results.append(result)
    
    return results

def create_text_histogram(data, title, bins=20, width=60):
    """Create a simple text-based histogram."""
    print(f"\n{title}")
    print("=" * len(title))
    
    if not data:
        print("No data available")
        return
    
    min_val = min(data)
    max_val = max(data)
    bin_width = (max_val - min_val) / bins
    
    # Create bins
    bin_counts = [0] * bins
    for value in data:
        bin_idx = min(int((value - min_val) / bin_width), bins - 1)
        bin_counts[bin_idx] += 1
    
    max_count = max(bin_counts) if bin_counts else 1
    
    # Print histogram
    for i in range(bins):
        bin_start = min_val + i * bin_width
        bin_end = min_val + (i + 1) * bin_width
        bar_length = int((bin_counts[i] / max_count) * width)
        bar = '█' * bar_length
        print(f"{bin_start:8.2f} - {bin_end:8.2f} | {bar} ({bin_counts[i]})")
    
    # Statistics
    mean_val = statistics.mean(data)
    median_val = statistics.median(data)
    print(f"\nMean: {mean_val:.2f}, Median: {median_val:.2f}, Min: {min_val:.2f}, Max: {max_val:.2f}")

def create_text_chart(data, labels, title, width=60):
    """Create a simple text-based bar chart."""
    print(f"\n{title}")
    print("=" * len(title))
    
    if not data:
        print("No data available")
        return
    
    max_val = max(data)
    
    for i, (value, label) in enumerate(zip(data, labels)):
        bar_length = int((value / max_val) * width)
        bar = '█' * bar_length
        print(f"{label:15} | {bar} {value:.2f}")

def analyze_results_with_text_charts(results):
    """Analyze the test results and create text-based visualizations."""
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['success'])
    failed_tests = total_tests - successful_tests
    
    print(f"=== TEST RESULTS SUMMARY ===")
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success rate: {successful_tests/total_tests*100:.1f}%")
    
    # Extract performance data
    cycle_counts = [r['user_cycles'] for r in results if r['user_cycles'] is not None]
    gen_times = [r['gen_time'] for r in results if r['gen_time'] is not None]
    verify_times = [r['verify_time'] for r in results if r['verify_time'] is not None]
    
    # Create histograms
    create_text_histogram(cycle_counts, "USER CYCLES DISTRIBUTION", bins=15)
    create_text_histogram(gen_times, "GENERATION TIME DISTRIBUTION (seconds)", bins=15)
    create_text_histogram(verify_times, "VERIFICATION TIME DISTRIBUTION (ms)", bins=15)
    
    # Performance by category
    test_categories = defaultdict(lambda: {'gen_times': [], 'cycles': [], 'permits': 0, 'total': 0})
    
    for r in results:
        category = r['test_name'][:3] if len(r['test_name']) >= 3 else r['test_name']
        if r['gen_time']:
            test_categories[category]['gen_times'].append(r['gen_time'])
        if r['user_cycles']:
            test_categories[category]['cycles'].append(r['user_cycles'])
        if r['decision'] == 'Permit':
            test_categories[category]['permits'] += 1
        test_categories[category]['total'] += 1
    
    categories = sorted(test_categories.keys())
    avg_gen_times = [statistics.mean(test_categories[cat]['gen_times']) 
                     if test_categories[cat]['gen_times'] else 0 for cat in categories]
    avg_cycles = [statistics.mean(test_categories[cat]['cycles']) 
                  if test_categories[cat]['cycles'] else 0 for cat in categories]
    permit_rates = [test_categories[cat]['permits'] / test_categories[cat]['total'] * 100 
                   for cat in categories]
    
    create_text_chart(avg_gen_times, categories, "AVERAGE GENERATION TIME BY CATEGORY (seconds)")
    create_text_chart(avg_cycles, categories, "AVERAGE USER CYCLES BY CATEGORY")
    create_text_chart(permit_rates, categories, "PERMIT RATE BY CATEGORY (%)")
    
    # Slowest tests
    slow_tests = sorted([(r['test_name'], r['gen_time']) for r in results if r['gen_time']], 
                       key=lambda x: x[1], reverse=True)[:10]
    
    print(f"\n=== TOP 10 SLOWEST TESTS ===")
    print("=" * 30)
    for i, (test_name, gen_time) in enumerate(slow_tests, 1):
        print(f"{i:2d}. {test_name:20} {gen_time:8.2f}s")
    
    # Decision breakdown
    permit_count = sum(1 for r in results if r['decision'] == 'Permit')
    deny_count = sum(1 for r in results if r['decision'] == 'Deny')
    
    print(f"\n=== DECISION BREAKDOWN ===")
    print("=" * 24)
    print(f"Permit decisions: {permit_count} ({permit_count/total_tests*100:.1f}%)")
    print(f"Deny decisions:   {deny_count} ({deny_count/total_tests*100:.1f}%)")
    
    # Performance outliers
    if gen_times:
        mean_gen_time = statistics.mean(gen_times)
        outliers = [(r['test_name'], r['gen_time']) for r in results 
                   if r['gen_time'] and r['gen_time'] > mean_gen_time * 3]
        
        if outliers:
            print(f"\n=== PERFORMANCE OUTLIERS (>3x average) ===")
            print("=" * 42)
            for test_name, gen_time in sorted(outliers, key=lambda x: x[1], reverse=True):
                print(f"{test_name:20} {gen_time:8.2f}s ({gen_time/mean_gen_time:.1f}x average)")
    
    return results

def export_csv_data(results):
    """Export results to CSV for external analysis."""
    csv_filename = 'performance_data.csv'
    with open(csv_filename, 'w') as f:
        # Header
        f.write("test_name,category,user_cycles,gen_time,verify_time,decision,success\n")
        
        # Data
        for r in results:
            category = r['test_name'][:3] if len(r['test_name']) >= 3 else r['test_name']
            f.write(f"{r['test_name']},{category},{r['user_cycles']},{r['gen_time']},"
                   f"{r['verify_time']},{r['decision']},{r['success']}\n")
    
    print(f"\nPerformance data exported to {csv_filename}")
    print("You can use this CSV file with Excel, Google Sheets, or other tools for advanced visualization.")

# Main execution
print(f"Analyzing log file: {LOG_FILE}")
results = parse_log_file(LOG_FILE)
analyzed_results = analyze_results_with_text_charts(results)
export_csv_data(results)

print("\n" + "="*60)
print("ANALYSIS COMPLETE")
print("="*60)
print("Text-based charts generated above.")
print("CSV data exported for external visualization tools.")
