from pylgtv import WebOsClient

import sys
import logging
import argparse
import socket
import struct

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

class LgCommand (object):
    def __init__(self, ip):
        self.client = WebOsClient(ip)

        self.commandLines = {
            'off': self.off, 
            'on': self.wakeonlan, 
            'software-info': self.software_info, 
            'volume-up': self.volume_up,
            'volume-down': self.volume_down,
            'current-app': self.current_app,
            'apps': self.apps,
            'services': self.services,
            'get-volume': self.get_volume,
            'get-inputs': self.get_inputs,
            'app': self.app,
            'set-volume': self.set_volume,
            'close-app': self.close_app,
            'mute': self.mute,
            'unmute': self.unmute,
            'get-mute': self.get_mute,
            'get-input': self.get_input,
            'set-input': self.set_input,
            'channel-up': self.channel_up,
            'channel-down': self.channel_down,
            'channels': self.channels,
            'get-channel': self.get_channel,
            'info': self.info,
            'set-channel': self.set_channel,

            'play': self.play,
            'pause': self.pause,
            'stop': self.stop,
            'close': self.close,
            'rewind': self.rewind,
            'fast-forward': self.fast_forward,

            'enter': self.enter,
            'delete': self.delete,

            #'3d-on': threeDOn,
            #'3d-off': threeDOff,
        }    
        
    def run(self, command, arg=None):
        return self.commandLines[command](arg);


    def delete(self, arg):
        return self.client.send_delete_key()

    def enter(self, arg):
        return self.client.send_enter_key()

    def play(self, arg):
        return self.client.play()

    def pause(self, arg):
        return self.client.pause()

    def stop(self, arg):
        return self.client.stop()

    def close(self, arg):
        return self.client.close()

    def rewind(self, arg):
        return self.client.rewind()

    def fast_forward(self, arg):
        return self.client.fast_forward()

    def info(self, arg):
        return self.client.get_channel_info()

    def set_channel(self, arg):
        return self.client.set_channel(arg)

    def get_channel(self, arg):
        return self.client.get_current_channel()

    def channels(self, arg):
        return self.client.get_channels()

    def channel_down(self, arg):
        return self.client.channel_down()

    def channel_up(self, arg):
        return self.client.channel_up()

    def get_input(self, arg):
        return self.client.get_input()

    def set_input(self, arg):
        return self.client.set_input(arg)

    def unmute(self, arg):
        return self.client.set_mute(False)

    def mute(self, arg):
        return self.client.set_mute(True)

    def get_mute(self, arg):
        return self.client.get_muted()

    def set_volume(self, arg):
        return self.client.set_volume(int(arg))

    def close_app(self, arg):
        return self.client.close_app(arg)

    def app(self, arg):
        return self.client.launch_app(arg)

    def get_inputs(self, arg):
        return self.client.get_inputs()

    def get_volume(self, arg):
        return self.client.get_volume()

    def services(self, arg):
        return self.client.get_services()

    def current_app(self, arg):
        return self.client.get_current_app()

    def apps(self, arg):
        return self.client.get_apps()

    def off(self, arg):
        self.client.power_off()
        return "TV has been turned off."

    def software_info(self, arg):
        return self.check()

    def volume_down(self, arg):
        return self.client.volume_down()

    def volume_up(self, arg):
        return self.client.volume_up()

    def wakeonlan(self, mac):
        if mac is not None:
            addr_byte = mac.split(':')
            hw_addr = struct.pack('BBBBBB', int(addr_byte[0], 16),
                                  int(addr_byte[1], 16),
                                  int(addr_byte[2], 16),
                                  int(addr_byte[3], 16),
                                  int(addr_byte[4], 16),
                                  int(addr_byte[5], 16))
            msg = b'\xff' * 6 + hw_addr * 16
            socket_instance = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            socket_instance.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            socket_instance.sendto(msg, ('<broadcast>', 9))
            socket_instance.close()
            return "TV has been turned on."
        else:
            return "mac address (arg) not set. use -h for help."






    def check(self):
        return self.client.get_software_info()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ip", help="ip address of the tv")
    
    parser.add_argument("-c", "--command", help="the command to run", default='')
    parser.add_argument("-a", "--arg", help="command argument", default=None)
    args = parser.parse_args()
    
    cmd = LgCommand(args.ip)
    if(args.command):
        print(cmd.run(args.command, args.arg))
    else:
        cmd.check()
        print("TV is on.")
                
main()
