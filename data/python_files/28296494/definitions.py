import clr
clr.AddReference('System.Drawing')
clr.AddReferenceToFile('CommonRules.dll')

import System
from System.Drawing import Color
from System.Text.RegularExpressions import Regex
from stej.Tools.UdpLogViewer.Core import ProcessingResult as PR
from stej.Tools.UdpLogViewer.CommonRules import LogItemProcessor as LIP

clr.AddReferenceToFile('Growl.Connector.dll')
clr.AddReferenceToFile('Growl.CoreLibrary.dll')
import Growl.Connector
class ToGrowl(LIP):
	def __new__(cls, regex, connector, condition=None, regexOnLogger=False):
		inst = LIP.__new__(cls, regex, None, None, regexOnLogger)
		inst.connector = connector
		inst.condition = condition
		inst.Name      = "To Growl"
		inst.DetailsInfo = "%s - %s" % (inst.Name, regex)
		return inst
	def Process(self, logItem, parameters):
		if self.Matches(logItem) and (self.condition == None or self.condition(logItem, parameters)):
			notification = Growl.Connector.Notification('UdpLogViewer', 'lv', System.DateTime.Now.Ticks.ToString(), 'Log item arrived', logItem.Message)
			notification.Priority = Growl.Connector.Priority.Emergency
			connector.Notify(notification)
		ret = PR.ContinueWithProcessing()
		ret.RuleIsMatching = True
		return ret
	def ToString(self):
		return "%s %s" % (ToGrowl,self.Regex)
		
class ToFile(LIP):
	def __new__(cls, regex):
		inst = LIP.__new__(cls, regex, None, None, False)
		inst.Name = "To file"
		inst.DetailsInfo = "%s - %s" % (inst.Name, regex)
		return inst
	def Process(self, logItem, parameters):
		if self.Matches(logItem):
			from System.IO import File
			f = File.AppendText('out.log')
			f.WriteLine(logItem.Message)
			f.Close()
		ret = PR.ContinueWithProcessing()
		ret.RuleIsMatching = True
		return ret
	def ToString(self):
		return "%s %s" % (ToFile, self.Regex)