var ShowLock = function()
{
   this.thePanel.theLock._alpha = 100;
};
var HideLock = function()
{
   this.thePanel.theLock._alpha = 0;
};
var SetText = function(theField, theString)
{
   this.thePanel["textField" + theField].text = theString;
};
var SetColor = function(theColor)
{
   myColor = theColor;
   if(theColor != 16711935)
   {
      targetBar = this.thePanel.diploDisplay.teamColorBar;
      targetBar._alpha = 100;
      var _loc3_ = new Color(targetBar);
      _loc3_.setRGB(theColor);
   }
};
var SetAutoSaveText = function(theString)
{
   trace("*********SetAutoSaveText " + theString);
   this.thePanel.autoSaveMC.textField0.text = theString;
};
var ShowAutoSave = function()
{
   this.thePanel.autoSaveMC._alpha = 100;
};
var HideAutoSave = function()
{
   this.thePanel.autoSaveMC._alpha = 0;
};
