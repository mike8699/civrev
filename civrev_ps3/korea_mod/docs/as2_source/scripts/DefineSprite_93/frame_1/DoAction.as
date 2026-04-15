startW = 68.7;
startH = 142.2;
endW = 200;
endH = 250;
startX = this._x;
endX = startX - 0.5 * (endW - startW) - 20;
startY = this._y;
endY = startY - 25;
isExpanded = false;
var SetHighlight = function(theBoolean)
{
   if(theBoolean == 1)
   {
      this.highlightClip.Show();
   }
   else
   {
      this.highlightClip.Hide();
   }
};
var SetTeamColor = function(theColor)
{
   targetBar = this.teamColorBar;
   if(theColor == "transparent")
   {
      targetBar._alpha = 0;
   }
   else
   {
      targetBar._alpha = 100;
      this["colorful" + theColor] = new Color(targetBar);
      this["colorful" + theColor].setRGB(theColor);
      trace("Setting the color: " + targetBar + " : " + theColor + " : this[\"colorful\" + theColor]\": " + this["colorful" + theColor]);
   }
};
var SetPeace = function(theBoolean, theString)
{
   if(theBoolean == 1)
   {
      symbolPeace._alpha = 100;
      symbolPeace.SetText(theString);
   }
   else
   {
      symbolPeace._alpha = 0;
      symbolPeace.SetText("");
   }
};
var SetWar = function(theBoolean, theString)
{
   if(theBoolean == 1)
   {
      symbolWar._alpha = 100;
      symbolWar.SetText(theString);
   }
   else
   {
      symbolWar._alpha = 0;
      symbolWar.SetText("");
   }
};
var SetHelpText = function(helpText1, helpText2)
{
   this.helpPanel1.SetText(helpText1);
   this.helpPanel2.SetText(helpText2);
   ShowHelp();
};
var HideHelp = function()
{
   myFadeIn1.stop();
   myFadeIn2.stop();
   this.helpPanel1._alpha = 0;
   this.helpPanel2._alpha = 0;
};
var ShowHelp = function()
{
   target_mc = this.helpPanel1;
   myFadeIn1 = new mx.transitions.Tween(target_mc,"_alpha",mx.transitions.easing.Strong.easeIn,0,100,0.2,true);
   target_mc = this.helpPanel2;
   myFadeIn2 = new mx.transitions.Tween(target_mc,"_alpha",mx.transitions.easing.Strong.easeIn,0,100,0.2,true);
};
var ExpandPortrait = function()
{
   target_mc = this;
   target_mc.swapDepths(this.getNextHighestDepth());
   myWidthStretch = new mx.transitions.Tween(target_mc,"_width",mx.transitions.easing.Strong.easeIn,this._width,endW,0.2,true);
   myHeightStretch = new mx.transitions.Tween(target_mc,"_height",mx.transitions.easing.Strong.easeIn,this._height,endH,0.2,true);
   mySlideToCenter = new mx.transitions.Tween(target_mc,"_x",mx.transitions.easing.Strong.easeIn,this._x,endX,0.2,true);
   myScootDown = new mx.transitions.Tween(target_mc,"_y",mx.transitions.easing.Strong.easeIn,this._y,endY,0.2,true);
   isExpanded = true;
   portraitImage._alpha = 0;
   myScootDown.onMotionFinished = function()
   {
      _parent.UpdateIconPlacement();
   };
};
var ShrinkPortrait = function()
{
   target_mc = this;
   target_mc.swapDepths(this.getNextHighestDepth());
   myWidthStretch = new mx.transitions.Tween(target_mc,"_width",mx.transitions.easing.Strong.easeIn,this._width,startW,0.2,true);
   myHeightStretch = new mx.transitions.Tween(target_mc,"_height",mx.transitions.easing.Strong.easeIn,this._height,startH,0.2,true);
   mySlideToCenter = new mx.transitions.Tween(target_mc,"_x",mx.transitions.easing.Strong.easeIn,this._x,startX,0.2,true);
   myScootDown = new mx.transitions.Tween(target_mc,"_y",mx.transitions.easing.Strong.easeIn,this._y,startY,0.2,true);
   isExpanded = false;
   myScootDown.onMotionFinished = function()
   {
      _parent.UpdateIconPlacement();
      portraitImage._alpha = 100;
   };
};
