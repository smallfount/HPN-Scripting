# Deploying (IRF-)(iMC-)config and software on HP5130 24/48 Ports (PoE) Switches
#
#-------------------------------------------------------------------------------
# Author:      Remi Batist
# Version:     3.0
#
# Created:     20-04-2016
# Comments:    remi.batist@axez.nl
#-------------------------------------------------------------------------------

#	How to use de script;
#	1) On the HP IMC server(or other tftp-srver), put this script and software in the "%IMC Install Folder%\server\tmp" folder.
#	2) Set the DHCP-Server in the "deploy" network with this script as bootfile. Example on a Comware devices below.
#			dhcp enable
#			dhcp server forbid 10.0.1.1 10.0.1.200
#			dhcp server ip-pool v1
# 			gateway 10.0.1.1
# 			bootfile-name 5130_irf-config.py
# 			tftp-server ip 10.0.1.100
# 			network 10.0.1.0 24
#	3) Boot a switch without a config-file and connect it to the "deploy" network.

# 	You can change this or other custom settings below when needed

#   Custom settings
tftpsrv = "10.0.1.100"
imc_bootfile = "autocfg_startup.cfg"
optional_file1 = "" # ap_config.py for example
optional_file2 = ""
imc_snmpread = 'iMCread'
imc_snmpwrite = 'iMCwrite'
bootfile = "5130ei-cmw710-boot-r3111p07.bin"
sysfile = "5130ei-cmw710-system-r3111p07.bin"
poefile = "S5130EI-POE-145.bin"
irf_48_port_1 = "/0/49"
irf_48_port_2 = "/0/51"
irf_24_port_1 = "/0/25"
irf_24_port_2 = "/0/27"
poe_pse_numbers = {"1":"4","2":"7","3":"10","4":"13","5":"16","6":"19","7":"22","8":"25","9":"26"}
irf_prio_numbers = {"1":"32","2":"31","3":"30","4":"29","5":"28","6":"27","7":"26","8":"25","9":"24"}

#### Importing python modules
import comware
import os
import sys
import time
import termios

#### RAW user-input module
fd = sys.stdin.fileno();
new = termios.tcgetattr(fd)
new[3] = new[3] | termios.ICANON | termios.ECHO
new[6] [termios.VMIN] = 1
new[6] [termios.VTIME] = 0
termios.tcsetattr(fd, termios.TCSANOW, new)
termios.tcsendbreak(fd,0)

#### Notification for Starting
print (('\n' * 5) + "Starting script for deploying IRF-config and software on 5130 switches\n"
        "\nPlease wait while getting the current versions and settings...."
        )

#### Getting Current settings and versions
def SwitchInput():
    sys.stdout.write("\r%d%%" % 0)
    sys.stdout.flush()
    #### Enable logging: flash:/logfile/logfile.log
    comware.CLI('system ; info-center logfile frequency 1 ; info-center source SHELL logfile level debugging ; info-center source SNMP logbuffer level debugging', False)
    #### Get Current IRF Member
    get_memberid = comware.CLI('display irf link', False).get_output()
    for line in get_memberid:
        if 'Member' in line:
            s1 = line.rindex('Member') + 7
            e1 = len(line)
            memberid = line[s1:e1]
    sys.stdout.write("\r%d%%" % 25)
    sys.stdout.flush()
    #### Get SwitchModel
    get_model = comware.CLI('display int ten brief', False).get_output()
    for line in get_model:
        if '/0/28' in line:
            model = "24 Ports"
        if '/0/52' in line:
            model = "48 Ports"
    sys.stdout.write("\r%d%%" % 50)
    sys.stdout.flush()
    #### Get Mac-address
    get_mac_address = comware.CLI('dis device manuinfo | in MAC_ADDRESS', False).get_output()
    for line in get_mac_address:
        if 'MAC_ADDRESS' in line:
            s2 = line.rindex('MAC_ADDRESS') + 23
            e2 = len(line)
            mac_address = line[s2:e2]
    #### Get Switch Software Version
    get_sw_version = comware.CLI('display version | in Software', False).get_output()
    sw_version = get_sw_version[1]
    sys.stdout.write("\r%d%%" % 75)
    sys.stdout.flush()
    #### Get PoE Software Version
    try:
        comware.CLI('system ; poe enable pse ' + str(poe_pse_numbers[memberid]), False).get_output()
    except SystemError:
        poe_version = 'N/A'
    try:
        comware.CLI('system ; int gig' + memberid + '/0/1 ; poe enable ', False).get_output()
    except SystemError:
        poe_version = 'N/A'
    try:
        get_poe_version = comware.CLI('display poe pse | in Software', False).get_output()
        for line in get_poe_version:
            if 'Software' in line:
                s3 = line.rindex('Software') + 31
                e3 = len(line)
                poe_version = line[s3:e3]
    except SystemError:
        poe_version = 'N/A'
    sys.stdout.write("\r%d%%\n" % 100)
    sys.stdout.flush()
    return memberid, model, mac_address, sw_version, poe_version


