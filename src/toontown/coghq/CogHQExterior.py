from direct.directnotify import DirectNotifyGlobal
from toontown.battle import BattlePlace
from direct.fsm import ClassicFSM, State
from direct.fsm import State
from toontown.toonbase import ToontownGlobals
from panda3d.core import *
from otp.distributed.TelemetryLimiter import RotationLimitToH, TLGatherAllAvs
from otp.nametag import NametagGlobals
from toontown.dna.DNAParser import loadDNAFileAI, DNAStorage
from toontown.hood import ZoneUtil

class CogHQExterior(BattlePlace.BattlePlace):
    notify = DirectNotifyGlobal.directNotify.newCategory('CogHQExterior')

    def __init__(self, loader, parentFSM, doneEvent):
        BattlePlace.BattlePlace.__init__(self, loader, doneEvent)
        self.parentFSM = parentFSM
        self.fsm = ClassicFSM.ClassicFSM('CogHQExterior', [State.State('start', self.enterStart, self.exitStart, ['walk',
          'tunnelIn',
          'teleportIn',
          'doorIn']),
         State.State('walk', self.enterWalk, self.exitWalk, ['stickerBook',
          'purchase',
          'teleportOut',
          'tunnelOut',
          'doorOut',
          'died',
          'stopped',
          'WaitForBattle',
          'battle',
          'squished',
          'stopped']),
         State.State('stopped', self.enterStopped, self.exitStopped, ['walk', 'teleportOut', 'stickerBook']),
         State.State('doorIn', self.enterDoorIn, self.exitDoorIn, ['walk', 'stopped']),
         State.State('doorOut', self.enterDoorOut, self.exitDoorOut, ['walk', 'stopped']),
         State.State('stickerBook', self.enterStickerBook, self.exitStickerBook, ['walk',
          'WaitForBattle',
          'battle',
          'tunnelOut',
          'teleportOut',
          'doorOut',
          'squished',
          'died']),
         State.State('purchase', self.enterPurchase, self.exitPurchase, ['walk']),
         State.State('WaitForBattle', self.enterWaitForBattle, self.exitWaitForBattle, ['battle', 'walk']),
         State.State('battle', self.enterBattle, self.exitBattle, ['walk', 'teleportOut', 'died']),
         State.State('squished', self.enterSquished, self.exitSquished, ['walk', 'died', 'teleportOut']),
         State.State('teleportIn', self.enterTeleportIn, self.exitTeleportIn, ['walk', 'WaitForBattle', 'battle']),
         State.State('teleportOut', self.enterTeleportOut, self.exitTeleportOut, ['teleportIn', 'final', 'WaitForBattle']),
         State.State('died', self.enterDied, self.exitDied, ['quietZone']),
         State.State('tunnelIn', self.enterTunnelIn, self.exitTunnelIn, ['walk', 'WaitForBattle', 'battle']),
         State.State('tunnelOut', self.enterTunnelOut, self.exitTunnelOut, ['final']),
         State.State('final', self.enterFinal, self.exitFinal, ['start'])], 'start', 'final')

    def load(self):
        self.parentFSM.getStateNamed('cogHQExterior').addChild(self.fsm)
        BattlePlace.BattlePlace.load(self)

    def unload(self):
        self.parentFSM.getStateNamed('cogHQExterior').removeChild(self.fsm)
        del self.fsm
        BattlePlace.BattlePlace.unload(self)

    def enter(self, requestStatus):
        self.zoneId = requestStatus['zoneId']
        BattlePlace.BattlePlace.enter(self)
        self.fsm.enterInitialState()
        base.playMusic(self.loader.music, looping=1, volume=0.8)
        self.loader.geom.reparentTo(render)
        self.nodeList = [self.loader.geom]
        self._telemLimiter = TLGatherAllAvs('CogHQExterior', RotationLimitToH)
        self.accept('doorDoneEvent', self.handleDoorDoneEvent)
        self.accept('DistributedDoor_doorTrigger', self.handleDoorTrigger)
        NametagGlobals.setMasterArrowsOn(1)
        self.tunnelOriginList = base.cr.hoodMgr.addLinkTunnelHooks(self, self.nodeList, self.zoneId)
        how = requestStatus['how']
        self.fsm.request(how, [requestStatus])

        # Load the CogHQ DNA file:
        dnaStore = DNAStorage()
        dnaFileName = self.genDNAFileName(self.zoneId)
        loadDNAFileAI(dnaStore, dnaFileName)

        # Collect all of the vis group zone IDs:
        self.zoneVisDict = {}
        for i in xrange(dnaStore.getNumDNAVisGroupsAI()):
            groupFullName = dnaStore.getDNAVisGroupName(i)
            visGroup = dnaStore.getDNAVisGroupAI(i)
            visZoneId = int(base.cr.hoodMgr.extractGroupName(groupFullName))
            visZoneId = ZoneUtil.getTrueZoneId(visZoneId, self.zoneId)
            visibles = []
            for i in xrange(visGroup.getNumVisibles()):
                visibles.append(int(visGroup.getVisibleName(i)))
            visibles.append(ZoneUtil.getBranchZone(visZoneId))
            self.zoneVisDict[visZoneId] = visibles

        # Next, we want interest in all vis groups due to this being a Cog HQ:
        base.cr.sendSetZoneMsg(self.zoneId, self.zoneVisDict.values()[0])
    def exit(self):
        self.fsm.requestFinalState()
        self._telemLimiter.destroy()
        del self._telemLimiter
        self.loader.music.stop()
        for node in self.tunnelOriginList:
            node.removeNode()

        del self.tunnelOriginList
        if self.loader.geom:
            self.loader.geom.reparentTo(hidden)
        self.ignoreAll()
        BattlePlace.BattlePlace.exit(self)

    def enterPurchase(self):
        base.localAvatar.b_setAnimState('neutral', 1)
        self.accept('teleportQuery', self.handleTeleportQuery)
        base.localAvatar.setTeleportAvailable(1)
        base.localAvatar.laffMeter.start()
        base.localAvatar.obscureMoveFurnitureButton(1)

    def exitPurchase(self):
        base.localAvatar.setTeleportAvailable(0)
        self.ignore('teleportQuery')
        base.localAvatar.laffMeter.stop()
        base.localAvatar.obscureMoveFurnitureButton(0)

    def enterTunnelOut(self, requestStatus):
        fromZoneId = self.zoneId - self.zoneId % 100
        tunnelName = base.cr.hoodMgr.makeLinkTunnelName(self.loader.hood.id, fromZoneId)
        requestStatus['tunnelName'] = tunnelName
        BattlePlace.BattlePlace.enterTunnelOut(self, requestStatus)

    def enterTeleportIn(self, requestStatus):
        x, y, z, h, p, r = base.cr.hoodMgr.getPlaygroundCenterFromId(self.loader.hood.id)
        base.localAvatar.setPosHpr(render, x, y, z, h, p, r)
        BattlePlace.BattlePlace.enterTeleportIn(self, requestStatus)

    def enterTeleportOut(self, requestStatus, callback = None):
        if 'battle' in requestStatus:
            self.__teleportOutDone(requestStatus)
        else:
            BattlePlace.BattlePlace.enterTeleportOut(self, requestStatus, self.__teleportOutDone)

    def __teleportOutDone(self, requestStatus):
        hoodId = requestStatus['hoodId']
        zoneId = requestStatus['zoneId']
        avId = requestStatus['avId']
        shardId = requestStatus['shardId']
        if hoodId == self.loader.hood.hoodId and zoneId == self.loader.hood.hoodId and shardId == None:
            self.fsm.request('teleportIn', [requestStatus])
        elif hoodId == ToontownGlobals.MyEstate:
            self.getEstateZoneAndGoHome(requestStatus)
        else:
            self.doneStatus = requestStatus
            messenger.send(self.doneEvent)
        return

    def exitTeleportOut(self):
        BattlePlace.BattlePlace.exitTeleportOut(self)

    def enterSquished(self):
        base.localAvatar.laffMeter.start()
        base.localAvatar.b_setAnimState('Squish')
        taskMgr.doMethodLater(2.0, self.handleSquishDone, base.localAvatar.uniqueName('finishSquishTask'))

    def handleSquishDone(self, extraArgs = []):
        base.cr.playGame.getPlace().setState('walk')

    def exitSquished(self):
        taskMgr.remove(base.localAvatar.uniqueName('finishSquishTask'))
        base.localAvatar.laffMeter.stop()
