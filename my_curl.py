from socket import *
import csv
import argparse
import re
import sys
from os.path import exists

class HTTP:
    def __init__(self, serverName, ip, port, query, url):
        '''
        Constructor
        '''
        self.client = socket(AF_INET, SOCK_STREAM)
        self.ip = ip
        self.url = url
        self.serverName = serverName
        self.port = int(port)
        self.query = query
        self.content_length = 0
        self.http_status = ""
        self.useIP = False
        self.header = bytes()
        self.code = int()
        self.addr = (serverName, int(port))
        self.client.settimeout(11)
        self.connect()
    
    def connect(self):
        try:
            ip = gethostbyname(self.serverName)
            # check if ip is valid
            if self.ip != "" and self.ip != ip:
                self.client.close()
                print("Invalid URL: IP address does not match given IP")
                exit()
            if self.ip != "":
                self.useIP = True 
            self.ip = str(ip) 
            # set the tuple to connect to based on ip or hostname
            self.addr = (self.serverName, self.port) if self.useIP == False else (self.ip, self.port)
        except:
            print("Invalid URL: Hostname not found")
            self.client.close()
            exit()
        try:
            self.client.connect(self.addr)
        except:
            print("Invalid URL: Unable to connect to server")
            self.client.close()
            exit()
    
    def sendRequest(self):
        try:
            # build the request and send it
            get = "GET " + self.query + " HTTP/1.1\r\nHost: " + self.serverName + "\r\n\r\n"
            b = get.encode('ISO-8859-1')
            self.client.sendall(b)
        except:
            print("Invalid URL: Unable to send request")
            self.client.close()
            exit()
    
    def get_header(self):
        try:
            i = 0
            # get the header
            while True:
                data = self.client.recv(1) 
                # if the first byte received is b'', there is an error; raise an exception. This would apply particularly to port 443
                if i == 0 and data == b'': 
                    self.status(False)
                    raise Exception("[Errno 54] Connection reset by peer")
                # if there is no more data to get
                if data == None or b'\r\n\r' in self.header:
                    break
                self.header += data
                i += 1
        except Exception as e:
            self.http_status = str(e)
            self.code = int(re.search(r'\d+', self.http_status).group())
            self.write_to_csv("Unsuccessful")
            self.client.close()
            exit()
    
    def read_header(self):
        i = 0
        for param in self.header.split(b'\r\n'):
            if i == 0 and b'HTTP/1.1 200 OK' not in param:
                # if the first line is not 200 OK, then the request was unsuccessful
                self.http_status = param.decode("ISO-8859-1")
                self.code = [int(word) for word in self.http_status.split() if word.isdigit()][0]
                self.status(False)
                self.write_to_csv("Unsuccessful")
                self.client.close()
                exit()
            elif i == 0:
                # else, the request was successful
                self.http_status = param.decode("ISO-8859-1")
                self.code = [int(word) for word in self.http_status.split() if word.isdigit()][0]
                self.status(True)
            if b'Content-Length:' in param:
                self.content_length = int(param[len(b'Content-Length:'):])
            if b'Transfer-Encoding: chunked' in param:
                # chunked encoding is not supported
                self.write_to_csv("Unsuccessful")
                self.client.close()
                exit()
            i += 1
    
    def recv_write_content(self):
        try:
            # buffered content receiving and writing
            i = 0
            file = open("HTTPoutput1.html", "w")
            while True:
                if (i == self.content_length):
                    break
                data = self.client.recv(1024)
                file.write(data.decode("ISO-8859-1"))
                i += len(data)
            file.close()
        except:
            print("Invalid URL: Unable to receive content")
            self.client.close()
            exit()
    
    def write_to_csv(self, status):
        if exists("Log.csv") == False:
            with open("Log.csv", "w", newline='') as csvfile:
                title_col = ['Successful/Unsuccessful', 'Server Status Code', 'Requested URL', 'Hostname', 'Source IP', 'Destination IP', 'Source Port', 'Destination Port', 'Server Response Line']
                writer = csv.writer(csvfile, delimiter=',')
                writer.writerow(title_col)

        with open("Log.csv", "a", newline='') as csvfile:
            src_ip, src_port = self.client.getsockname()
            info = (
                status + ", " + str(self.code) + ", " + self.url + ", " + self.serverName + ", " + 
                src_ip + ", " + self.ip + ", " + str(src_port) + ", " + str(self.port) + ", " + self.http_status
            )
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow([info])
    
    def status(self, is_success):
        if is_success:
            print("Successful")
        else:
            print("Unsuccessful")

    def close(self):
        self.client.close()
                