#### Startmenu for deploying the switch
def StartMenu(memberid, model, mac_address, sw_version, poe_version):
    checkbox1 = checkbox2 = checkbox3 = checkbox4 = checkbox5 = checkbox6 = set_memberid = ''
    Menu = True
    while Menu:
        print   "\n" * 5 + "Current switch information:",\
                "\n  Current switch model         " + str(model),\
                "\n  Current MAC-address          " + str(mac_address),\
                "\n  Current software version     " + str(sw_version),\
                "\n  Current PoE version          " + str(poe_version),\
                "\n  Current Member-ID            " + str(memberid),\
                "\n  Newly chosen Member-ID       " + str(set_memberid),\
                "\n" * 2 + "Files ready for installation:",\
                "\n  Switch Boot-file             " + str(bootfile),\
                "\n  Switch System-file           " + str(sysfile),\
                "\n  Switch PoE software-file     " + str(poefile),\
                "\n" * 2 + "%-60s %-1s %-1s %-1s" % ("1.Update switch firmware", "[", checkbox1, "]"),\
                "\n%-60s %-1s %-1s %-1s" % ("2.Update PoE firmware", "[", checkbox2, "]"),\
                "\n%-60s %-1s %-1s %-1s" % ("3.Download optional files", "[", checkbox3, "]"),\
                "\n%-60s %-1s %-1s %-1s" % ("4.Change IRF Member-ID only", "[", checkbox4, "]"),\
                "\n%-60s %-1s %-1s %-1s" % ("5.Change IRF Member-ID and set IRF-port-config", "[", checkbox5, "]"),\
                "\n%-60s %-1s %-1s %-1s" % ("6.Trigger iMC for deployment (min. firmware v3109P05!)", "[", checkbox6, "]"),\
                "\n%-60s " % ("7.Run selection"),\
                "\n%-60s " % ("8.Exit/Quit and start CLI"),\
                "\n%-60s " % ("9.Exit/Quit and reboot")
        ans=raw_input("\nWhat would you like to do? ")
        if ans=="1":
            checkbox1 = "X"
            checkbox6 = ""
        elif ans=="2":
            checkbox2 = "X"
            checkbox6 = ""
        elif ans=="3":
            checkbox3 = "X"
        elif ans=="4":
            set_memberid = raw_input("Enter new Member-ID: ")
            checkbox4 = "X"
        elif ans=="5":
            set_memberid = raw_input("Enter new Member-ID: ")
            checkbox4 = "X"
            checkbox5 = "X"
            checkbox6 = ""
        elif ans=="6":
            checkbox1 = ""
            checkbox2 = ""
            checkbox5 = ""
            checkbox6 = "X"
        elif ans=="7":
            Menu = False
        elif ans=="8":
            print "\nQuiting script, starting CLI...\n"
            quit()
        elif ans=="9":
            print "\nQuiting script and rebooting...\n"
            comware.CLI('reboot force')
            quit()
        else:
            print("\n Not Valid Choice Try again")
    return checkbox1, checkbox2, checkbox3, checkbox4, checkbox5, checkbox6 ,set_memberid

#### Switch software update
def SoftwareUpdate(checkbox1):
    if checkbox1 == "X":
        print "\nUpdating Switch Firmware....\n"
        try:
            comware.CLI("tftp " + tftpsrv + " get " + bootfile)
            print "\nSwitch Firmware download successful\n"
        except SystemError as s:
            print "\nSwitch Firmware download successful\n"
        try:
            comware.CLI("tftp " + tftpsrv + " get " + sysfile)
            print "\nSwitch Firmware download successful\n"
        except SystemError as s:
            print "\nSwitch Firmware download successful\n"
        try:
            comware.CLI("boot-loader file boot flash:/" + bootfile + " system flash:/" + sysfile + " all main")
            print "\nConfiguring boot-loader successful\n"
        except SystemError as s:
            print s
            print "\nChange bootloader successful\n"
    else:
        print "\nSkipping Switch Firmware update"

