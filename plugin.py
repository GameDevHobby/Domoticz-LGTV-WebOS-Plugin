# 
#       LG TV WebOS 3 Plugin Author: Chris Gheen @GameDevHobby, 2017
#       
"""
<plugin key="lgtv" name="LG TV (with Kodi remote)" author="Chris Gheen @GameDevHobby" version="0.5" wikilink="https://github.com/GameDevHobby/lgtv-webos-domoticz-plugin" externallink="http://www.lg.com/us/tvs">
    <description>
* Enable remote start on your TV: [Settings] => [Network] => [Home Network Setup] => [Remote Start] => [On]<br/>
* Give your TV a static IP address, or make a DHCP reservation for a specific IP address in your router.<br/>
* Determine the MAC address of your TV: [Settings] => [Network] => [Network Setup] => [View Network Status]<br/>
    </description>
    <params>
        <param field="Address" label="IP address" width="200px" required="true" default="192.168.1.191"/>
        <param field="Mode1" label="Max volume" width="30px" required="true" default="20"/>
        <param field="Mode2" label="MAC address" width="200px" required="true" default="AA:BB:CC:DD:EE:FF"/>
        <param field="Mode3" label="Volume bar" width="75px">
            <options>
                <option label="True" value="Volume"/>
                <option label="False" value="Fixed" default="true" />
            </options>
        </param>
        <param field="Mode5" label="Update interval (sec)" width="30px" required="true" default="30"/>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true" />
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import datetime
import subprocess

class BasePlugin:
    isConnected = False
    powerOn = False
    tvState = 0
    tvVolume = 0
    tvSource = 0
    tvPlaying = {} #''
    SourceOptions3 = {}
    SourceOptions4 = {}
    startTime = ''
    endTime = ''
    perc_playingTime = 0
    debug = False

    def run(self, command, arg=""):
        cmd = "python3 " + Parameters["HomeFolder"] + "lg.py " + Parameters["Address"] + " -c " + command 
        if arg != "":
            cmd = cmd + " -a " + arg

        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        
        out = out.decode("utf-8")
        err = err.decode("utf-8")
        
        #Domoticz.Debug(str(p.returncode))
        #Domoticz.Debug(out)
        #Domoticz.Debug(err)
        self.debug = False

        if p.returncode == 1:
            return str(err)
        else:
            return str(out)
    
    # Executed once at reboot/update, can create up to 255 devices
    def onStart(self):
        global _tv
        
        if Parameters["Mode6"] == "Debug": 
            Domoticz.Debugging(1)
            self.debug = True

        #TODO: get number of inputs and apps to build list
        
        self.SourceOptions3 =   {   "LevelActions"  : "||||||", 
                                    "LevelNames"    : "Off|TV|HDMI1|HDMI2|HDMI3|Hulu|Netflix|Amazon|Youtube|iPlayer|Unknown",
                                    "LevelOffHidden": "true",
                                    "SelectorStyle" : "0"
                                }
                                    
        if (len(Devices) == 0):
            Domoticz.Device(Name="Status", Unit=1, Type=17, Image=2, Switchtype=17).Create()
            if Parameters["Mode3"] == "Volume": Domoticz.Device(Name="Volume", Unit=2, Type=244, Subtype=73, Switchtype=7, Image=8).Create()
            Domoticz.Device(Name="Source", Unit=3, TypeName="Selector Switch", Switchtype=18, Image=2, Options=self.SourceOptions3).Create()
            Domoticz.Log("Devices created")
        elif (Parameters["Mode3"] == "Volume" and 2 not in Devices):
            Domoticz.Device(Name="Volume", Unit=2, Type=244, Subtype=73, Switchtype=7, Image=8).Create()
            Domoticz.Log("Volume device created")
        elif (Parameters["Mode3"] != "Volume" and 2 in Devices):
            Devices[2].Delete()
            Domoticz.Log("Volume device deleted")
        elif 1 not in Devices:
            Domoticz.Device(Name="Status", Unit=1, Type=17, Image=2, Switchtype=17).Create()
            Domoticz.Log("TV device created")
        elif 3 not in Devices:
            Domoticz.Device(Name="Source", Unit=3, TypeName="Selector Switch", Switchtype=18, Image=2, Options=self.SourceOptions3).Create()
            Domoticz.Log("Source device created")
        else:
            if (1 in Devices): self.tvState = Devices[1].nValue    #--> of sValue
            if (2 in Devices): self.tvVolume = Devices[2].nValue   #--> of sValue
            if (3 in Devices): self.tvSource = Devices[3].sValue
        
        # Set update interval, values below 10 seconds are not allowed due to timeout of 5 seconds in bravia.py script
        updateInterval = int(Parameters["Mode5"])
        if updateInterval < 30:
            if updateInterval < 10: updateInterval == 10
            Domoticz.Log("Update interval set to " + str(updateInterval) + " (minimum is 10 seconds)")
            Domoticz.Heartbeat(updateInterval)
        else:
            Domoticz.Heartbeat(30)
        if self.debug == True:
            DumpConfigToLog()

        return #--> return True

    def onConnect(self, Status, Description):
        if (Status == 0):
            self.isConnected = True
            Domoticz.Log("Connected successfully to: "+Parameters["Address"])
        else:
            self.isConnected = False
            self.powerOn = False
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Parameters["Address"])
            Domoticz.Debug("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+" with error: "+Description)
            self.SyncDevices()
        return
    
    # Called when a single,complete message is received from the external hardware
    def onMessage(self, Data, Status, Extra):
        Domoticz.Log('onMessage: '+str(Data)+" ,"+str(Status)+" ,"+str(Extra))    
        return True
    
    # Executed each time we click on device through Domoticz GUI
    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

        Command = Command.strip()
        action, sep, params = Command.partition(' ')
        action = action.capitalize()
        params = params.capitalize()
       
        if self.powerOn == False:
            if Unit == 1:     # TV power switch
                if action == "On":
                    try:
                        self.run("on", Parameters["Mode2"])#_tv.turn_on()
                        self.tvPlaying = "TV starting" # Show that the TV is starting, as booting the TV takes some time
                        #self.tvSource = "10"
                        self.SyncDevices()
                    except Exception as err:
                        Domoticz.Log('Error when starting TV using WOL (' +  err + ')')
        else:
            if Unit == 1:     # TV power switch
                if action == "Off":
                    self.run("off")#_tv.turn_off()
                    self.tvPlaying = "Off"
                    self.SyncDevices()

                
                # Remote buttons (action is capitalized so chosen for Command)
                elif Command == "ChannelUp": self.run("channel-up")#_tv.send_req_ircc("AAAAAQAAAAEAAAAQAw==")       # ChannelUp
                elif Command == "ChannelDown": self.run("channel-down")#_tv.send_req_ircc("AAAAAQAAAAEAAAARAw==")     # ChannelDown
                #elif Command == "Channels": #_tv.send_req_ircc("AAAAAQAAAAEAAAA6Aw==")        # Display, shows information on what is playing
                elif Command == "VolumeUp": self.run("volume-up")#_tv.send_req_ircc("AAAAAQAAAAEAAAASAw==")        # VolumeUp
                elif Command == "VolumeDown": self.run("volume-down")#_tv.send_req_ircc("AAAAAQAAAAEAAAATAw==")      # VolumeDown
                #elif Command == "Mute": #_tv.send_req_ircc("AAAAAQAAAAEAAAAUAw==")            # Mute
                elif Command == "Select": self.run("enter")#_tv.send_req_ircc("AAAAAQAAAAEAAABlAw==")          # Confirm
                #elif Command == "Up": #_tv.send_req_ircc("AAAAAQAAAAEAAAB0Aw==")              # Up
                #elif Command == "Down": #_tv.send_req_ircc("AAAAAQAAAAEAAAB1Aw==")            # Down
                #elif Command == "Left": #_tv.send_req_ircc("AAAAAQAAAAEAAAA0Aw==")            # Left
                #elif Command == "Right": #_tv.send_req_ircc("AAAAAQAAAAEAAAAzAw==")           # Right
                #elif Command == "Home": #_tv.send_req_ircc("AAAAAQAAAAEAAABgAw==")            # Home
                elif Command == "Info": self.run("info")#_tv.send_req_ircc("AAAAAgAAAKQAAABbAw==")            # EPG
                #elif Command == "Back": #_tv.send_req_ircc("AAAAAgAAAJcAAAAjAw==")            # Return
                #elif Command == "ContextMenu": #_tv.send_req_ircc("AAAAAgAAAJcAAAA2Aw==")     # Options
                #elif Command == "FullScreen": #_tv.send_req_ircc("AAAAAQAAAAEAAABjAw==")      # Exit
                #elif Command == "ShowSubtitles": #_tv.send_req_ircc("AAAAAQAAAAEAAAAlAw==")   # Input
                elif Command == "Stop": self.run("stop")#_tv.send_req_ircc("AAAAAgAAAJcAAAAYAw==")            # Stop
                elif Command == "BigStepBack": self.run("pause")#_tv.send_req_ircc("AAAAAgAAAJcAAAAZAw==")     # Pause
                elif Command == "Rewind": self.run("rewind")#_tv.send_req_ircc("AAAAAgAAAJcAAAAbAw==")          # Rewind
                elif Command == "PlayPause": self.run("pause")#_tv.send_req_ircc("AAAAAgAAABoAAABnAw==")       # TV pause
                elif Command == "FastForward": self.run("fast-forward")#_tv.send_req_ircc("AAAAAgAAAJcAAAAcAw==")     # Forward
                elif Command == "BigStepForward": self.run("play")#_tv.send_req_ircc("AAAAAgAAAJcAAAAaAw==")  # Play
                
            if Unit == 2:     # TV volume
                if action == 'Set': #--> and (params.capitalize() == 'Level') or (Command.lower() == 'Volume')
                    max = int(Parameters["Mode1"])
                    if Level > max:
                        self.tvVolume = str(max)
                    else:
                        self.tvVolume = str(Level)
                    #_tv.set_volume_level(self.tvVolume)
                    self.run("set-volume", self.tvVolume)
                elif action == "Off":
                    #_tv.mute_volume()
                    self.run("mute")
                    UpdateDevice(2, 0, str(self.tvVolume))
                elif action == "On":
                    #_tv.mute_volume()
                    self.run("unmute")
                    UpdateDevice(2, 1, str(self.tvVolume))
                    
            if Unit == 3:   # TV source
                if Command == 'Set Level':
                    if Level == 10:
                        #_tv.send_req_ircc("AAAAAQAAAAEAAAAAAw==") #TV Num1
                        self.GetTVInfo()
                    if Level == 20:
                        #_tv.send_req_ircc("AAAAAgAAABoAAABaAw==") #HDMI1
                        self.run("app", "com.webos.app.hdmi1")
                        self.tvPlaying = "HDMI 1"
                    if Level == 30:
                        #_tv.send_req_ircc("AAAAAgAAABoAAABbAw==") #HDMI2
                        self.run("app", "com.webos.app.hdmi2")
                        self.tvPlaying = "HDMI 2"
                    if Level == 40:
                        #_tv.send_req_ircc("AAAAAgAAABoAAABcAw==") #HDMI3
                        self.tvPlaying = "HDMI 3"                        
                        self.run("app", "com.webos.app.hdmi3")
                    if Level == 50:
                        #_tv.send_req_ircc("AAAAAgAAABoAAABdAw==") #HDMI4
                        self.tvPlaying = "Hulu"
                        self.run("app", "hulu")
                    if Level == 60:
                        #_tv.send_req_ircc("AAAAAgAAABoAAAB8Aw==") #Netflix
                        self.tvPlaying = "Netflix"
                        self.run("app", "netflix")
                    if Level == 70:
                        #_tv.send_req_ircc("AAAAAgAAABoAAAB8Aw==") #Amazon
                        self.tvPlaying = "Amazon"
                        self.run("app", "Lovefilm")
                    if Level == 80:
                        #_tv.send_req_ircc("AAAAAgAAABoAAAB8Aw==") #Youtube
                        self.tvPlaying = "Youtube"
                        self.run("app", "Youtube.Leanback.V4")
                    if Level == 90:
                        #_tv.send_req_ircc("AAAAAgAAABoAAAB8Aw==") #iPlayer
                        self.tvPlaying = "iPlayer"
                        self.run("app", "Bbc.Iplayer.3.0")
                    if Level == 100:
                        #_tv.send_req_ircc("AAAAAgAAABoAAAB8Aw==") #Unknown
                        self.tvPlaying = "Unknown"                        

                    self.tvSource = Level
                    self.SyncDevices()
            
        return

    def onDisconnect(self):
        self.isConnected = False
        Domoticz.Log("LG TV has disconnected.")
        return
        
    # Executed once when HW updated/removed
    def onStop(self):
        Domoticz.Log("onStop called")
        return True
    
    # Execution depend of Domoticz.Heartbeat(x) x in seconds
    def onHeartbeat(self):
        tvStatus = ''
        out = self.run("software-info")
        #Domoticz.Debug(out)

        if 'TimeoutError()' in out:
            tvStatus = 'off'#_tv.get_power_status()
        else:
            tvStatus = 'active'

        #Domoticz.Debug(out)
        Domoticz.Debug('Status TV: ' + tvStatus)

        if tvStatus == 'active':                            # TV is on
            self.powerOn = True
            self.GetTVInfo()
        else:                                               # TV is off or standby
            self.powerOn = False
            self.SyncDevices()

        return

    def SyncDevices(self):
        # TV is off
        if self.powerOn == False:
            if self.tvPlaying == "TV starting":         # TV is booting and not yet responding to get_power_status
                UpdateDevice(1, 1, self.tvPlaying)
                #UpdateDevice(3, 1, self.tvSource)
            else:                                       # TV is off so set devices to off
                self.ClearDevices()
        # TV is on
        else:
            if self.tvPlaying == "Off":                 # TV is set to off in Domoticz, but self.powerOn is still true
                self.ClearDevices()
            else:                                       # TV is on so set devices to on
                if not self.tvPlaying:
                    Domoticz.Debug("No information from TV received (TV was paused and then continued playing from disk) - SyncDevices")
                else:
                    UpdateDevice(1, 1, self.tvPlaying)
                    UpdateDevice(3, 1, str(self.tvSource))
                if Parameters["Mode3"] == "Volume": UpdateDevice(2, 2, str(self.tvVolume))

        return
    
    def ClearDevices(self):
        self.tvPlaying = "Off"
        UpdateDevice(1, 0, self.tvPlaying)          #Status
        if Parameters["Mode3"] == "Volume": UpdateDevice(2, 0, str(self.tvVolume))  #Volume
        self.tvSource = 0
        UpdateDevice(3, 0, str(self.tvSource))      #Source
        
        return
    
    def GetTVInfo(self):
        currentApp = str(self.run("current-app")).rstrip()
        currentInput = str(self.run("get-input")).rstrip()
        currentChannel = self.run("get-channel")
        currentInfo = self.run("info")

        self.tvPlaying = {'title': 'test', 'programTitle': None}#_tv.get_playing_info()
        Domoticz.Debug("App: " + currentApp)
        Domoticz.Debug("Input: " + currentInput)
        Domoticz.Debug("Channel: " + currentChannel)
        Domoticz.Debug("Info: " + currentInfo)

        if not "errorCode" in currentChannel:#self.tvPlaying['programTitle'] != None:      # Get information on channel and program title if tuner of TV is used
            # pylgtv seems to return invalid JSON, so parse the fragment ourselves
            if "channelName" in currentChannel:
                currentChannelInfo = currentChannel.split(',')
                currentChannelName = next((s for s in currentChannelInfo if 'channelName' in s), None).split('\'')[3]
            else:
                currentChannelName = None

            if "channelNumber" in currentChannel:
                currentChannelInfo = currentChannel.split(',')
                currentChannelNumber = next((s for s in currentChannelInfo if 'channelNumber' in s), None).split('\'')[3]
            else:
                currentChannelNumber = None

            if currentChannelNumber is not None:
                self.tvPlaying = str(currentChannelNumber + ': ' + currentChannelName )
            else:
                self.tvPlaying = str(currentChannel + ' (' + currentInfo + ')' )

            UpdateDevice(1, 1, self.tvPlaying)
            self.tvSource = 10
            UpdateDevice(3, 1, str(self.tvSource))        # Set source device to TV
        else:                               # No channel info found
            # When TV plays apps, no title information is available, it can return '' or 'com.webos.app.*'
            self.tvPlaying = currentApp.replace('com.webos.app.', '').title()  # Set the appname as fallback 
            if "hdmi1" in self.tvPlaying.lower():
                self.tvSource = 20
                UpdateDevice(3, 1, str(self.tvSource))    # Set source device to HDMI1
                self.tvPlaying = 'HDMI1'
            elif "hdmi2" in self.tvPlaying.lower():
                self.tvSource = 30
                UpdateDevice(3, 1, str(self.tvSource))    # Set source device to HDMI2
                self.tvPlaying = 'HDMI2'
            elif "hdmi3" in self.tvPlaying.lower():
                self.tvSource = 40
                UpdateDevice(3, 1, str(self.tvSource))    # Set source device to HDMI3
                self.tvPlaying = 'HDMI3'
            elif "hulu" in self.tvPlaying.lower():
                self.tvSource = 50
                UpdateDevice(3, 1, str(self.tvSource))    # Set source device to Hulu
            elif "netflix" in self.tvPlaying.lower():
                self.tvSource = 60
                UpdateDevice(3, 1, str(self.tvSource))    # Set source device to Netflix
            elif "lovefilm" in self.tvPlaying.lower():
                self.tvSource = 70
                UpdateDevice(3, 1, str(self.tvSource))    # Set source device to Amazon
            elif "youtube" in self.tvPlaying.lower():
                self.tvSource = 80
                UpdateDevice(3, 1, str(self.tvSource))    # Set source device to Youtube
            elif "iplayer" in self.tvPlaying.lower():
                self.tvSource = 90
                UpdateDevice(3, 1, str(self.tvSource))    # Set source device to iPlayer
            else:
                self.tvSource = 100
                UpdateDevice(3, 1, str(self.tvSource))    # Set source device to Unknown

            UpdateDevice(1, 1, self.tvPlaying)

        # Get volume information of TV
        if Parameters["Mode3"] == "Volume":
            #self.tvVolume = _tv.get_volume_info()
            output = self.run("get-volume")#.replace("\\n'", "").replace("'", "").replace("b", "")
            # Check if output is a digit instead of garbage
            if not str(output).isdigit():
                output = 0
            mute = self.run("get-mute")
            mute_level = 2
            if mute == "True":
                mute_level = 0
            
            Domoticz.Debug("vol: " + str(output))
            self.tvVolume = int(output)
            if self.tvVolume != None: UpdateDevice(2, mute_level, str(self.tvVolume))
                
        return

_plugin = BasePlugin()

def onStart():
    _plugin.onStart()

def onConnect(Status, Description):
    _plugin.onConnect(Status, Description)

def onMessage(Data, Status, Extra):
    _plugin.onMessage(Data, Status, Extra)

def onCommand(Unit, Command, Level, Hue):
    _plugin.onCommand(Unit, Command, Level, Hue)

def onDisconnect():
    _plugin.onDisconnect()

def onHeartbeat():
    _plugin.onHeartbeat()

# Update Device into database
def UpdateDevice(Unit, nValue, sValue, AlwaysUpdate=False):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it 
    if (Unit in Devices):
        if ((Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue) or (AlwaysUpdate == True)):
            Devices[Unit].Update(nValue, str(sValue))
            Domoticz.Log("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
    return

# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Internal ID:     '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("External ID:     '" + str(Devices[x].DeviceID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

