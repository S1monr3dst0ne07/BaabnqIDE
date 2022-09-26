
"""
Acc - Accumolator
Reg - Register
mem - Memory

16-Bit Maschine

set attr - set attr into Reg

add none - Acc = Acc + Reg
sub none - Acc = Acc - Reg
shg none - Acc = Acc shifted greater
shs none - Acc = Acc shifted smaller

lor none - Acc = Acc (logical or) Reg
and none - Acc = Acc (logical and) Reg
xor none - Acc = Acc (logical xor) Reg
not none - Acc = Acc (logical not)

lDA attr - Load mem at attr into Acc
lDR attr - Load mem at attr into Reg
sAD attr - Save Acc into mem at attr
sRD attr - Save Reg into mem at attr

lPA atrr - Load mem pointed to by mem at attr into Acc
lPR atrr - Load mem pointed to by mem at attr into Reg
sAP atrr - Save Acc into mem pointed to by mem at attr
sRP atrr - Save Reg into mem pointed to by mem at attr

out attr - outputs mem at attr
inp attr - inputs  mem at attr

lab attr - define lable
got attr - goto attr
jm0 attr - goto attr if Acc = 0
jmA attr - goto attr if Acc = Reg

jmG attr - goto attr if Acc > Reg (jmG for jump great)
jmL attr - goto atrr if Acc < Reg (jmL for jump less)

jmS attr - goto attr as subroutine (pc gets push to stack)
ret none - return from subroutine (stack gets pop to pc)

pha none - push Acc to stack
pla none - pull from stack to Acc


brk none - stops programm
clr none - clears Reg and Acc

putstr none - print the Acc as ascii


ahm none - allocate a number of word given by the Reg and put a pointer to the base into the Acc
fhm none - free a number of word given by the Reg at the address given by the Acc


plugin attr - runs plugin with name of attr



-------
This version supports external debugging
There are two modes: 'Running' and 'Breakpoint'
by default the vm is running in 'Running' mode, this can be switch by the breakpoint assember command: asm 'breakpoint 0'
In 'Breakpoint' mode the vm awaits commands from stdin:
    Continue     - switch mode back to running
    Next         - step to and execute next instruction
    



"""

import time
import glob
import argparse
import sys, os
import traceback

class cInt:
    def __init__(self, xInt = 0, xIntLimit = 65535):
        self.xInt = xInt
        self.xIntLimit = xIntLimit
        
        
    def Set(self, xNew):
        self.xInt = int(xNew) % self.xIntLimit
        
    def Add(self, xValue):
        self.Set(self.xInt + int(xValue))
        
        
    def Sub(self, xValue):
        self.Set(self.xInt - int(xValue))

    def __int__(self):
        return self.xInt
    
    
class cLine:
    def __init__(self, xInst = "", xAttr = None):
        self.xInst = xInst
        self.xAttr = xAttr
        
    def __str__(self):
        return "{: <10}{}".format(str(self.xInst), str(self.xAttr))
 
class cPluginEnv:
    pass
 
