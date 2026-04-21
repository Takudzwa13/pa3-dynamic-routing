#!/usr/bin/env python3
"""
ECMP Traffic Monitor for PA3
"""

import sys
import time


IFACE1 = 'r1-eth1'
IFACE2 = 'r1-eth2'
OUTPUT_PLOT = '/tmp/ecmp_traffic.png'


def get_tx_bytes(iface):
    try:
        with open('/proc/net/dev', 'r') as f:
            for line in f:
                if ':' in line and iface in line:
                    parts = line.split(':')
                    stats = parts[1].strip().split()
                    if len(stats) >= 9:
                        return int(stats[8])
        return 0
    except:
        return 0


def monitor(interval, duration):
    times = []
    cumul1 = []
    cumul2 = []
    rates1 = []
    rates2 = []
    
    prev1 = get_tx_bytes(IFACE1)
    prev2 = get_tx_bytes(IFACE2)
    start1 = prev1
    start2 = prev2
    
    start_time = time.time()
    end_time = start_time + duration
    
    print("\n" + "="*90)
    print(f"{'Time(s)':>8}  {'eth1 Cumul(MB)':>18}  {'eth1 Rate(MB/s)':>20}  {'eth2 Cumul(MB)':>18}  {'eth2 Rate(MB/s)':>20}")
    print("-"*90)
    
    while time.time() < end_time:
        time.sleep(interval)
        elapsed = time.time() - start_time
        
        curr1 = get_tx_bytes(IFACE1)
        curr2 = get_tx_bytes(IFACE2)
        
        total1 = (curr1 - start1) / 1000000
        total2 = (curr2 - start2) / 1000000
        
        rate1 = ((curr1 - prev1) / interval) / 1000000
        rate2 = ((curr2 - prev2) / interval) / 1000000
        
        times.append(elapsed)
        cumul1.append(total1)
        cumul2.append(total2)
        rates1.append(rate1)
        rates2.append(rate2)
        
        print(f"{elapsed:>8.1f}  {total1:>18.3f}  {rate1:>20.3f}  {total2:>18.3f}  {rate2:>20.3f}")
        
        prev1, prev2 = curr1, curr2
    
    return {'times': times, 'cumul1': cumul1, 'cumul2': cumul2, 'rate1': rates1, 'rate2': rates2}


def plot(data):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        t = data['times']
        
        ax1.plot(t, data['cumul1'], 'b-', label='r1-eth1 (via r2)')
        ax1.plot(t, data['cumul2'], 'r-', label='r1-eth2 (via r3)')
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Cumulative TX (MB)')
        ax1.set_title('ECMP Traffic - Cumulative')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        ax2.plot(t, data['rate1'], 'b-', label='r1-eth1 (via r2)')
        ax2.plot(t, data['rate2'], 'r-', label='r1-eth2 (via r3)')
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Rate (MB/s)')
        ax2.set_title('ECMP Traffic - Instantaneous Rate')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(OUTPUT_PLOT, dpi=150)
        print(f"\nPlot saved: {OUTPUT_PLOT}")
    except ImportError:
        print("\nmatplotlib not installed")


def main():
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    
    print(f"ECMP Monitor - Interval: {interval}s, Duration: {duration}s")
    data = monitor(interval, duration)
    if data['times']:
        plot(data)


if __name__ == '__main__':
    main()
