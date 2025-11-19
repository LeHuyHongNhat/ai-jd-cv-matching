"""
Script để phân tích và visualize kết quả Load Testing

Requirements:
    pip install pandas matplotlib seaborn

Usage:
    python analyze_results.py results.csv
    python analyze_results.py --html report.html
"""

import argparse
import json
import sys
import os
from typing import Dict, List, Any
import warnings
warnings.filterwarnings('ignore')

# Check if required packages are installed
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError as e:
    print("❌ Missing required packages!")
    print("\nPlease install:")
    print("  pip install pandas matplotlib seaborn")
    sys.exit(1)

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)


class LoadTestAnalyzer:
    """Phân tích kết quả Load Testing"""
    
    def __init__(self, data_file: str = None):
        self.data_file = data_file
        self.df = None
        self.summary = {}
    
    def load_csv(self, csv_file: str):
        """Load dữ liệu từ Locust CSV file"""
        print(f"Loading data from {csv_file}...")
        
        try:
            # Locust generates multiple CSV files
            # We'll focus on the stats file
            if not csv_file.endswith('_stats.csv'):
                base_name = csv_file.replace('.csv', '')
                csv_file = f"{base_name}_stats.csv"
            
            if not os.path.exists(csv_file):
                print(f"❌ File not found: {csv_file}")
                return False
            
            self.df = pd.read_csv(csv_file)
            print(f"✅ Loaded {len(self.df)} rows")
            return True
        except Exception as e:
            print(f"❌ Error loading CSV: {str(e)}")
            return False
    
    def load_json(self, json_file: str):
        """Load dữ liệu từ k6 JSON file"""
        print(f"Loading data from {json_file}...")
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Convert k6 JSON to DataFrame
            # This is a simplified version
            print("✅ JSON loaded (summary only)")
            self.summary = data
            return True
        except Exception as e:
            print(f"❌ Error loading JSON: {str(e)}")
            return False
    
    def calculate_statistics(self):
        """Tính toán các thống kê cơ bản"""
        if self.df is None or self.df.empty:
            print("No data to analyze")
            return
        
        print("\n" + "="*60)
        print("STATISTICS SUMMARY")
        print("="*60)
        
        # Group by request type/name
        if 'Name' in self.df.columns:
            grouped = self.df.groupby('Name')
            
            for name, group in grouped:
                print(f"\n📊 Endpoint: {name}")
                print("-" * 60)
                
                if '# Requests' in group.columns:
                    total_reqs = group['# Requests'].sum()
                    print(f"  Total Requests:        {total_reqs}")
                
                if '# Failures' in group.columns:
                    total_fails = group['# Failures'].sum()
                    fail_rate = (total_fails / total_reqs * 100) if total_reqs > 0 else 0
                    print(f"  Total Failures:        {total_fails} ({fail_rate:.2f}%)")
                
                if 'Average Response Time' in group.columns:
                    avg_response = group['Average Response Time'].mean()
                    print(f"  Avg Response Time:     {avg_response:.2f}ms")
                
                if 'Min Response Time' in group.columns:
                    min_response = group['Min Response Time'].min()
                    print(f"  Min Response Time:     {min_response:.2f}ms")
                
                if 'Max Response Time' in group.columns:
                    max_response = group['Max Response Time'].max()
                    print(f"  Max Response Time:     {max_response:.2f}ms")
                
                if 'Requests/s' in group.columns:
                    rps = group['Requests/s'].mean()
                    print(f"  Requests per Second:   {rps:.2f}")
        
        print("\n" + "="*60)
    
    def plot_response_times(self, output_file: str = "response_times.png"):
        """Vẽ biểu đồ response times"""
        if self.df is None or self.df.empty:
            print("No data to plot")
            return
        
        print(f"\nGenerating response time plot...")
        
        fig, axes = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot 1: Average Response Time by Endpoint
        if 'Name' in self.df.columns and 'Average Response Time' in self.df.columns:
            ax1 = axes[0]
            data = self.df.groupby('Name')['Average Response Time'].mean().sort_values(ascending=False)
            data.plot(kind='barh', ax=ax1, color='skyblue')
            ax1.set_xlabel('Average Response Time (ms)')
            ax1.set_title('Average Response Time by Endpoint')
            ax1.grid(True, alpha=0.3)
        
        # Plot 2: Response Time Distribution
        if 'Average Response Time' in self.df.columns:
            ax2 = axes[1]
            self.df['Average Response Time'].hist(bins=50, ax=ax2, color='lightcoral', edgecolor='black')
            ax2.set_xlabel('Response Time (ms)')
            ax2.set_ylabel('Frequency')
            ax2.set_title('Response Time Distribution')
            ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✅ Plot saved to {output_file}")
        plt.close()
    
    def plot_throughput(self, output_file: str = "throughput.png"):
        """Vẽ biểu đồ throughput (RPS)"""
        if self.df is None or self.df.empty:
            print("No data to plot")
            return
        
        print(f"\nGenerating throughput plot...")
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        if 'Name' in self.df.columns and 'Requests/s' in self.df.columns:
            data = self.df.groupby('Name')['Requests/s'].mean().sort_values(ascending=False)
            data.plot(kind='barh', ax=ax, color='lightgreen')
            ax.set_xlabel('Requests per Second')
            ax.set_title('Throughput by Endpoint')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✅ Plot saved to {output_file}")
        plt.close()
    
    def plot_error_rate(self, output_file: str = "error_rate.png"):
        """Vẽ biểu đồ error rate"""
        if self.df is None or self.df.empty:
            print("No data to plot")
            return
        
        print(f"\nGenerating error rate plot...")
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        if 'Name' in self.df.columns and '# Requests' in self.df.columns and '# Failures' in self.df.columns:
            grouped = self.df.groupby('Name').agg({
                '# Requests': 'sum',
                '# Failures': 'sum'
            })
            grouped['Error Rate (%)'] = (grouped['# Failures'] / grouped['# Requests'] * 100)
            grouped['Error Rate (%)'].sort_values(ascending=False).plot(kind='barh', ax=ax, color='salmon')
            ax.set_xlabel('Error Rate (%)')
            ax.set_title('Error Rate by Endpoint')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✅ Plot saved to {output_file}")
        plt.close()
    
    def generate_report(self, output_dir: str = "load_test_analysis"):
        """Tạo báo cáo đầy đủ với charts"""
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n{'='*60}")
        print(f"Generating comprehensive report in: {output_dir}")
        print(f"{'='*60}")
        
        # Generate all plots
        self.plot_response_times(os.path.join(output_dir, "response_times.png"))
        self.plot_throughput(os.path.join(output_dir, "throughput.png"))
        self.plot_error_rate(os.path.join(output_dir, "error_rate.png"))
        
        # Generate HTML report
        html_file = os.path.join(output_dir, "analysis_report.html")
        self.generate_html_report(html_file)
        
        print(f"\n{'='*60}")
        print(f"✅ Report generated successfully!")
        print(f"{'='*60}")
        print(f"\nView the report:")
        print(f"  HTML: {html_file}")
        print(f"  Charts: {output_dir}/*.png")
    
    def generate_html_report(self, output_file: str):
        """Tạo HTML report"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Load Test Analysis Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .summary {{
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .chart {{
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .chart img {{
            max-width: 100%;
            height: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
        }}
        .metric-label {{
            font-weight: bold;
            color: #666;
        }}
        .metric-value {{
            font-size: 24px;
            color: #333;
        }}
    </style>
</head>
<body>
    <h1>🚀 Load Test Analysis Report</h1>
    <p>Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="summary">
        <h2>📊 Summary Statistics</h2>
        <p>Analysis of load test results</p>
        <!-- Add summary stats here -->
    </div>
    
    <div class="chart">
        <h2>⏱️ Response Times</h2>
        <img src="response_times.png" alt="Response Times">
    </div>
    
    <div class="chart">
        <h2>📈 Throughput</h2>
        <img src="throughput.png" alt="Throughput">
    </div>
    
    <div class="chart">
        <h2>❌ Error Rate</h2>
        <img src="error_rate.png" alt="Error Rate">
    </div>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML report saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Load Testing Results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze Locust CSV results
  python analyze_results.py results_stats.csv
  
  # Analyze k6 JSON results
  python analyze_results.py --json summary.json
  
  # Generate full report with charts
  python analyze_results.py results_stats.csv --report
"""
    )
    
    parser.add_argument(
        'file',
        nargs='?',
        help='CSV or JSON file with test results'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Input file is JSON (k6 format)'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate comprehensive report with charts'
    )
    parser.add_argument(
        '--output-dir',
        default='load_test_analysis',
        help='Output directory for reports (default: load_test_analysis)'
    )
    
    args = parser.parse_args()
    
    # If no file provided, look for recent results
    if not args.file:
        print("No file specified. Looking for recent test results...")
        
        # Look for CSV files
        csv_files = [f for f in os.listdir('.') if f.endswith('_stats.csv')]
        if csv_files:
            args.file = sorted(csv_files)[-1]  # Get most recent
            print(f"Found: {args.file}")
        else:
            print("❌ No test result files found!")
            print("\nPlease specify a file:")
            print("  python analyze_results.py results_stats.csv")
            sys.exit(1)
    
    # Create analyzer
    analyzer = LoadTestAnalyzer(args.file)
    
    # Load data
    if args.json:
        success = analyzer.load_json(args.file)
    else:
        success = analyzer.load_csv(args.file)
    
    if not success:
        sys.exit(1)
    
    # Calculate statistics
    analyzer.calculate_statistics()
    
    # Generate report if requested
    if args.report:
        analyzer.generate_report(args.output_dir)
    else:
        print("\n💡 Tip: Use --report to generate visual charts and HTML report")
        print(f"   python analyze_results.py {args.file} --report")


if __name__ == "__main__":
    main()

