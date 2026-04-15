var numLoaded = 0;
var bgH_s = 484.5;
var bgH_l = 593;
var bgW_s = 124.4;
var bgW_l = 312;
var diffH = bgH_l - bgH_s;
var targetY = 55;
var originY = 102;
var duration = 1;
var portS_H = 143.3;
var portS_W = 103.8;
var portL_H = 315;
var portL_W = 250;
var portTargetY = 60;
var portOriginY = 101.8;
var portOriginX = 9.9;
var rightX = 145;
var centerX = 0;
var leftX = -145;
var portHorizBuffer = 60;
var CheckLoaded = function()
{
   numLoaded++;
   if(numLoaded > 4)
   {
      switch(_root.increaseSpeed)
      {
         case 1:
            duration = 0.3;
            break;
         case 2:
            duration = 0.6;
            break;
         default:
            duration = 1;
      }
      trace("load broadcaster");
   }
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
      this.thePanel.bg.gotoAndPlay("highlighted");
      theIcon._alpha = 100;
   }
   else
   {
      this.thePanel.bg.gotoAndPlay("regular");
      theIcon._alpha = 0;
   }
};
var AnimateGrow = function()
{
   target = this.thePanel.bg;
   animateGrowW = new mx.transitions.Tween(target,"_width",mx.transitions.easing.Strong.easeOut,target._width,bgW_l,duration,true);
   animateGrowX = new mx.transitions.Tween(target,"_x",mx.transitions.easing.Strong.easeOut,target._x,- 0.5 * (bgW_l - bgW_s),duration,true);
   animateGrowH = new mx.transitions.Tween(target,"_height",mx.transitions.easing.Strong.easeOut,target._height,bgH_l,duration,true);
   animateGrowY = new mx.transitions.Tween(target,"_y",mx.transitions.easing.Strong.easeOut,target._y,portTargetY,duration,true);
   target = this.thePanel.diploDisplay;
   SetPortrait("-1");
   animateGrowW_port = new mx.transitions.Tween(target,"_width",mx.transitions.easing.Strong.easeOut,target._width,portL_W,duration,true);
   animateGrowX_port = new mx.transitions.Tween(target,"_x",mx.transitions.easing.Strong.easeOut,target._x,- 0.5 * (portL_W - portS_W) + portHorizBuffer,duration,true);
   animateGrowH_port = new mx.transitions.Tween(target,"_height",mx.transitions.easing.Strong.easeOut,target._height,portL_H,duration,true);
   animateGrowY_port = new mx.transitions.Tween(target,"_y",mx.transitions.easing.Strong.easeOut,target._y,portTargetY,duration,true);
};
var AnimateShrink = function()
{
   target = this.thePanel.bg;
   animateShrinkW = new mx.transitions.Tween(target,"_width",mx.transitions.easing.Strong.easeOut,target._width,bgW_s,duration,true);
   animateShrinkX = new mx.transitions.Tween(target,"_x",mx.transitions.easing.Strong.easeOut,target._x,0,duration,true);
   animateGrowH = new mx.transitions.Tween(target,"_height",mx.transitions.easing.Strong.easeOut,target._height,bgH_s,duration,true);
   animateGrowY = new mx.transitions.Tween(target,"_y",mx.transitions.easing.Strong.easeOut,target._y,originY,duration,true);
   target = this.thePanel.diploDisplay;
   SetPortrait("reset");
   animateGrowW_port = new mx.transitions.Tween(target,"_width",mx.transitions.easing.Strong.easeOut,target._width,portS_W,duration,true);
   animateGrowX_port = new mx.transitions.Tween(target,"_x",mx.transitions.easing.Strong.easeOut,target._x,portOriginX,duration,true);
   animateGrowH_port = new mx.transitions.Tween(target,"_height",mx.transitions.easing.Strong.easeOut,target._height,portS_H,duration,true);
   animateGrowY_port = new mx.transitions.Tween(target,"_y",mx.transitions.easing.Strong.easeOut,target._y,portOriginY,duration,true);
};
var ScootUp = function()
{
   target = this.thePanel;
   animateScootUp = new mx.transitions.Tween(target,"_y",mx.transitions.easing.Strong.easeOut,target._y,originY - diffH,duration,true);
};
var ScootDown = function()
{
   target = this.thePanel;
   animateScootDown = new mx.transitions.Tween(target,"_y",mx.transitions.easing.Strong.easeOut,target._y,originY,duration,true);
};
var isBlank = function()
{
   if(unitStack.unit0.myPortrait == "blank" || unitStack.unit0.myPortrait == "")
   {
      return true;
   }
   return false;
};
var ScootRight = function()
{
   target = this.thePanel;
   animateSlideX = new mx.transitions.Tween(target,"_x",mx.transitions.easing.Strong.easeOut,target._x,rightX,duration,true);
};
var ScootCenter = function()
{
   target = this.thePanel;
   animateSlideX = new mx.transitions.Tween(target,"_x",mx.transitions.easing.Strong.easeOut,target._x,centerX,duration,true);
};
var ScootLeft = function()
{
   target = this.thePanel;
   animateSlideX = new mx.transitions.Tween(target,"_x",mx.transitions.easing.Strong.easeOut,target._x,leftX,duration,true);
};
