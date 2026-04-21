#!/usr/bin/env python3
"""
CSCI 4550/5550 - Programming Assignment 3
Diamond Network Topology with OSPF Routing
Author: Takudzwa13
"""

import os
import time
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import Node
from mininet.link import TCLink
from mininet.log import info, setLogLevel


class FRRouting(Node):
    """Custom router node running FRRouting OSPF daemon"""
    
    def __init__(self, name, **params):
        super(FRRouting, self).__init__(name, **params)
        self.run_dir = f'/tmp/{name}-runtime'
        self.conf_dir = f'/tmp/{name}-config'
    
    def start_ospf(self, networks):
        """Start OSPF routing on this router"""
        # Enable IP forwarding
        self.cmd('sysctl -w net.ipv4.ip_forward=1')
        self.cmd('sysctl -w net.ipv4.fib_multipath_hash_policy=1')
        
        # Create runtime directory
        self.cmd(f'rm -rf {self.run_dir}')
        self.cmd(f'mkdir -p {self.run_dir}')
        self.cmd(f'chown frr:frr {self.run_dir}')
        self.cmd(f'chmod 775 {self.run_dir}')
        
        # Create config directory and file
        os.makedirs(self.conf_dir, exist_ok=True)
        conf_file = f'{self.conf_dir}/frr.conf'
        
        # Build OSPF network statements
        ospf_networks = "\n".join([f" network {net} area 0" for net in networks])
        
        # FRR configuration
        config = f"""hostname {self.name}
password zebra
log stdout
!
router ospf
 ospf router-id {self.params.get('router_id', '1.1.1.1')}
{ospf_networks}
!
"""
        
        with open(conf_file, 'w') as f:
            f.write(config)
        
        self.cmd(f'chown -R frr:frr {self.conf_dir}')
        
        # Start Zebra daemon (kernel routing table manager)
        self.cmd(f'/usr/lib/frr/zebra -d -f {conf_file} -u frr -g frr '
                f'-z {self.run_dir}/zserv.api --vty_socket {self.run_dir} '
                f'-i {self.run_dir}/zebra.pid')
        
        # Start OSPF daemon
        self.cmd(f'/usr/lib/frr/ospfd -d -f {conf_file} -u frr -g frr '
                f'-z {self.run_dir}/zserv.api --vty_socket {self.run_dir} '
                f'-i {self.run_dir}/ospfd.pid')
        
        self._wait_for_frr()
    
    def _wait_for_frr(self):
        """Wait for FRR socket files to appear"""
        info(f"  Waiting for {self.name}...")
        for _ in range(10):
            result = self.cmd(f'ls {self.run_dir}/zebra.vty 2>/dev/null')
            if "zebra.vty" in result:
                self.cmd(f'chmod 666 {self.run_dir}/*.vty')
                self.cmd(f'chmod 666 {self.run_dir}/zserv.api')
                info(" ready\n")
                return
            time.sleep(0.5)
        info(" WARNING: Timeout\n")
    
    def terminate(self):
        """Clean up FRR processes"""
        self.cmd(f'kill -9 $(cat {self.run_dir}/ospfd.pid) 2>/dev/null')
        self.cmd(f'kill -9 $(cat {self.run_dir}/zebra.pid) 2>/dev/null')
        self.cmd(f'rm -rf {self.run_dir}')
        self.cmd(f'rm -rf {self.conf_dir}')
        super(FRRouting, self).terminate()


def create_diamond_topology():
    """Build the diamond network topology"""
    
    net = Mininet(link=TCLink)
    
    # Hosts
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.1.1/24')
    h4 = net.addHost('h4', ip='10.0.1.2/24')
    
    # Switches
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')
    
    # Routers
    r1 = net.addHost('r1', cls=FRRouting, router_id='1.1.1.1')
    r2 = net.addHost('r2', cls=FRRouting, router_id='2.2.2.2')
    r3 = net.addHost('r3', cls=FRRouting, router_id='3.3.3.3')
    r4 = net.addHost('r4', cls=FRRouting, router_id='4.4.4.4')
    
    # LAN Connections
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(s1, r1)
    
    net.addLink(h3, s2)
    net.addLink(h4, s2)
    net.addLink(s2, r4)
    
    # Core Diamond Connections (100 Mbps, 10ms delay)
    net.addLink(r1, r2, bw=100, delay='10ms')
    net.addLink(r1, r3, bw=100, delay='10ms')
    net.addLink(r2, r4, bw=100, delay='10ms')
    net.addLink(r3, r4, bw=100, delay='10ms')
    
    net.start()
    
    # Configure Router Interfaces
    info("\n*** Configuring router interfaces\n")
    
    r1.cmd('ifconfig r1-eth0 10.0.0.254 netmask 255.255.255.0 up')
    r1.cmd('ifconfig r1-eth1 10.0.12.1 netmask 255.255.255.252 up')
    r1.cmd('ifconfig r1-eth2 10.0.13.1 netmask 255.255.255.252 up')
    
    r2.cmd('ifconfig r2-eth0 10.0.12.2 netmask 255.255.255.252 up')
    r2.cmd('ifconfig r2-eth1 10.0.24.1 netmask 255.255.255.252 up')
    
    r3.cmd('ifconfig r3-eth0 10.0.13.2 netmask 255.255.255.252 up')
    r3.cmd('ifconfig r3-eth1 10.0.34.1 netmask 255.255.255.252 up')
    
    r4.cmd('ifconfig r4-eth0 10.0.24.2 netmask 255.255.255.252 up')
    r4.cmd('ifconfig r4-eth1 10.0.34.2 netmask 255.255.255.252 up')
    r4.cmd('ifconfig r4-eth2 10.0.1.254 netmask 255.255.255.0 up')
    
    # Start OSPF on each router
    info("\n*** Starting OSPF routing\n")
    
    r1.start_ospf(['10.0.0.0/24', '10.0.12.0/30', '10.0.13.0/30'])
    r2.start_ospf(['10.0.12.0/30', '10.0.24.0/30'])
    r3.start_ospf(['10.0.13.0/30', '10.0.34.0/30'])
    r4.start_ospf(['10.0.1.0/24', '10.0.24.0/30', '10.0.34.0/30'])
    
    # Configure host default gateways
    h1.cmd('ip route add default via 10.0.0.254')
    h2.cmd('ip route add default via 10.0.0.254')
    h3.cmd('ip route add default via 10.0.1.254')
    h4.cmd('ip route add default via 10.0.1.254')
    
    info("\n" + "="*60 + "\n")
    info("TOPOLOGY READY!\n")
    info("="*60 + "\n")
    info("OSPF needs 30-40 seconds to converge\n")
    info("Commands to try:\n")
    info("  mininet> h1 ping h2\n")
    info("  mininet> h1 ping h3\n")
    info("  mininet> r1 ip route\n")
    info("  mininet> xterm r1 h1 h3\n")
    info("="*60 + "\n")
    
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    create_diamond_topology()
