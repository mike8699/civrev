var showPortrait = true;
var ShowLock = function()
{
   this.theLock._alpha = 100;
};
var HideLock = function()
{
   this.theLock._alpha = 0;
};
var ShowHighlight = function()
{
   HighlightBG(1);
   ScootCenter();
   theButton._alpha = 100;
};
var HideHighlight = function()
{
   HighlightBG(0);
   theButton._alpha = 0;
};
var HighlightBG = function(theState)
{
   if(theState == 1)
   {
      this.bg.gotoAndPlay("highlighted");
      theIcon._alpha = 100;
   }
   else
   {
      this.bg.gotoAndPlay("regular");
      theIcon._alpha = 0;
   }
};
var SetText = function(theField, theString)
{
   this.theTextClip["textField" + theField].text = theString;
   this.theTextClip["textField" + theField + "S"].text = theString;
};
var SetColor = function(theColor)
{
   myColor = parseInt(theColor);
   if(theColor != 16711935)
   {
      targetBar = this.theTextClip.teamColorBar;
      targetBar1 = this.theTextClip.theCivSymbol;
      targetBar2 = this.theTextClip.theCivSymbol2;
      targetBar._alpha = 100;
      var _loc3_ = new Color(targetBar);
      _loc3_.setRGB(theColor);
   }
   else
   {
      trace("This should not be displaying the team color bar!");
      targetBar._alpha = 0;
   }
};
var AnimatePortraitFromRight = function()
{
   if(showPortrait == true)
   {
      duration = 0.5;
      target = this.theTextClip;
   }
};
var AnimatePortraitFromLeft = function()
{
   if(showPortrait == true)
   {
      duration = 0.5;
      target = this.theTextClip;
      optSlideTween = new mx.transitions.Tween(target,"_alpha",mx.transitions.easing.Strong.easeOut,0,100,duration,true);
   }
};
var PortraitFadeOut = function()
{
   _parent.portEntranceTween.fforward();
   optSlideTween.fforward();
   trace("fading out main portrait");
   duration = 0.5;
   ClearBitmaps();
};
var PortraitFadeIn = function()
{
   _parent.portEntranceTween.fforward();
   optSlideTween.fforward();
   trace("fading in main portrait");
   duration = 0.5;
   target = this.portImageLarge;
   fadeOutPortTween = new mx.transitions.Tween(target,"_alpha",mx.transitions.easing.Strong.easeOut,0,100,duration,true);
};
var ShowPortrait = function(theBool)
{
   showPortrait = theBool;
   if(showPortrait == false)
   {
      PortraitFadeOut();
      portraitImage._alpha = 0;
   }
   else
   {
      trace("turn on");
      portraitImage._alpha = 100;
      _parent.UpdatePrimaryDisplay();
   }
};
