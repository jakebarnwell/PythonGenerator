import clr
clr.AddReference('FSharp.Core')
clr.AddReference('System.Core')
clr.AddReferenceToFileAndPath('C:\\experimentos\\fsharp\\AbcExplorationLib\\AbcExplorationLib\\bin\\Debug\\abcexplorationlib.dll')
clr.AddReferenceToFileAndPath('C:\\experimentos\\fsharp\\AbcExplorationLib\\SwfSupport\\bin\\Debug\\SwfSupport1.dll')
clr.AddReferenceToFileAndPath('C:\\development\\libs\\ManagedZLib.1.1.1\\bin\\dotNet.1.1\\ManagedZLib.dll')

from Langexplr.Abc import *
from Langexplr.SwfSupport import *
from System.IO import *
from ManagedZLib import Decompress
from Microsoft.FSharp.Core import FuncConvert 
from System import Func
from Microsoft.FSharp.Core import Option

#f = FileStream("testclass.abc",FileMode.Open)
#avf = AvmAbcFile.Create(f)
#f.Close()

stream = FileStream("c:\\temp\\Test.swf",FileMode.Open)

swffile = SwfFile.ReadFrom(stream,FuncConvert.ToFastFunc[Stream,BinaryReader](lambda s:Decompress(s)))

print swffile

from System.Diagnostics import Debugger

#Debugger.Break()

for tag in [abcTag for abcTag in \
             swffile.Tags if isinstance(abcTag,DoAbcTag) and abcTag.Name == 'frame2']:
   print tag
   dataStream = MemoryStream(tag.Data)
   abcFile = AvmAbcFile.Create(dataStream)
   print abcFile
   for c in abcFile.Classes:
      print c.Name.ToString()
      for m in c.Methods:
        print "    " + m.Name.ToString()+" " + (m.Method.Body <> None).ToString() 
        if (Option[AvmMethodBody].get_IsSome(m.Method.Body)):
           for i in m.Method.Body.Value.Instructions:
              print "            " + i.Name

stream.Close()



