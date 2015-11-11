from DistributedNPCToonBaseAI import DistributedNPCToonBaseAI
from ToonDNA import ToonDNA
from toontown.toonbase import ToontownGlobals

class DistributedNPCGloveAI(DistributedNPCToonBaseAI):

    def requestTransformation(self, color):
        avId = self.air.getAvatarIdFromSender()
        av = self.air.doId2do.get(avId)

        if av is None or not hasattr(av, 'dna'):
            return

        if av.dna.gloveColor == color:
            self.sendUpdate('doTransformation', [avId, 1])
            return
            
	    if av.dna.headColor == color and av.dna.legColor == color and av.dna.armColor == color:
		    self.sendUpdate('doTransformatiion', [avId, 3])
		    
        if av.getTotalMoney() < ToontownGlobals.GloveCost:
            self.sendUpdate('doTransformation', [avId, 2])
            return
	   
        if av.getTotalMoney() < ToontownGlobals.ColorCost:
            self.sendUpdate('doTransformation', [avId, 4])
            return
		
        av.takeMoney(ToontownGlobals.GloveCost)
        newDNA = ToonDNA()
        newDNA.makeFromNetString(av.getDNAString())
        newDNA.gloveColor = color
        newDNA.headColor = color
        newDNA.legColor = color
        newDNA.armColor = color
        taskMgr.doMethodLater(1.0, lambda task: av.b_setDNAString(newDNA.makeNetString()), 'transform-%d' % avId)
        self.sendUpdate('doTransformation', [avId, 3])
