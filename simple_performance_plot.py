#!/usr/bin/env python3
import re
import matplotlib.pyplot as plt
import argparse
import sys

def parse_log_file(file_path):
    """Parse log file and extract generation times with test names"""
    data = []
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Split by test sections
    sections = re.split(r'# ---------- (\w+) ----------', content)
    
    for i in range(1, len(sections), 2):
        if i + 1 < len(sections):
            test_name = sections[i].strip()
            test_content = sections[i + 1]
            
            # Extract gen time (in seconds)
            gen_match = re.search(r'Gen time elapsed: ([\d.]+)s', test_content)
            
            if gen_match:
                gen_time = float(gen_match.group(1))
                data.append({
                    'test_name': test_name,
                    'gen_time_s': gen_time
                })
    
    return data

def get_testcase_info(case_cnt=None, test_name=None):
    """
    API to get test case information by case number or test name
    
    Args:
        case_cnt: Case number (0-based index) in the sorted common test cases
        test_name: Exact test case name (e.g., 'IIA001')
    
    Returns:
        Dictionary with test case info or list of all cases if no parameters given
    """
    # Parse both log files
    current_data = parse_log_file('logs/batch_09_17_11_29_compiled.log')
    old_data = parse_log_file('logs/batch_09_14_23_56_current_version.log')
    
    # Create dictionaries for easier lookup
    old_dict = {d['test_name']: d['gen_time_s'] for d in old_data}
    current_dict = {d['test_name']: d['gen_time_s'] for d in current_data}
    
    # Find common test cases
    old_tests = set(old_dict.keys())
    current_tests = set(current_dict.keys())
    common_tests = old_tests.intersection(current_tests)
    
    # Sort common tests for consistent ordering
    common_tests_sorted = sorted(list(common_tests))
    
    # If no parameters given, return all test cases
    if case_cnt is None and test_name is None:
        result = []
        for i, name in enumerate(common_tests_sorted):
            result.append({
                'case_cnt': i,
                'test_name': name,
                'old_time_s': old_dict[name],
                'current_time_s': current_dict[name],
                'improvement_percent': ((old_dict[name] - current_dict[name]) / old_dict[name]) * 100
            })
        return result
    
    # Search by case count
    if case_cnt is not None:
        if 0 <= case_cnt < len(common_tests_sorted):
            name = common_tests_sorted[case_cnt]
            return {
                'case_cnt': case_cnt,
                'test_name': name,
                'old_time_s': old_dict[name],
                'current_time_s': current_dict[name],
                'improvement_percent': ((old_dict[name] - current_dict[name]) / old_dict[name]) * 100
            }
        else:
            return {'error': f'Case count {case_cnt} out of range. Valid range: 0-{len(common_tests_sorted)-1}'}
    
    # Search by test name
    if test_name is not None:
        if test_name in common_tests_sorted:
            case_cnt = common_tests_sorted.index(test_name)
            return {
                'case_cnt': case_cnt,
                'test_name': test_name,
                'old_time_s': old_dict[test_name],
                'current_time_s': current_dict[test_name],
                'improvement_percent': ((old_dict[test_name] - current_dict[test_name]) / old_dict[test_name]) * 100
            }
        else:
            return {'error': f'Test case "{test_name}" not found in common test cases'}