# Parse the command line input
def parseUserInput(args):

    # get the URL from cmdline
    url = args.full_URL
    # create a dictionary to store the URL components
    urlDict = {
        'serverName': None,
        'serverIP': None,
        'serverPort': None,
        'serverQuery': None,
        'serverUrl': url
    }

    # check if the URL is valid - needs to have http and not https
    http = re.search(r"(?P<http>https*)://", url)
    if http != None:
        http = http.group(1)
    if http != 'http':
        print('Invalid URL: HTTP is not specified')
        exit()
    if http == 'https':
        print('Invalid URL: HTTPS is not supported')
        exit()
    
    # Check for a hostname or IP address
    serverName = re.findall("([a-z]+(\.[a-zA-z0-9]+){1,5})", url)
    # re.findall returns a list of tuples, so we need to extract the first element
    if serverName != []:
        serverName = serverName[0]
    ip = re.findall("([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})", url)
    if len(ip) > 0:
        ip = ip[0]
    domain = url[7:]
    query = ""
    
    # If the server name isn't found, then it must be an IP address
    if (serverName is not None and not domain.startswith(serverName)) or serverName is None:
        serverName = None
    
    if serverName == None:
        # if both ip and server name are not found, then the URL is invalid
        if (len(ip) == 0):
            print('Invalid URL: No hostname or IP specified')
            exit()
        # if an IP address is present but there is no host name specified, then the URL is invalid
        if (args.hostname == None):
            print('Invalid URL: No hostname specified.')
            exit()
        # get the hostname and IP from the command line
        urlDict['serverName'] = args.hostname
        urlDict['serverIP'] = ip
        query = url.replace("http://" + ip, "", 1) # set the query to url without http://
    else:
        # else, server name exists so we grab it, update the dictionary, and set the query
        name, _ = serverName
        urlDict['serverName'] = name
        query = url.replace("http://" + name, "", 1)
    
    if len(query) != 0:
        # if there is a query and a port indicator exists, we need to check if the port is actually specified
        if query[0] == ':':
            count = 0
            for c in query:
                if count == 0:
                    count += 1
                    continue
                if not c.isdigit():
                    break
                count += 1
            if count == 0:
                print('Invalid URL: No port specified')
                exit()
            # set the port to the port specified in the query, set the query
            urlDict['serverPort'] = int(query[1:count])
            urlDict['serverQuery'] = query[count:]
        else:
            # else set the port to 80 and query as it is
            urlDict['serverPort'] = "80"
            urlDict['serverQuery'] = query
    return urlDict


# create command line parser
parser = argparse.ArgumentParser(description='Curl a URL')
parser.add_argument('full_URL', type=str, help='http://hostname[ip]:[port]/[query]')
parser.add_argument('hostname', type=str, nargs = '?', help='Optional hostname argument')

if (len(sys.argv) < 2):
    parser.print_help()
    exit()

# get the args from the command line
args = parser.parse_args()
# parse the args
urlDict = parseUserInput(args)
ip = ""
query = "/"
port = "80"
# get the ip, query, and port
if urlDict["serverIP"] != None:
    ip = urlDict["serverIP"]
if urlDict["serverQuery"] != "" and urlDict["serverQuery"] != None:
    query = urlDict["serverQuery"]
if urlDict["serverPort"] != None:
    port = urlDict["serverPort"]
    
http = HTTP(urlDict["serverName"], ip, port, query, urlDict["serverUrl"])

http.sendRequest()
http.get_header()
http.read_header()
http.recv_write_content()
    
http.write_to_csv("Success")
http.close()
