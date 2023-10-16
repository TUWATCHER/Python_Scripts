
from jnpr.junos import Device
from jnpr.junos.factory import loadyaml
from netmiko import ConnectHandler
from datetime import datetime
import re
import getpass
# import pwd

# nix_user = pwd.getpwnam('ichaykun')
# passwd = nix_user.pw_passwd
hostname = None
pw = '********'
timestamp = datetime.now()
key_file = '/var/tmp/id_rsa'
host_file = '/var/tmp/juniper_host'
license_yml = '/var/tmp/license.yml'
log_file = open('/var/tmp/log', 'a')

open_yaml = loadyaml(license_yml)
License = open_yaml['GetLicense']


def est_connect():
    esxi_device = {
        'device_type': 'linux',
        'host': '10.255.255.200',
        'username': 'root',
        'password': '*******',
        'auto_connect': False}
    # print(f"Establish connectivity for host: {esxi_device['host']}")
    connection = ConnectHandler(**esxi_device)
    connection.establish_connection()
    connection.set_base_prompt(alt_prompt_terminator=']')
    return connection


def close_connect():
    conn = est_connect()
    conn.disconnect()


def get_vmid(host):
    print("---Getting VM ID---")
    return est_connect().send_command(f'vim-cmd vmsvc/getallvms | grep {host}')[0:2]


def get_vmlist():
    print("---Getting VM List---")
    print(est_connect().send_command('vim-cmd vmsvc/getallvms'))


def get_vmstatus(id):
    print("---Getting VM STATUS---")
    return est_connect().send_command(f'vim-cmd vmsvc/power.getstate {id} | grep Power')


def get_snapshotid(id):
    print("---Getting Snapshot ID---")
    snapid = re.findall('\d+', est_connect().send_command(f'vim-cmd vmsvc/get.snapshotinfo {id} | grep id'))
    return snapid[0]


def restorevm(id, snapshot):
    print("Trying to restore system from snapshot")
    print(f'Restoring snapshot for VM ID: {id}')
    print(est_connect().send_command(f'vim-cmd vmsvc/snapshot.revert {id} {snapshot} suppressPowerOn'))


def poweron_vm(id):
    print(f"Powering on VM id: {id}")
    print(est_connect().send_command(f'vim-cmd vmsvc/power.on {id}'))


# Open host file
if hostname is None:

    with open(host_file) as host_file:
        hostname = host_file.read().splitlines()
else:
    print("Hostname is empty please, specify: ")
    hostname = input()

print(f"Currect sctipt will be executed for next hostnames: {hostname} \n")

# Get password for key file
if pw is None:
    pw = getpass.getpass("Please enter password:")

# Start connection for devices

for hosts in hostname:
    try:
        with Device(host=hosts, user='automation', password=pw, ssh_private_key_file=key_file, port=22) as dev:
            print(100 * '*')

            print(f"Connecting to device {dev.facts['hostname']}")
            vm_id = get_vmid(dev.facts['hostname'])
            print(f"VM ID is {vm_id}")

            print(f"Checking license for {dev.facts['hostname']}")
            table = License(dev)
            table.get()
            if int(table['Virtual Appliance'].time[0:2]) <= 2:
                print(f"Begin restoration of {dev.facts['hostname']}")
                log_file.write(f"{timestamp} Restore {dev.facts['hostname']} \n")
                restorevm(vm_id, get_snapshotid(vm_id))
                if get_vmstatus(vm_id) == "Powered off":
                    print(f"Current VM status is: {get_vmstatus(vm_id)}")
                    print("Turning it on")
                    log_file.write(f"Current VM status is: {get_vmstatus(vm_id)}, Turning it on \n")
                    poweron_vm(vm_id)
                else:
                    print("VM is Active")
            else:
                print(f"License left: {table['Virtual Appliance'].time}, Not Today")
                log_file.write(f"{timestamp} License left: {table['Virtual Appliance'].time}, Not Today \n")


    except Exception as ex:
        print(ex)
log_file.close()
close_connect()
