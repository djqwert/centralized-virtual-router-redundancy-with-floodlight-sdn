# This protocol to work correctly need a Floodlight controller
# installed and already actived inside the network

from random import random
import time
import socket  
import select
import netifaces as ni
import sys

# Set of parameters useful for this application.
# The application need 2 informations given in input with the command: python ./router [DATA1] [DATA2]
# DATA1 is the name of the interface used to communicate with the controller and to send in broadcast the vrid
# DATA2 is used to send a vrid via command line to the router
INTERFACE_NAME = sys.argv[1] + "-eth1"
INTERFACE_IP = ni.ifaddresses(INTERFACE_NAME)[ni.AF_INET][0]["addr"]
BROADCAST_ADDRESS = "10.0.2.255"
VRIP = "10.0.2.254"         # vrip used by the router
COMM_PORT = 8888            # communication port used to exchange packet between routers and controller
ROUTER_STATE = 0            # 0: no-state, 1: backup, 2: master
WAITING_TIME = 0.5          # in real cases WAITING_TIME must be about 1 ms (0.001)
VRID = int(sys.argv[2])     # router id must be beetwen 1-255
sock = None                 # socket

# This function prints the basic informations of the router like interface used to communicate
# With the controller, its address ip and its vrid
def info():

    print "[INFO]"
    print INTERFACE_NAME
    print "\tinet " + INTERFACE_IP + " netmask 255.255.255.0 " + "broadcast " + BROADCAST_ADDRESS
    print "VRID: " + str(VRID)
    
    global sock

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    print "[INFO] Socket created"

    sock.bind(("", COMM_PORT))

    print "[INFO] Socket bound to port %d" %(COMM_PORT)

    sock.sendto(str(VRID), (BROADCAST_ADDRESS, COMM_PORT))
    print "[INFO] Packet sent to %s throught port %s" %(BROADCAST_ADDRESS, COMM_PORT)
    
# The router sent its vrid in broadcast and it waits for the response from the floodlight controller,
# if the router dont receive a packet within 10 seconds, the election will stop
def election():

    global sock, ROUTER_STATE

    try:
        sock.settimeout(10)
        while True:
            data, addr = sock.recvfrom(1024)    # verifico che gli altri nodi siano attivi
            if addr[0] == VRIP:
                break;
    except:
        print "[ERR] Controller is offline"
        sock.close()
        exit()

    print "[INFO] Election terminated"

    data = int(data);

    if VRID < data:
        ROUTER_STATE = 1
    else:
        ROUTER_STATE = 2
   
# This function is very useful to empty the queue bounded with the socket
# because, in some cases, some broadcast packet could be spammed on the same router line
def manageQueue():

    global sock

    try:
        sock.setblocking(0)	    # non-blocking mode actived
        while True:
            data, addr = sock.recvfrom(1024)
    except:
        print "[INFO] Receive queue has been emptied"	
        
    sock.setblocking(1)

# Main application function. An active router can jump between the router_state 1 e 2, where
# it is waiting for a master router election or to be downgraded a backup router
def protocol():

    global sock, ROUTER_STATE

    while True:
        
        if ROUTER_STATE == 1:                       # I am waiting for my colleague router goes down
            
            print "[INFO] I am the virtual backup router"
            sock.setblocking(1)
            
            while True:
                data, addr = sock.recvfrom(1024) 
                if addr[0] == VRIP and VRID == int(data):
                    ROUTER_STATE = 2
                    break;
            
        elif ROUTER_STATE == 2:                       # I am the master! Yeah!
            
            print "[INFO] I am the virtual master router"
            sock.setblocking(0)
            
            while True:
            
                sock.sendto(str(VRID), (BROADCAST_ADDRESS, COMM_PORT));
                print "[INFO] VRRP advertisement sent to (%s, %d)" %(BROADCAST_ADDRESS, COMM_PORT)
                
                data, addr = sock.recvfrom(1024)
                
                if addr[0] == VRIP and VRID < int(data):
                    # print "Ho ricevuto un pacchetto con ", int(data) , " da: ", addr
                    ROUTER_STATE = 1
                    break;
                
                time.sleep(WAITING_TIME)  
            
        else:                                       # OMG, What did it happen here?
                                                    # in general, should must be impossible arrive here
            print "[ERR] Something went wrong during the selection role"
            sock.close()
            exit();

    sock.close()

if __name__ == '__main__':
    
    print "[INFO] Lazy VRRP started on this device"
    
    info()
    election()
    manageQueue()
    protocol()    