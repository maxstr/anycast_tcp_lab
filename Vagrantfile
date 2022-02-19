# -*- mode: ruby -*-
# vi: set ft=ruby :
require 'ipaddr'

# Topology
# client using "internet" interface IP (192.168.10.0/24) -> router -> forwarder -> encap over private network(192.168.0.0/24) -> backend

def network_index(network, index)
	initial_address = IPAddr.new network
	new_addr = IPAddr.new (initial_address.to_i + index), Socket::AF_INET
	return new_addr.to_s
end

Vagrant.configure("2") do |config|

	(1..6).each do |i|
		config.vm.define "backend-#{i}" do |backend|
			backend.vm.network :private_network, type: 'dhcp', subnet: "192.168.10.0/24", docker_connect__alias: "backend-#{i}-internet"
			backend.vm.network :private_network, type: 'dhcp', subnet: "192.168.0.0/24", docker_connect__alias: "backend-#{i}"
			backend.vm.provider "docker" do |d|
				d.build_dir = "./"
				d.build_args = ["--target", "backend"]
				d.create_args = ["--privileged"]
			end
		end
	end

	config.vm.define "client" do |client|
		client.vm.network :private_network, type: "dhcp", subnet: "192.168.10.0/24", docker_connect__alias: "client"
		client.vm.provider "docker" do |d|
			d.build_dir = "./"
			d.build_args = ["--target", "client"]
			d.create_args = ["--privileged"]
		end
	
	end

	config.vm.define "router" do |router|
		router.vm.network :private_network, type: "dhcp", subnet: "192.168.10.0/24", docker_connect__alias: "router-internet"
		router.vm.network :private_network, type: "dhcp", subnet: "192.168.0.0/24", docker_connect__alias: "router"
		router.vm.provider "docker" do |d|
			d.build_dir = "./"
			d.build_args = ["--target", "router"]
			d.create_args = ["--privileged"]
		end
	end


	(1..8).each do |i|
		config.vm.define "forwarder-#{i}" do |forwarder|
			forwarder.vm.network :private_network, type: "dhcp", subnet: "192.168.0.0/24"
			forwarder.vm.provider "docker" do |d|
				d.build_dir = "./"
				d.build_args = ["--target", "forwarder"]
				d.create_args = ["--privileged", "--sysctl", "net.ipv4.vs.sloppy_tcp=1"]
			end
		end
	end

end
