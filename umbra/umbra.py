#!/usr/bin/env python
from json import dumps, loads
import os,sys,argparse, urllib2
import websocket
import thread
import time
import uuid
import logging
import threading
logging.basicConfig(level=logging.DEBUG)

class Umbra:
    def __init__(self, port):
        self.cmd_id = 0
        self.chrome_debug_port = port
        self.launch_tab_socket = self.get_websocket(self.on_open)
        self.launch_tab_socket.run_forever()
        
    def get_websocket(self, on_open, url=None):
        debug_info = loads(urllib2.urlopen("http://localhost:%s/json" % self.chrome_debug_port).read())
        if url: #Polling for the data url we used to initialize the window
            while not filter(lambda x: x['url'] == url, debug_info):
                debug_info = loads(urllib2.urlopen("http://localhost:%s/json" % self.chrome_debug_port).read())
                time.sleep(0.5)
            debug_info = filter(lambda x: x['url'] == url, debug_info)
        return_socket = websocket.WebSocketApp(debug_info[0]['webSocketDebuggerUrl'], on_message = self.on_message)
        return_socket.on_open = on_open
        return return_socket
        
    def on_message(self, ws, message):
        message = loads(message)
        if "method" in message.keys() and message["method"] == "Network.requestWillBeSent":
            pass #print message
            
    def on_open(self, ws):
        self.fetch_url("http://archive.org")
        time.sleep(10)
        sys.exit(0)
 
    def send_command(self,tab=None, **kwargs):
        if not tab:
            tab = self.launch_tab_socket
        command = {}
        command.update(kwargs)
        self.cmd_id += 1 
        command['id'] = self.cmd_id
        tab.send(dumps(command))
       
    def fetch_url(self, url):
        new_page = 'data:text/html;charset=utf-8,<html><body>%s</body></html>' % str(uuid.uuid4())
        self.send_command(method="Runtime.evaluate", params={"expression":"window.open('%s');" % new_page})
        def on_open(ws):
            self.send_command(tab=ws, method="Network.enable")       
            self.send_command(tab=ws, method="Runtime.evaluate", params={"expression":"document.location = '%s';" % url})       
        socket = self.get_websocket(on_open, new_page)
        threading.Thread(target=socket.run_forever).start()

class Chrome():
    def __init__(self, port):
        self.port = port

    def __enter__(self):
        import psutil, subprocess
        self.chrome_process = subprocess.Popen(["google-chrome", "--remote-debugging-port=%s" % self.port])
        start = time.time()
        open_debug_port = lambda conn: conn.laddr[1] == int(self.port)
        chrome_ps_wrapper = psutil.Process(self.chrome_process.pid)
        while time.time() - start < 10 and len(filter(open_debug_port, chrome_ps_wrapper.get_connections())) == 0:
            time.sleep(1)
        if len(filter(open_debug_port, chrome_ps_wrapper.get_connections())) == 0:
            self.chrome_process.kill()
            raise Exception("Chrome failed to listen on the debug port in time!")

    def __exit__(self, *args):
        print "Killing"
        self.chrome_process.kill() 

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),
            description='umbra - Browser automation tool',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument('-p', '--port', dest='port', default='9222',
            help='Port to have invoked chrome listen on for debugging connections')
    args = arg_parser.parse_args(args=sys.argv[1:])
    with Chrome(args.port):
        Umbra(args.port)
