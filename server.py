# Jacqueline Lee and Vivek Paramasivam, 
# CSE 461 Winter 2015

import threading
import socket
import sys
import time
import string
import re
from pprint import pprint

TIMEOUT = 10 # seconds
server_is_running = True

# Calls sys.exit
def terminate():
	# Exits the program
	sys.exit()

def timeout_function(connection):
	connection['isClosed'] = True

def reset_timer(connection):
	#print "set_timer"
	connection['timerLock'].acquire() 
	timer = connection['timer']
	if timer is not None:
		timer.cancel()
	timer = threading.Timer(TIMEOUT, timeout_function, (connection,))
	timer.start()
	connection['timerLock'].release() 

def handle_forwarding_to_server(thisConnection):
	print "new thread: handle_forwarding_to_server"
	pprint(thisConnection)
	try:
		while True:
			#print "waiting for client requests"
			time.sleep(0.1)
			data = thisConnection['clientsocket'].recv(16) # size = ?
			reset_timer(thisConnection)
			print "Recv'd from client: " + data
			if data:
				#print "Sending to server: " + data
				thisConnection['hostsocket'].sendall(data)
			elif connect_tunneling:
				if thisConnection['isClosed']:
					break
			else:
				break
	except Exception as e:
		pprint(e)
	finally:
		print "FINALLY end thread handle_forwarding_to_server clientsocket "
		thisConnection['hostsocket'].close()

# ***** RENAME THIS CHUNK LATER ***** #

def handle_client(clientsocket, address):
	print "thread: handle_client"
	header_array = []
	previous_header_line = "temp"
	current_header_line = ""

	# TODO tokenize all the header lines
	while len(previous_header_line) != 0:
		curr_byte = clientsocket.recv(1) # Read the next byte
		#header_byte_buffer += curr_byte
		if (curr_byte == '\n'):
			# TODO: only add to header_array if its the type we ant
			#print "header: " + current_header_line
			header_array.append(current_header_line)
			previous_header_line = current_header_line;
			current_header_line = ""
			continue
		if (curr_byte == '\r'):
			continue
		current_header_line += curr_byte

	connection_closed = False
	host = ""
	hostport = 80	# default
	connect_tunneling = False

	for i in range(0, len(header_array)):
		line = header_array[i]
		if i == 0:	# First line HTTP protocol
			print  (time.strftime("%d %m %H:%M:%S")) + " >>> " + line # Do we print HTTP/1.0?
			line_arr = re.split(' |\t',line)
			# print line_arr
			print line_arr[0].lower() 
			line_arr[2] = "HTTP/1.0"
			if (line_arr[0].lower() == "connect"):
				print "CONNECT = TRUE"
				connect_tunneling = True
			if ("https://" in line_arr[1].lower()):				
				hostport = 443

			header_array[0] = line_arr[0] + " " + line_arr[1] + " " + line_arr[2]
		elif line[0:5].lower() == "host:":
			host = line[6:].lower()
			print "host: " + host
			host_arr = host.rsplit(':', 1)		# split from the right, only split 1
			# print host_arr
			if (len(host_arr) > 1):
				try:
				    value = int(host_arr[1])	# port number
				    host = host_arr[0]
				    hostport = value
				except ValueError:	# not an int(port)
				    pass 	

		elif line.lower() == "connection: keep-alive":
			connection_closed = True
			line = "connection: close"
			header_array[i] = line

		elif line.lower() == "proxy-connection: keep-alive":
			line = "proxy-connection: close"
			header_array[i] = line

	hostsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	host_address = (host, hostport)
	print "Attempting connection to " + host + ":" + str(hostport)
	connect_ret = hostsocket.connect_ex(host_address) 
	if (connect_ret != 0):
		print "host connect error: " + str(connect_ret)

	if (connect_tunneling):
		clientsocket.send('HTTP/1.0 200 OK\r\n\r\n')
		thisConnection = {
			"clientsocket" : clientsocket,
			"hostsocket" : hostsocket,
			"isClosed": False,
			"timerLock" : threading.Lock()
		}
		timer = threading.Timer(TIMEOUT, timeout_function, (thisConnection,))
		timer.start()
		thisConnection['timer'] = timer

		connect_handle_thread = threading.Thread(target=handle_forwarding_to_server, args=(thisConnection,))
		connect_handle_thread.setDaemon(True)
		connect_handle_thread.start()
	else:
		header_buffer = ""
		for i in range(0, len(header_array)):
			header_buffer += header_array[i] + '\n'
		print "header: " + header_buffer
		hostsocket.sendall(header_buffer + "\r\n")

	try:
		while True:
			time.sleep(0.1)
			data = hostsocket.recv(1024) # size = ?
			if connect_tunneling:
				if thisConnection['isClosed']:
					break
				reset_timer(thisConnection)
			elif data:
				clientsocket.sendall(data)
			else:
				break
	except Exception as e:
		pprint(e)
	finally:
		print "FINALLY end thread handle_client host: " + host + ": " + str(hostport)
		#clientsocket.close()

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