def interactive_query_mode():
    """Interactive query mode - loop waiting for user input"""
    print("="*60)
    print("Interactive Query Mode")
    print("="*60)
    print("Commands:")
    print("  <number>     - Get info for case number (e.g., '5')")
    print("  <test_name>  - Get info for test case name (e.g., 'IIA001')")
    print("  list <n>     - Show first n test cases (e.g., 'list 10')")
    print("  all          - Show all test cases")
    print("  stats        - Show overall statistics")
    print("  help         - Show this help")
    print("  quit/exit    - Exit query mode")
    print("="*60)
    
    # Get total number of cases for reference
    all_cases = get_testcase_info()
    total_cases = len(all_cases)
    print(f"Total common test cases: {total_cases}")
    print()
    
    while True:
        try:
            user_input = input("Query> ").strip()
            
            if not user_input:
                continue
                
            # Handle quit/exit
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
                
            # Handle help
            elif user_input.lower() in ['help', 'h', '?']:
                print("\nCommands:")
                print("  <number>     - Get info for case number (e.g., '5')")
                print("  <test_name>  - Get info for test case name (e.g., 'IIA001')")
                print("  list <n>     - Show first n test cases (e.g., 'list 10')")
                print("  all          - Show all test cases")
                print("  stats        - Show overall statistics")
                print("  help         - Show this help")
                print("  quit/exit    - Exit query mode")
                print()
                continue
                
            # Handle stats
            elif user_input.lower() == 'stats':
                old_times = [case['old_time_s'] for case in all_cases]
                current_times = [case['current_time_s'] for case in all_cases]
                improvements = [case['improvement_percent'] for case in all_cases]
                
                old_avg = sum(old_times) / len(old_times)
                current_avg = sum(current_times) / len(current_times)
                overall_improvement = ((old_avg - current_avg) / old_avg) * 100
                
                print(f"\nOverall Statistics:")
                print(f"  Total test cases: {total_cases}")
                print(f"  Old version average: {old_avg:.3f}s")
                print(f"  Current version average: {current_avg:.3f}s")
                print(f"  Overall improvement: {overall_improvement:.2f}%")
                print(f"  Best improvement: {max(improvements):.1f}%")
                print(f"  Worst regression: {min(improvements):.1f}%")
                print()
                continue
                
            # Handle list command
            elif user_input.lower().startswith('list'):
                parts = user_input.split()
                if len(parts) == 1:
                    n = 10  # default
                else:
                    try:
                        n = int(parts[1])
                    except ValueError:
                        print("Invalid number. Usage: list <n>")
                        print()
                        continue
                
                print(f"\nFirst {min(n, total_cases)} test cases:")
                print(f"{'#':>3} {'Name':12} {'Old (s)':>8} {'Current (s)':>11} {'Change (%)':>10}")
                print("-" * 50)
                
                for i, case in enumerate(all_cases[:n]):
                    print(f"{case['case_cnt']:3d} {case['test_name']:12} "
                          f"{case['old_time_s']:8.3f} {case['current_time_s']:11.3f} "
                          f"{case['improvement_percent']:9.1f}")
                print()
                continue
                
            # Handle all command
            elif user_input.lower() == 'all':
                print(f"\nAll {total_cases} test cases:")
                print(f"{'#':>3} {'Name':12} {'Old (s)':>8} {'Current (s)':>11} {'Change (%)':>10}")
                print("-" * 50)
                
                for case in all_cases:
                    print(f"{case['case_cnt']:3d} {case['test_name']:12} "
                          f"{case['old_time_s']:8.3f} {case['current_time_s']:11.3f} "
                          f"{case['improvement_percent']:9.1f}")
                print()
                continue
                
            # Try to parse as number (case count)
            elif user_input.isdigit():
                case_cnt = int(user_input)
                info = get_testcase_info(case_cnt=case_cnt)
                
                if 'error' in info:
                    print(f"Error: {info['error']}")
                else:
                    print(f"\nCase #{info['case_cnt']}: {info['test_name']}")
                    print(f"  Old version: {info['old_time_s']:.3f}s")
                    print(f"  Current version: {info['current_time_s']:.3f}s")
                    print(f"  Change: {info['improvement_percent']:.1f}% ({'improvement' if info['improvement_percent'] > 0 else 'regression' if info['improvement_percent'] < 0 else 'no change'})")
                print()
                
            # Try to parse as test name
            else:
                info = get_testcase_info(test_name=user_input)
                
                if 'error' in info:
                    print(f"Error: {info['error']}")
                    print("Tip: Use 'list 10' to see available test names, or try a number for case count.")
                else:
                    print(f"\nCase #{info['case_cnt']}: {info['test_name']}")
                    print(f"  Old version: {info['old_time_s']:.3f}s")
                    print(f"  Current version: {info['current_time_s']:.3f}s")
                    print(f"  Change: {info['improvement_percent']:.1f}% ({'improvement' if info['improvement_percent'] > 0 else 'regression' if info['improvement_percent'] < 0 else 'no change'})")
                print()
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            print()

