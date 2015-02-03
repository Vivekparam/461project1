# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

import threading
import socket
import sys
import time
import string
import re

TIMEOUT = 10 # seconds
server_is_running = True

# Calls sys.exit
def terminate():
	# Exits the program
	sys.exit()

def timeout_function(connection):
	connection.isClosed = True

def reset_timer(connection):
	#print "set_timer"
	connection.timerLock.acquire() 
	timer = connection.timer
	if timer is not None:
		timer.cancel()
	timer = threading.Timer(TIMEOUT, timeout_function) 
	timer.start()
	connection.timerLock.release() 

def handle_forwarding_to_server(thisConnection):
	print "new thread: handle_forwarding_to_server"
	try:
		while True:
			print "Waiting for data from client"
			data = thisConnection.clientsocket.recv(16) # size = ?
			reset_timer(thisConnection)
			print "Recv'd from client: " + data
			if data:
				print "Sending to server: " + data
				thisConnection.hostsocket.sendall(data)
			elif connect_tunneling:
				if thisConnection.isClosed:
					break
			else:
				break
	finally:
		print "FINALLY"
		thisConnection.hostsocket.close()

# ***** RENAME THIS CHUNK LATER ***** #

def handle_client(clientsocket, address):
	print "handle_client"
	header_array = []

	header_byte_buffer = "" # all headers as we read them. To be send to host.
	previous_header_line = "temp"
	current_header_line = ""

	# TODO tokenize all the header lines
	while len(previous_header_line) != 0:
		curr_byte = clientsocket.recv(1) # Read the next byte
		header_byte_buffer += curr_byte
		if (curr_byte == '\n'):
			# TODO: only add to header_array if its the type we ant
			print "current line: " + current_header_line
			header_array.append(current_header_line)
			previous_header_line = current_header_line;
			current_header_line = ""
			continue
		if (curr_byte == '\r'):
			continue
		current_header_line += curr_byte

	print "header done"

	connection_closed = False
	host = ""
	hostport = 80	# default port
	connect_tunneling = False

	for i in range(0, len(header_array)):
		line = header_array[i]
		if i == 0:	# First line HTTP protocol
			print  (time.strftime("%d %m %H:%M:%S")) + " >>> " + line # Do we print HTTP/1.0?
			line_arr = re.split(' ',line)
			print line_arr
			if (line_arr[0].lower() == "CONNECT"):
				connect_tunneling = True
			if ("https://" in line_arr[1].lower()):				
				hostport = 443

		elif line[0:5].lower() == "host:":
			host = line[6:].lower()
			print "host: " + host

			host_arr = host.rsplit(':', 1)		# split from the right, only split 1
			print host_arr
			if (len(host_arr) > 1):
				try:
				    value = int(host_arr[1])		# port number
				    host = host_arr[0]
				    hostport = value
				except ValueError:
				    pass 	# not an int (port)

		elif string.lower(line) == "connection: close":
			connection_closed = true

	hostsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	host_address = (host, hostport)
	print "Attempting connection to " + host + ":" + str(hostport)
	hostsocket.connect(host_address)
	# clientsocket.send('HTTP/1.0 200 OK\r\n\r\n')
	hostsocket.sendall(header_byte_buffer)
	# while True:
	# 	data = clientsocket.recv(16) # size = ?
	# 	print "Recv'd from client: " + data
	# 	if data:
	# 		hostsocket.sendall(data)
	# 	else: 
	# 		break
	
	

	if (connect_tunneling):
		thisConnection = {
			"clientsocket" : clientsocket,
			"hostsocket" : hostsocket,
			"isClosed": False,
			"timerLock" : threading.Lock()
		}
		timer = threading.Timer(TIMEOUT, timeout_function, (thisConnection,))
		timer.start()
		thisConnection.timer = timer

		connect_handle_thread = threading.Thread(target=handle_forwarding_to_server, args=(thisConnection,))
		connect_handle_thread.setDaemon(True)
		connect_handle_thread.start()

	# thread forwarding from server to client
	try:
		while True:
			print "Waiting for data from server"
			data = hostsocket.recv(16) # size = ?
			if (connect_tunneling):
				reset_timer(thisConnection)
			print "Recv'd from server: " + data
			if data:
				print "Sending to client: " + data
				clientsocket.sendall(data)
			elif connect_tunneling:
				if thisConnection.isClosed:
					break
			else:
				break
	finally:
		print "FINALLY"
		clientsocket.close()

# ***** We create a separate thread to read for eof from console ***** #

# Loops until reading eof or 'q'
# from stdin, then sets server_is_running
# to false and terminates thread.
def readForEof():
	global server_is_running
	try: 
		while True:
			uin = sys.stdin.readline().strip()
			if not uin or (uin is 'q'):
				if not uin: print "eof"
				# got eof
				server_is_running = False
				terminate()
	except KeyboardInterrupt:
		server_is_running = False
		terminate()

# Create thread which reads from stdin
user_input_thread = threading.Thread(target=readForEof)
user_input_thread.setDaemon(True)
user_input_thread.start()

# ***** Create the listening thread, which dispatches child threads for each new connection ***** #


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = socket.gethostname()
server.bind((host, int(sys.argv[1])))
server.listen(5)
print  (time.strftime("%d %m %H:%M:%S")) + " - Proxy listening on " + host + ":" + sys.argv[1]


# Loops while server_is_running is true,
# accepting packets from clients and 
# sorting the packet into the proper Queue
# for future processing. For more information see
# handle_packet.
def acceptConnections():
	global server_is_running
	while server_is_running:
		(clientsocket, address) = server.accept()
		# perform basic packet handling then put it in a queue
		# create thread which deals with this cleint
		connection_handle_thread = threading.Thread(target=handle_client, args=(clientsocket, address))
		connection_handle_thread.setDaemon(True)
		connection_handle_thread.start()



# create thread which is accepting packets from clients
server_connection_thread = threading.Thread(target=acceptConnections)
server_connection_thread.setDaemon(True)
server_connection_thread.start()




# ***** Keep server alive until it is time ***** # 
# Exit when server stops running
while server_is_running:
	# loop de loop
	continue

server.close()
# End the process
terminate()