#### Switch poe update
def PoEUpdate(checkbox2, memberid):
    if checkbox2 == 'X':
        print "\nUpdating PoE Firmware....\n"
        try:
            comware.CLI("tftp " + tftpsrv + " get " + poefile)
            print "\nPoE Firmware download successful\n"
        except SystemError as s:
            print "\nPoE Firmware download successful\n"
        try:
            print "\nUpdating PoE Firmware..."
            comware.CLI("system ; poe update full " + poefile + " pse " + str(poe_pse_numbers[memberid]))
            print "\nPoE-Update successful\n"
        except SystemError as s:
            print "\nSkipping PoE-Update, member not available\n"
    else:
        print "\nSkipping PoE firmware update"


#### Download optional files

def OptFiles(checkbox3):
    if checkbox3 == 'X':
        print "\nDownloading optional files..."
    	try:
            if optional_file1:
                comware.CLI('tftp ' + tftpsrv + ' get ' + optional_file1)
    	except SystemError as s:
    		print "\nDownload file successful\n"
        try:
            if optional_file2:
                comware.CLI('tftp ' + tftpsrv + ' get ' + optional_file2)
    	except SystemError as s:
    		print "\nDownload file successful\n"
    else:
        print "\nSkipping optional files"

#### Change IRF MemberID
def ChangeIRFMemberID(memberid, checkbox4, set_memberid):
    if checkbox4 == 'X':
        print "\nChanging IRF MemberID..."
        comware.CLI("system ; irf member " + memberid + " renumber " + set_memberid)
    else:
        print "\nskipping IRF MemberID Change"


#### Set IRFPorts in startup config
def SetIRFPorts(memberid, model, checkbox5, set_memberid):
    if checkbox5 == 'X':
        if model == "48 Ports":
            print ('\n' * 5) + 'Deploying IRF-Port-config for 48 ports switch...\n'
        if model == "24 Ports":
            print ('\n' * 5) + 'Deploying IRF-Port-config for 24 ports switch...\n'
        set_prio = irf_prio_numbers[set_memberid]
        startup_file = open('flash:/startup.cfg', 'w')
        startup_file.write("\nirf member "+ set_memberid +" priority "+ set_prio + "\n")
        if model == "48 Ports":
            startup_file.write("\nirf-port "+ set_memberid +"/1")
            startup_file.write("\nport group interface Ten-GigabitEthernet"+ set_memberid + irf_48_port_1 + '\n')
            startup_file.write("\nirf-port "+ set_memberid +"/2")
            startup_file.write("\nport group interface Ten-GigabitEthernet"+ set_memberid + irf_48_port_2 + '\n')
        if model == "24 Ports":
            startup_file.write("\nirf-port "+ set_memberid +"/1")
            startup_file.write("\nport group interface Ten-GigabitEthernet"+ set_memberid + irf_24_port_1 + '\n')
            startup_file.write("\nirf-port "+ set_memberid +"/2")
            startup_file.write("\nport group interface Ten-GigabitEthernet"+ set_memberid + irf_24_port_2 + '\n')
        startup_file.close()
        comware.CLI("startup saved-configuration startup.cfg")
    else:
        print "\nSkipping IRF-Port-config"

#### Trigger iMC for auto-deployment
def TriggeriMC(checkbox6):
    if checkbox6 == 'X':
        print "\nTriggering iMC for deploy, please wait..."
        comware.CLI('system ; snmp-agent ; snmp-agent community read ' + imc_snmpread + ' ; snmp-agent community write ' + imc_snmpwrite + ' ; snmp-agent sys-info version all')
        try:
    		comware.CLI('tftp ' + tftpsrv + ' get ' + imc_bootfile + ' tmp.cfg')
	except SystemError as s:
    		print "\nDownload file successful\n"
        for s in range(300):
                sys.stdout.write("\r%s%s%s" % ("iMC Triggered successfully, waiting for config...", str(300 - s), " seconds remaining"))
                sys.stdout.flush()
                time.sleep( 1 )
    else:
        print "\nSkipping iMC deploy"

def Reboot():
    comware.CLI('reboot force')
    quit()


#### Define main function
def main():
    (memberid, model, mac_address, sw_version, poe_version) = SwitchInput()
    (checkbox1, checkbox2, checkbox3, checkbox4, checkbox5, checkbox6 ,set_memberid) = StartMenu(memberid, model, mac_address, sw_version, poe_version)
    SoftwareUpdate(checkbox1)
    PoEUpdate(checkbox2, memberid)
    OptFiles(checkbox3)
    ChangeIRFMemberID(memberid, checkbox4, set_memberid)
    SetIRFPorts(memberid, model, checkbox5, set_memberid)
    TriggeriMC(checkbox6)
    Reboot()


if __name__ == "__main__":
    main()


