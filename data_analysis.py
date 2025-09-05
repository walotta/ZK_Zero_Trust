import os
import re
from collections import defaultdict
import matplotlib.pyplot as plt
import statistics

LOG_FILE = 'batch_08_14_12_08.log'
assert os.path.exists(LOG_FILE), "Log file does not exist."

# Create output directory for pictures
PIC_OUTPUT_DIR = 'pic_output'
os.makedirs(PIC_OUTPUT_DIR, exist_ok=True)

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

def analyze_results(results):
    """Analyze the test results and print statistics."""
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['success'])
    failed_tests = total_tests - successful_tests
    
    print(f"=== TEST RESULTS SUMMARY ===")
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success rate: {successful_tests/total_tests*100:.1f}%")
    print()
    
    # Performance statistics
    cycle_counts = [r['user_cycles'] for r in results if r['user_cycles'] is not None]
    gen_times = [r['gen_time'] for r in results if r['gen_time'] is not None]
    verify_times = [r['verify_time'] for r in results if r['verify_time'] is not None]
    
    if cycle_counts:
        print(f"=== PERFORMANCE STATISTICS ===")
        print(f"User Cycles - Min: {min(cycle_counts)}, Max: {max(cycle_counts)}, Avg: {sum(cycle_counts)/len(cycle_counts):.0f}")
        print(f"Gen Time - Min: {min(gen_times):.2f}s, Max: {max(gen_times):.2f}s, Avg: {sum(gen_times)/len(gen_times):.2f}s")
        print(f"Verify Time - Min: {min(verify_times):.2f}ms, Max: {max(verify_times):.2f}ms, Avg: {sum(verify_times)/len(verify_times):.2f}ms")
        print()
    
    # Decision breakdown
    permit_count = sum(1 for r in results if r['decision'] == 'Permit')
    deny_count = sum(1 for r in results if r['decision'] == 'Deny')
    
    print(f"=== DECISION BREAKDOWN ===")
    print(f"Permit decisions: {permit_count}")
    print(f"Deny decisions: {deny_count}")
    print()
    
    # Performance outliers (tests that took significantly longer)
    if gen_times:
        avg_gen_time = sum(gen_times) / len(gen_times)
        slow_tests = [(r['test_name'], r['gen_time']) for r in results 
                     if r['gen_time'] and r['gen_time'] > avg_gen_time * 2]
        
        if slow_tests:
            print(f"=== SLOW TESTS (>2x average gen time) ===")
            for test_name, gen_time in sorted(slow_tests, key=lambda x: x[1], reverse=True):
                print(f"- {test_name}: {gen_time:.2f}s")
            print()
    
    # Test categories analysis
    test_categories = defaultdict(list)
    for r in results:
        # Extract category from test name (e.g., IIA, IIB, IIC)
        category = r['test_name'][:3] if len(r['test_name']) >= 3 else r['test_name']
        test_categories[category].append(r)
    
    print(f"=== TEST CATEGORIES ===")
    for category in sorted(test_categories.keys()):
        tests = test_categories[category]
        success_count = sum(1 for t in tests if t['success'])
        permit_count = sum(1 for t in tests if t['decision'] == 'Permit')
        avg_cycles = sum(t['user_cycles'] for t in tests if t['user_cycles']) / len([t for t in tests if t['user_cycles']])
        print(f"{category}: {len(tests)} tests, {success_count}/{len(tests)} success, {permit_count} permits, avg {avg_cycles:.0f} cycles")
    print()
    
    # Failed tests
    if failed_tests > 0:
        print(f"=== FAILED TESTS ===")
        for r in results:
            if not r['success']:
                print(f"- {r['test_name']}: Got {r['decision']}, Expected {r['expected_decision']}")
        print()
    
    return results