def create_simple_comparison():
    """Create a simple comparison chart"""
    
    # Parse both log files
    current_data = parse_log_file('logs/batch_09_17_11_29_compiled.log')
    old_data = parse_log_file('logs/batch_09_14_23_56_current_version.log')
    
    print(f"Old version: {len(old_data)} tests")
    print(f"Current version: {len(current_data)} tests")
    
    # Create dictionaries for easier lookup
    old_dict = {d['test_name']: d['gen_time_s'] for d in old_data}
    current_dict = {d['test_name']: d['gen_time_s'] for d in current_data}
    
    # Find common test cases
    old_tests = set(old_dict.keys())
    current_tests = set(current_dict.keys())
    common_tests = old_tests.intersection(current_tests)
    
    print(f"Common test cases: {len(common_tests)}")
    print(f"Only in old version: {len(old_tests - current_tests)}")
    print(f"Only in current version: {len(current_tests - old_tests)}")
    
    # Sort common tests for consistent ordering
    common_tests_sorted = sorted(list(common_tests))
    
    # Extract aligned data for common tests only
    aligned_old_times = [old_dict[test] for test in common_tests_sorted]
    aligned_current_times = [current_dict[test] for test in common_tests_sorted]
    
    # Create figure
    plt.figure(figsize=(16, 8))
    
    # Plot aligned data
    plt.plot(range(len(common_tests_sorted)), aligned_old_times, 'b-o', alpha=0.7, markersize=3, label='Old Version', linewidth=1)
    plt.plot(range(len(common_tests_sorted)), aligned_current_times, 'r-o', alpha=0.7, markersize=3, label='Current Version', linewidth=1)
    
    plt.title('Generation Time Comparison: Old vs Current Version (Common Test Cases)', fontsize=16, fontweight='bold')
    plt.xlabel('Case ID (Test Number)')
    plt.ylabel('Generation Time (seconds)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Add some statistics as text
    old_avg = sum(aligned_old_times) / len(aligned_old_times)
    current_avg = sum(aligned_current_times) / len(aligned_current_times)
    improvement = ((old_avg - current_avg) / old_avg) * 100
    
    stats_text = f'Old Avg: {old_avg:.2f}s\nCurrent Avg: {current_avg:.2f}s\nChange: {improvement:.1f}%\nCommon Cases: {len(common_tests_sorted)}'
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig('generation_time_comparison.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"\nChart saved as 'generation_time_comparison.png'")
    print(f"Old version average: {old_avg:.3f} seconds ({len(common_tests_sorted)} common cases)")
    print(f"Current version average: {current_avg:.3f} seconds ({len(common_tests_sorted)} common cases)")
    print(f"Performance change: {improvement:.2f}% ({'improvement' if improvement > 0 else 'regression'})")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Performance comparison tool for test cases')
    parser.add_argument('--query', action='store_true', 
                       help='Enter interactive query mode (no chart generation)')
    
    args = parser.parse_args()
    
    if args.query:
        # Interactive query mode - no chart generation
        interactive_query_mode()
    else:
        # Default behavior - create chart and show demo
        create_simple_comparison()
        
        # Demo the API functionality
        print("\n" + "="*60)
        print("API Demo - Test Case Information")
        print("="*60)
        
        # Example 1: Get info by case count
        print("\n1. Get test case info by case count (case_cnt=0):")
        info = get_testcase_info(case_cnt=0)
        if 'error' not in info:
            print(f"   Case #{info['case_cnt']}: {info['test_name']}")
            print(f"   Old version: {info['old_time_s']:.3f}s")
            print(f"   Current version: {info['current_time_s']:.3f}s")
            print(f"   Improvement: {info['improvement_percent']:.1f}%")
        else:
            print(f"   {info['error']}")
        
        # Example 2: Get info by test name
        print("\n2. Get test case info by name (test_name='IIA001'):")
        info = get_testcase_info(test_name='IIA001')
        if 'error' not in info:
            print(f"   Case #{info['case_cnt']}: {info['test_name']}")
            print(f"   Old version: {info['old_time_s']:.3f}s")
            print(f"   Current version: {info['current_time_s']:.3f}s")
            print(f"   Improvement: {info['improvement_percent']:.1f}%")
        else:
            print(f"   {info['error']}")
        
        # Example 3: Show first 5 test cases
        print("\n3. First 5 test cases overview:")
        all_cases = get_testcase_info()
        for case in all_cases[:5]:
            print(f"   Case #{case['case_cnt']:3d}: {case['test_name']:10s} | "
                  f"Old: {case['old_time_s']:6.3f}s | Current: {case['current_time_s']:6.3f}s | "
                  f"Change: {case['improvement_percent']:6.1f}%")
        
        print(f"\n   Total common test cases: {len(all_cases)}")
        print("\nTo use the API in your code:")
        print("   from simple_performance_plot import get_testcase_info")
        print("   info = get_testcase_info(case_cnt=10)  # Get case #10")
        print("   info = get_testcase_info(test_name='IIA006')  # Get specific test")
        print("   all_cases = get_testcase_info()  # Get all test cases")
        print("\nTo enter interactive query mode:")
        print("   python3 simple_performance_plot.py --query")