class cMain:
    def __init__(self, xFile, xDebug):
        self.xFile = xFile
        self.xMode = 0
        self.xDebug = xDebug
        
        self.xBitSize = 16
        self.xIntLimit = 2 ** self.xBitSize 
        
        self.xReg = cInt(0, self.xIntLimit)
        self.xAcc = cInt(0, self.xIntLimit)
        
        #just to avoid confusion:
        #the heap is part of the memory and in this case it's the top half
        self.xHeapStartAddress = self.xIntLimit // 2        
        self.xHeapSize = self.xIntLimit - self.xHeapStartAddress
        
        #memory addresses allocated on the heap
        self.xHeapAlloc = [] 
        
        self.xMem = [cInt(0, self.xIntLimit) for i in range(self.xIntLimit)]
        
        self.xStack = []
                
        self.xProgramIndex = 0
        self.xLables = {}
        
        self.xTotalIndex = 0

        #assign a pointer to the memory and stack to the plugin env
        #this works because when you copy a list in python, it will just copy a pointer to that list, which can also be modified
        self.xPluginEnv = cPluginEnv()
        self.xPluginEnv.xDebug = self.xDebug
        self.xPluginEnv.xMem   = self.xMem
        self.xPluginEnv.xStack = self.xStack
                
                                                
        self.xDelayPerExecCycleInMs = 0
        

    
    def Structuring(self, xRawSource):
        #this function will take in the raw source and make it into a structure
        xLineStructureBuffer = []
        xLineIndex = 0
        xLineOffset = 0
        for xLineIterator in [x.strip().replace("  ", " ").split(" ") for x in xRawSource.split("\n") if x.replace(" ", "") != "" and x.strip()[0] != '"']:            
            xInst = xLineIterator[0]
            xAttr = xLineIterator[1] if len(xLineIterator) > 1 else None
            
            if xInst == "lab":
                if not xAttr is None:
                    self.xLables[xAttr] = str(xLineIndex - xLineOffset)
                    xLineOffset += 1
                
                else:
                    print("Attribute Error: " + " ".join(xLineIterator))
                    sys.exit(0)
                
            else:
                xLineStructureBuffer.append(cLine(xInst = xInst, xAttr = xAttr))
        
            xLineIndex += 1
        
        return xLineStructureBuffer
    
    
    #applies protocol when debugging is enabled
    def AplyProt(self, xRaw, xPrefix):
        if self.xDebug:
            return xPrefix + "(" + xRaw.replace("\n", "") + ")"
        
        else:
            return xRaw

    def ProcessBackspace(self, xRaw):
        while "\b" in xRaw:
            xIndex = xRaw.index("\b")
            xRaw = xRaw[:xIndex - 1] + xRaw[xIndex + 1:]
    
        return xRaw
    
    def UpdateHeapUsage(self):
        xUsage = f"{len(self.xHeapAlloc)}:{self.xHeapSize}".format()
        print(self.AplyProt(xUsage, "HeapUsage"))
        
    def Interpret(self):
        xLastVars = {}
        
        self.xLineStructures = self.Structuring(self.xFile)
        
        if self.xDebug:
            self.UpdateHeapUsage()
            
            #check for varmapper
            try:
                xFirstLine = self.xFile.split("\n")[0]
                xVarMapper = eval(xFirstLine[1:])
                
            except Exception as E:
                xVarMapper = {}

        try:
            while self.xProgramIndex < len(self.xLineStructures):
                xTimeAtCycleStart = time.time()        
                xLine = self.xLineStructures[self.xProgramIndex]                
                xInst = xLine.xInst
                xAttr = xLine.xAttr

                if self.xDebug:

                                        
                    #mode 1 is 'breakpoint'
                    if self.xMode == 1:
                        try:
                            while True:
                                xRaw = input()
                                xRawSplit = xRaw.split(" ")
                                xDebugOption = xRawSplit[0]
                                xDebugArgs   = xRawSplit[1:]
                                
                                if xDebugOption == "Next":          break
                                elif xDebugOption == "Continue":    
                                    self.xMode = 0
                                    print(self.AplyProt(str(self.xMode), "Mode"))
                                    break

                        except Exception: pass
                
                    xVars = {xVarName : int(self.xMem[xVarAddress]) for xVarName, xVarAddress in xVarMapper.items()}
                    if xLastVars == {}: xLastVars = {xKey : xVars[xKey] - 1 for xKey in xVars.keys()}
                    xVarsDiff = {xKey : xVars[xKey] for xKey in xVars.keys() if xVars[xKey] != xLastVars[xKey]} #get the variables that changed to make sending more efficent
                    xLastVars = xVars
                    
                    if xVarsDiff != {}: print(self.AplyProt(str(xVarsDiff), "Var"))
                    
                    
                #execute inst
                if xInst == "set":
                    self.xReg.Set(int(xAttr))
                    
                elif xInst == "add":
                    self.xAcc.Add(self.xReg)
                
                elif xInst == "sub":
                    self.xAcc.Sub(self.xReg)
                
                elif xInst == "shg":
                    self.xAcc.Set(int(self.xAcc) * 2)
                    
                elif xInst == "shs":
                    self.xAcc.Set(int(self.xAcc) // 2)
                
                elif xInst == "lor":
                    self.xAcc.Set(int(self.xAcc) | int(self.xReg))
    
                elif xInst == "and":
                    self.xAcc.Set(int(self.xAcc) & int(self.xReg))
    
                elif xInst == "xor":
                    self.xAcc.Set(int(self.xAcc) ^ int(self.xReg))
    
                elif xInst == "not":
                    xAccBin = bin(int(self.xAcc))[2:]
                    xFixLenAccBin = "0" * (self.xBitSize - len(xAccBin)) + xAccBin
                    
                    
                    xInverted = []
                    for xI in xFixLenAccBin:
                        if xI == "0":
                            xInverted.append("1")
                        
                        elif xI == "1":
                            xInverted.append("0")

                    self.xAcc.Set(int("".join(xInverted), 2))
    
                    
            
                elif xInst == "lDA":
                    self.xAcc.Set(int(self.xMem[int(xAttr)]))
                
                elif xInst == "lDR":
                    self.xReg.Set(int(self.xMem[int(xAttr)]))
                
                elif xInst == "sAD":
                    self.xMem[int(xAttr)].Set(self.xAcc)
                
                elif xInst == "sRD":
                    self.xMem[int(xAttr)].Set(self.xReg)
     
                elif xInst == "lPA":
                    self.xAcc.Set(int(self.xMem[int(self.xMem[int(xAttr)])]))
                
                elif xInst == "lPR":
                    self.xReg.Set(int(self.xMem[int(self.xMem[int(xAttr)])]))
    
                elif xInst == "sAP":
                    self.xMem[int(self.xMem[int(xAttr)])].Set(int(self.xAcc))
                
                elif xInst == "sRP":
                    self.xMem[int(self.xMem[int(xAttr)])].Set(int(self.xReg))
    
                
                elif xInst == "out":
                    xIntRaw = int(self.xMem[int(xAttr)])
                    print(self.AplyProt(str(xIntRaw), "Print") + "\n", end = "")
                
                elif xInst == "inp":
                    print(self.AplyProt(">>>", "Print"))
                    xInputRaw = input()
                    xInput = self.ProcessBackspace(xInputRaw)
                                        
                    self.xMem[int(xAttr)].Set(0 if xInput == "" else int(xInput))
                
                elif xInst == "got":
                    self.xProgramIndex = int(self.xLables[str(xAttr)])
                    continue
                
                elif xInst == "jm0":
                    if int(self.xAcc) == 0:
                        self.xProgramIndex = int(self.xLables[str(xAttr)])
                        continue
                    
                    
                elif xInst == "jmA":
                    if int(self.xAcc) == int(self.xReg):
                        self.xProgramIndex = int(self.xLables[str(xAttr)])
                        continue
                  
                elif xInst == "jmG":
                    if int(self.xAcc) > int(self.xReg):
                        self.xProgramIndex = int(self.xLables[str(xAttr)])
                        continue
                
                elif xInst == "jmL":
                    if int(self.xAcc) < int(self.xReg):
                        self.xProgramIndex = int(self.xLables[str(xAttr)])
                        continue
    
                        
                elif xInst == "brk":
                    break
                    
                elif xInst == "clr":
                    self.xReg.Set(0)
                    self.xAcc.Set(0)
                
                elif xInst == "jmS":
                    xReturnAddr = (self.xProgramIndex + 1) * 2
                    self.xStack.append(xReturnAddr)
                    self.xProgramIndex = int(self.xLables[str(xAttr)])

                    if self.xDebug: print(self.AplyProt(f"push:{str(xReturnAddr)} <{str(xInst)} {str(xAttr)}>".format(), "Stack"))
                    continue
                    
                    
                elif xInst == "ret":
                    if len(self.xStack) != 0:
                        self.xProgramIndex = int(self.xStack.pop() / 2)
                        if self.xDebug: print(self.AplyProt("pull:0", "Stack"))
                        continue

                    else:
                        print(self.AplyProt("Error: Stack underflow\n", "Print"))
                        
                elif xInst == "pha":
                    xPushValue = int(self.xAcc)
                    self.xStack.append(xPushValue)

                    if self.xDebug: print(self.AplyProt(f'push:{str(xPushValue)}'.format(), "Stack"))
                    
                elif xInst == "pla":
                    if len(self.xStack) != 0:
                        xPullValue = int(self.xStack.pop())
                        self.xAcc.Set(xPullValue)
                        if self.xDebug: print(self.AplyProt("pull:0", "Stack"))
                        
                    else:
                        print(self.AplyProt("Error: Stack underflow\n", "Print"))
                
                elif xInst == "putstr":
                    xAscii = int(self.xAcc)
                    xChr = chr(xAscii)
                    
                    if self.xDebug:     print(self.AplyProt(str(xAscii), "Chr") + "\n", end = "")
                    else:               print(xChr, end = "", flush = True)
                    
                    
                    
                elif xInst == "ahm":                    
                    xAllocSize = int(self.xReg)
                    
                    #find the correct number of word in a row that are free
                    xBasePointer = None
                    for xHeapIndex in range(self.xHeapStartAddress, self.xHeapStartAddress + self.xHeapSize):
                        #terminate the loop if the xHeapIndex plus the size that the memory row need to by is greater than the heap itself
                        #because any check would be out of range and thus useless anyway
                        if xHeapIndex + xAllocSize > self.xHeapStartAddress + self.xHeapSize:
                            break

                        #otherwise check for a matching row
                        if all([xHeapIndex + xCheckIndex not in self.xHeapAlloc for xCheckIndex in range(xAllocSize)]):
                            xBasePointer = xHeapIndex
                            break
                    
                    if xBasePointer is None:
                        print("Program out of heap memory")
                        sys.exit(0)
                        
                    else:
                        for xAddrIndex in range(xBasePointer, xBasePointer + xAllocSize):
                            #append all the memory addresses to the alloc list, in order for them to properly freed 
                            self.xHeapAlloc.append(xAddrIndex)
                            
                            #and reset the address, just for safety
                            self.xMem[xAddrIndex].Set(0)
                        
                        #override the Acc to return the memory address to the user
                        self.xAcc.Set(xBasePointer)

                    if self.xDebug: 
                        self.UpdateHeapUsage()

                        
                elif xInst == "fhm":                    
                    xFreeSize = int(self.xReg)
                    xFreeBase = int(self.xAcc)
                    
                    for xFreeAddrIndex in range(xFreeBase, xFreeBase + xFreeSize):
                        if xFreeAddrIndex in self.xHeapAlloc: 
                            self.xHeapAlloc.remove(xFreeAddrIndex)
                        
                        self.xMem[xFreeAddrIndex].Set(0)

                    if self.xDebug: 
                        self.UpdateHeapUsage()

                
                elif xInst == "plugin":
                    try:
                        xPluginName = xAttr.split("::")[0]
                        xMethodName = xAttr.split("::")[1]
                        
                        if self.xDebug: print(self.AplyProt(xAttr, "Plugin"))
                        
                        exec(str(xPluginName) + "." + str(xMethodName) + '(self.xPluginEnv)')

                    except Exception as E:
                        print(self.AplyProt(f"Plugin Error: {str(traceback.format_exc())}\n".format(), "Print"))
                
                elif xInst == "breakpoint":
                    if self.xDebug:
                        self.xMode = 1
                        print(self.AplyProt(str(self.xMode), "Mode"))
                
                    
                else:
                    print(self.AplyProt(f"Invaild command: {str(xInst)}\n".format(), "Print"))
                    sys.exit(0)
                
                self.xProgramIndex += 1
                self.xTotalIndex += 1
                
                #delay till quota is reached
                while (time.time() - xTimeAtCycleStart) * 1000 < self.xDelayPerExecCycleInMs:
                    time.sleep(1 / 1000)
                
                
                sys.stdout.flush()


        except KeyboardInterrupt:
            pass

        except KeyError:
            print(self.AplyProt(f"Error: label not found '{str(cM.xLineStructures[cM.xProgramIndex])}'\n".format(), "Print"), flush = True)
        #print("Program took " + str(self.xTotalIndex) + " Cycles to complete")

                        
        
if __name__ == '__main__':
    xArgParser = argparse.ArgumentParser(description = "S1monsAssembly4 Virtual Machine v2 (with external debugging)")    

    xArgParser.add_argument("--file", type=str, dest="path", action="store", nargs=1, required=True, help = "Assembler file to run")
    xArgParser.add_argument("--PluginPath", type=str, dest="PluginPath", action="store", nargs=1,    help = "Path to plugin files")
    xArgParser.add_argument("--debug", action="store_true", default=False, dest="debug",             help = "DON'T USE THIS")
    xArgs = xArgParser.parse_args()
    

    try:
        xPath = xArgs.path[0]
        xFile = open(xPath, "r").read()
        
    except Exception as E:
        print("Error while loading file")
        sys.exit(0)


    if xArgs.PluginPath:
        try:            
            xPluginPath = xArgs.PluginPath[0]
            xPluginPaths = glob.glob(xPluginPath + "\\*.py")
            
            for xPathIter in xPluginPaths:
                xFileHandleIter = open(xPathIter)
                xFileHandle     = xFileHandleIter.read()
                xFileHandleIter.close()
                
                xPluginName = xPathIter.split("\\")[-1].split(".")[0]
                
                
                exec(xFileHandle, globals(), locals())
    
                
        except Exception as E:
            print("Error while loading Plugins:", "Print")
            print(E)
    
    
    
    cM = cMain(xFile = xFile, xDebug = xArgs.debug)
    cM.Interpret()
