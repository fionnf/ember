STA_IF = 0
class WLAN:
    def __init__(self, mode): pass
    def active(self, on=None): return True
    def isconnected(self): return True
    def scan(self): return [(b"TestNet", 0, 0, 0, 0, 0)]
    def connect(self, s, p): pass
    def disconnect(self): pass
    def ifconfig(self): return ("192.168.1.42", "", "", "")