def create_performance_plots(results):
    """Create various performance analysis plots as separate images."""
    # Extract data for plotting
    user_cycles = [r['user_cycles'] for r in results if r['user_cycles'] is not None]
    gen_times = [r['gen_time'] for r in results if r['gen_time'] is not None]
    verify_times = [r['verify_time'] for r in results if r['verify_time'] is not None]
    
    # 1. User Cycles Distribution
    plt.figure(figsize=(10, 6))
    plt.hist(user_cycles, bins=30, alpha=0.7, color='blue', edgecolor='black')
    plt.xlabel('User Cycles')
    plt.ylabel('Frequency')
    plt.title('User Cycles Distribution')
    mean_cycles = statistics.mean(user_cycles)
    plt.axvline(mean_cycles, color='red', linestyle='--', label=f'Mean: {mean_cycles:.0f}')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(PIC_OUTPUT_DIR, 'user_cycles_distribution.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("User cycles distribution saved")
    
    # 2. Enhanced Generation Time Distribution with Outliers
    plt.figure(figsize=(14, 8))
    
    # Create histogram
    n, bins, patches = plt.hist(gen_times, bins=40, alpha=0.7, color='lightblue', edgecolor='black')
    plt.xlabel('Generation Time (s)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.title('Generation Time Distribution with Time-Costly Tasks Highlighted', fontsize=14, fontweight='bold')
    
    # Calculate statistics
    mean_gen = statistics.mean(gen_times)
    median_gen = statistics.median(gen_times)
    std_gen = statistics.stdev(gen_times)
    
    # Add statistical lines
    plt.axvline(mean_gen, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_gen:.2f}s')
    plt.axvline(median_gen, color='orange', linestyle='--', linewidth=2, label=f'Median: {median_gen:.2f}s')
    plt.axvline(mean_gen + 2*std_gen, color='purple', linestyle=':', linewidth=2, label=f'Mean + 2σ: {mean_gen + 2*std_gen:.2f}s')
    
    # Identify and annotate time-costly tasks (outliers > mean + 2*std_dev)
    outlier_threshold = mean_gen + 2 * std_gen
    outliers = [(r['test_name'], r['gen_time']) for r in results 
               if r['gen_time'] and r['gen_time'] > outlier_threshold]
    
    # Sort outliers by generation time (descending)
    outliers.sort(key=lambda x: x[1], reverse=True)
    
    # Add text box with outlier information
    if outliers:
        outlier_text = "Time-Costly Tasks (> Mean + 2σ):\n"
        for i, (test_name, gen_time) in enumerate(outliers[:5]):  # Show top 5 outliers
            outlier_text += f"• {test_name}: {gen_time:.2f}s\n"
        if len(outliers) > 5:
            outlier_text += f"... and {len(outliers) - 5} more"
        
        # Position text box in upper right
        plt.text(0.98, 0.98, outlier_text, transform=plt.gca().transAxes, 
                fontsize=10, verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8))
    
    # Highlight outlier region in histogram
    for i, (bin_start, bin_end) in enumerate(zip(bins[:-1], bins[1:])):
        if bin_start >= outlier_threshold:
            patches[i].set_facecolor('red')
            patches[i].set_alpha(0.8)
    
    plt.legend(loc='upper right', bbox_to_anchor=(0.97, 0.7))
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(PIC_OUTPUT_DIR, 'generation_time_distribution.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("Enhanced generation time distribution saved")
    
    # 3. Verify Time Distribution
    plt.figure(figsize=(10, 6))
    plt.hist(verify_times, bins=30, alpha=0.7, color='orange', edgecolor='black')
    plt.xlabel('Verify Time (ms)')
    plt.ylabel('Frequency')
    plt.title('Verify Time Distribution')
    mean_verify = statistics.mean(verify_times)
    plt.axvline(mean_verify, color='red', linestyle='--', label=f'Mean: {mean_verify:.2f}ms')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(PIC_OUTPUT_DIR, 'verify_time_distribution.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("Verify time distribution saved")
    
    # 4. Performance by Test Category
    test_categories = defaultdict(list)
    for r in results:
        category = r['test_name'][:3] if len(r['test_name']) >= 3 else r['test_name']
        if r['gen_time']:
            test_categories[category].append(r['gen_time'])
    
    categories = list(test_categories.keys())
    avg_times = [statistics.mean(times) for times in test_categories.values()]
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(categories, avg_times, alpha=0.7, color=['red', 'green', 'blue', 'orange', 'purple'][:len(categories)])
    plt.xlabel('Test Category')
    plt.ylabel('Average Generation Time (s)')
    plt.title('Average Generation Time by Category')
    plt.xticks(rotation=45)
    
    # Add value labels on bars
    for bar, value in zip(bars, avg_times):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                f'{value:.2f}s', ha='center', va='bottom')
    
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(PIC_OUTPUT_DIR, 'category_performance.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("Category performance saved")

def create_detailed_performance_plot(results):
    """Create detailed timeline plots of test performance as separate images."""
    # This function has been removed - no timeline plots needed
    pass

def create_category_comparison_plot(results):
    """Create detailed comparison plots by test categories as separate images."""
    test_categories = defaultdict(lambda: {'gen_times': [], 'cycles': [], 'verify_times': [], 'permits': 0, 'total': 0})
    
    for r in results:
        category = r['test_name'][:3] if len(r['test_name']) >= 3 else r['test_name']
        if r['gen_time']:
            test_categories[category]['gen_times'].append(r['gen_time'])
        if r['user_cycles']:
            test_categories[category]['cycles'].append(r['user_cycles'])
        if r['verify_time']:
            test_categories[category]['verify_times'].append(r['verify_time'])
        if r['decision'] == 'Permit':
            test_categories[category]['permits'] += 1
        test_categories[category]['total'] += 1
    
    categories = sorted(test_categories.keys())
    colors = ['lightblue', 'lightgreen', 'lightcoral', 'lightyellow', 'lightpink']
    
    # Box plot for generation times
    plt.figure(figsize=(12, 8))
    gen_data = [test_categories[cat]['gen_times'] for cat in categories]
    box1 = plt.boxplot(gen_data, tick_labels=categories, patch_artist=True)
    plt.ylabel('Generation Time (s)')
    plt.title('Generation Time Distribution by Category')
    plt.grid(True, alpha=0.3)
    
    # Color the boxes
    for patch, color in zip(box1['boxes'], colors[:len(categories)]):
        patch.set_facecolor(color)
    
    plt.tight_layout()
    plt.savefig(os.path.join(PIC_OUTPUT_DIR, 'generation_time_by_category.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("Generation time by category saved")

# Parse and analyze the log file
print(f"Analyzing log file: {LOG_FILE}")
results = parse_log_file(LOG_FILE)
analyzed_results = analyze_results(results)

# Create performance visualizations
print(f"\nCreating performance visualizations in '{PIC_OUTPUT_DIR}' directory...")
create_performance_plots(results)
create_detailed_performance_plot(results)
create_category_comparison_plot(results)

print(f"\n🎉 All plots generated successfully in '{PIC_OUTPUT_DIR}' directory!")
print(f"📁 Generated files:")
pic_files = [
    'user_cycles_distribution.png',
    'generation_time_distribution.png', 
    'verify_time_distribution.png',
    'category_performance.png',
    'generation_time_by_category.png'
]
for pic_file in pic_files:
    print(f"   - {PIC_OUTPUT_DIR}/{pic_file}")