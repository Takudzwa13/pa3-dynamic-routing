#!/usr/bin/env python3
"""
ECMP Traffic Monitor for PA3
Reads /proc/net/dev to track traffic on r1's ECMP paths
Author: Takudzwa13
"""

import sys
import time
from pathlib import Path


# Configuration
INTERFACE_1 = 'r1-eth1'  # Path to r2
INTERFACE_2 = 'r1-eth2'  # Path to r3
PROC_NET_FILE = '/proc/net/dev'
OUTPUT_PLOT = '/tmp/ecmp_traffic.png'


def get_tx_bytes(interface):
    """Extract transmitted bytes count from /proc/net/dev"""
    try:
        with open(PROC_NET_FILE, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            if ':' in line and interface in line:
                parts = line.split(':')
                stats = parts[1].strip().split()
                if len(stats) >= 9:
                    return int(stats[8])  # TX bytes at index 8
        return 0
    except Exception:
        return 0


def bytes_to_megabytes(b):
    """Convert bytes to megabytes"""
    return b / 1_000_000.0


def print_table_header():
    """Display column headers for live table"""
    print("\n" + "="*95)
    print(f"{'Time(s)':>8}  {'r1-eth1 Total(MB)':>18}  {'r1-eth1 Rate(MB/s)':>20}  "
          f"{'r1-eth2 Total(MB)':>18}  {'r1-eth2 Rate(MB/s)':>20}")
    print("-"*95)


def print_data_row(elapsed, total1, rate1, total2, rate2):
    """Display one row of monitoring data"""
    print(f"{elapsed:>8.1f}  {total1:>18.3f}  {rate1:>20.3f}  "
          f"{total2:>18.3f}  {rate2:>20.3f}")


def monitor_traffic(interval_sec, duration_sec):
    """Main monitoring loop - polls interface counters"""
    
    time_points = []
    cumulative_1 = []
    cumulative_2 = []
    rate_1 = []
    rate_2 = []
    
    # Initial readings
    prev_tx1 = get_tx_bytes(INTERFACE_1)
    prev_tx2 = get_tx_bytes(INTERFACE_2)
    start_tx1 = prev_tx1
    start_tx2 = prev_tx2
    
    start_time = time.time()
    end_time = start_time + duration_sec
    
    print_table_header()
    
    while time.time() < end_time:
        time.sleep(interval_sec)
        
        current_time = time.time()
        elapsed = current_time - start_time
        
        # Get current counters
        curr_tx1 = get_tx_bytes(INTERFACE_1)
        curr_tx2 = get_tx_bytes(INTERFACE_2)
        
        # Calculate cumulative totals
        total1_mb = bytes_to_megabytes(curr_tx1 - start_tx1)
        total2_mb = bytes_to_megabytes(curr_tx2 - start_tx2)
        
        # Calculate instantaneous rates
        delta1 = curr_tx1 - prev_tx1
        delta2 = curr_tx2 - prev_tx2
        rate1_mbps = bytes_to_megabytes(delta1) / interval_sec
        rate2_mbps = bytes_to_megabytes(delta2) / interval_sec
        
        # Store data
        time_points.append(elapsed)
        cumulative_1.append(total1_mb)
        cumulative_2.append(total2_mb)
        rate_1.append(rate1_mbps)
        rate_2.append(rate2_mbps)
        
        # Print to screen
        print_data_row(elapsed, total1_mb, rate1_mbps, total2_mb, rate2_mbps)
        
        # Update previous values
        prev_tx1 = curr_tx1
        prev_tx2 = curr_tx2
    
    return {
        'times': time_points,
        'cumul1': cumulative_1,
        'cumul2': cumulative_2,
        'rate1': rate_1,
        'rate2': rate_2
    }


def generate_plot(data):
    """Create the two-panel plot"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        fig, (ax_top, ax_bottom) = plt.subplots(2, 1, figsize=(10, 8))
        
        t = data['times']
        
        # Top subplot - Cumulative traffic
        ax_top.plot(t, data['cumul1'], 'b-o', label=f'{INTERFACE_1} (via r2)', 
                   linewidth=2, markersize=3)
        ax_top.plot(t, data['cumul2'], 'r-s', label=f'{INTERFACE_2} (via r3)', 
                   linewidth=2, markersize=3)
        ax_top.set_xlabel('Time (seconds)')
        ax_top.set_ylabel('Total Data Transmitted (MB)')
        ax_top.set_title('ECMP Traffic Distribution - Cumulative Bytes')
        ax_top.legend()
        ax_top.grid(True, alpha=0.3)
        
        # Bottom subplot - Instantaneous rate
        ax_bottom.plot(t, data['rate1'], 'b-o', label=f'{INTERFACE_1} (via r2)', 
                      linewidth=2, markersize=3)
        ax_bottom.plot(t, data['rate2'], 'r-s', label=f'{INTERFACE_2} (via r3)', 
                      linewidth=2, markersize=3)
        ax_bottom.set_xlabel('Time (seconds)')
        ax_bottom.set_ylabel('Transmission Rate (MB/s)')
        ax_bottom.set_title('ECMP Traffic Distribution - Instantaneous Rate')
        ax_bottom.legend()
        ax_bottom.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(OUTPUT_PLOT, dpi=150)
        print(f"\n✓ Plot saved to: {OUTPUT_PLOT}")
        print(f"  View with: eog {OUTPUT_PLOT}")
        
    except ImportError:
        print("\n⚠ matplotlib not installed. Install with: pip install matplotlib")


def main():
    # Parse command line arguments
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    
    print("\n" + "="*60)
    print("ECMP Traffic Monitor for Router r1")
    print("="*60)
    print(f"Monitoring: {INTERFACE_1} and {INTERFACE_2}")
    print(f"Sample interval: {interval} second(s)")
    print(f"Total duration: {duration} second(s)")
    print("="*60)
    
    # Run the monitoring
    results = monitor_traffic(interval, duration)
    
    # Generate the plot
    if results['times']:
        generate_plot(results)
        print(f"\n✓ Collected {len(results['times'])} samples")
    else:
        print("\n✗ No data collected")
    
    print("\nMonitoring complete!\n")


if __name__ == '__main__':
    main()
