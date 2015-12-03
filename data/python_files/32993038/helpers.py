import socket
import struct
import binascii
import urllib
import urllib2
import bencode
import urlparse
import time
import uuid

def __udp_scrape(url, checksum):
    """
    Makes a UDP scrape request to the tracker.
    """
    try:
        payload = struct.pack('>QLL20s', 0x41727101980, 2, 1, binascii.a2b_hex(checksum))
    except Exception, e:
        raise e

    try:
        address = tuple(urlparse.urlparse(url).netloc.split(':'))
        connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except Exception, e:
        raise e

    try:
        connection.sendto(payload, (address[0], int(address[1])))
        response = connection.recv(1024)
    except Exception, e:
        raise e

    try:
         if struct.unpack('>L', response[:4]) == '2':
             raise Exception("An unknown tracker error has occurred.")
    except Exception, e:
        raise e

    try:
        action = struct.unpack('>LLLLL', response[:20])
    except Exception, e:
        raise e

    peers = action[3] + action[4]

    return peers

def __tcp_scrape(url, checksum):
    """
    Makes a TCP scrape request to the tracker.
    """

    try:
        payload = urllib.urlencode({'info_hash': binascii.a2b_hex(checksum)})
    except Exception, e:
        raise e

    try:
        request = urllib2.Request(url.replace('announce', 'scrape') + '?' + payload)
    except Exception, e:
        raise e

    try:
        connection = urllib2.urlopen(request)
        response = connection.read()
    except Exception, e:
        raise e

    try:
         if not connection.getcode() == 200:
             raise Exception("An unknown tracker error has occurred. The tracker returned an error code '%s'" % (connection.getcode()))
    except Exception, e:
        raise e

    try:
        response = bencode.bdecode(response)
    except Exception, e:
        raise e

    peers = response['files'][binascii.a2b_hex(checksum)]['incomplete'] + response['files'][binascii.a2b_hex(checksum)]['complete']

    return peers

def scrape(url, checksum):
    """
    Scrapes the tracker using TCP or UDP.
    """
    if urlparse.urlparse(url).scheme == 'udp':
        start_time = time.time()
        peers = __udp_scrape(url, checksum)
        end_time = time.time()
        return peers, end_time - start_time
    else:
        start_time = time.time()
        peers = __tcp_scrape(url, checksum)
        end_time = time.time()
        return peers, end_time - start_time