var SlideTheBoxContainer = function()
{
   optSlideTween.stop();
   target = this.options_mov;
   targetXLoc = CalculateTargetXLoc(theSelectedOption);
   target.targetXLoc = targetXLoc;
   duration = CalculateDuration(targetXLoc);
   optSlideTween = new mx.transitions.Tween(target,"_x",mx.transitions.easing.Strong.easeOut,target._x,targetXLoc,duration,true);
};
var CalculateTargetXLoc = function(theOption)
{
   theDifference = 0;
   theWidth = 130;
   targetLoc = -1 * (theWidth + theBuffer + theDifference) * (theOption - 2) + 278;
   return targetLoc;
};
var CalculateDuration = function()
{
   return Math.abs(options_mov._x - options_mov.targetXLoc) * 0.001 + 0.5;
};
var AnimateEnter = function()
{
   duration = 1;
   if(_root.demoMode == true)
   {
      target = this.bgParchment;
      slideInVert1 = new mx.transitions.Tween(target,"_y",mx.transitions.easing.Strong.easeOut,target._y + 720,target._y,duration,true);
      target._alpha = 100;
   }
   target = this.theMainPanel;
   slideInVert2 = new mx.transitions.Tween(target,"_x",mx.transitions.easing.Strong.easeOut,target._x + 800,target._x,duration,true);
   target._alpha = 100;
   target = this.theTopBar;
   slideInVert3 = new mx.transitions.Tween(target,"_y",mx.transitions.easing.Strong.easeOut,target._y - 300,target._y,duration,true);
   target._alpha = 100;
   target = this.options_mov;
   duration = 1.3;
   slideInVert4 = new mx.transitions.Tween(target,"_x",mx.transitions.easing.Strong.easeOut,target._x + target._width,target._x,duration,true);
   target._alpha = 100;
   slideInVert4.onMotionFinished = function()
   {
      trace("fscommand(\"AnimateEnterComplete\", \"GFX_SaveLoadScreen.swf\");");
      fscommand("AnimateEnterComplete","GFX_SaveLoadScreen.swf");
   };
};
var AnimateExit = function()
{
   duration = 0.5;
   if(_root.demoMode == true)
   {
      target = this.bgParchment;
      slideInVert1 = new mx.transitions.Tween(target,"_y",mx.transitions.easing.Strong.easeIn,target._y,target._y + 720,duration,true);
      target._alpha = 100;
   }
   target = this.theMainPanel;
   slideInVert2 = new mx.transitions.Tween(target,"_x",mx.transitions.easing.Strong.easeIn,target._x,target._x + 800,duration,true);
   target._alpha = 100;
   target = this.theTopBar;
   slideInVert3 = new mx.transitions.Tween(target,"_y",mx.transitions.easing.Strong.easeIn,target._y,target._y - 300,duration,true);
   target._alpha = 100;
   target = this.options_mov;
   slideInVert4 = new mx.transitions.Tween(target,"_x",mx.transitions.easing.Strong.easeIn,target._x,target._x + target._width,duration,true);
   target._alpha = 100;
   slideInVert4.onMotionFinished = function()
   {
      trace("fscommand(\"AnimateExitComplete\", \"GFX_SaveLoadScreen.swf\");");
      fscommand("AnimateExitComplete","GFX_SaveLoadScreen.swf");
   };
};
