var EnterMode = function(theMode)
{
   switch(theMode)
   {
      case "options":
         onKeyDown = function()
         {
            var _loc3_ = Key.getCode();
            switch(_loc3_)
            {
               case 20:
                  if(_root.testingMode == true)
                  {
                     trace("capslock");
                     this.theMainPanel.PortraitFadeOut();
                  }
                  break;
               case 77:
                  this.theMainPanel.ShowPortrait(true);
                  break;
               case 16:
                  this.theMainPanel.ShowPortrait(false);
                  break;
               case 87:
               case 38:
               case 83:
               case 40:
                  break;
               case 65:
               case 37:
                  goLeft();
                  break;
               case 68:
               case 39:
                  goRight();
                  break;
               case 45:
                  trace("fscommand(\"OnPressY\", 0);");
                  fscommand("OnPressY",0);
                  break;
               case 42:
                  trace("fscommand(\"OnPressX\", 0);");
                  fscommand("OnPressX",0);
                  break;
               case 13:
               case 90:
                  trace("fscommand(\"OnAccept\", " + theSelectedOption + ");");
                  fscommand("OnAccept",theSelectedOption);
                  break;
               case 8:
               case 81:
                  if(_root.demoMode == false)
                  {
                     trace("fscommand(\"OnCancel\", 0);");
                     fscommand("OnCancel",0);
                     AnimateExit();
                  }
                  break;
               default:
                  trace("Unknown Keypress " + _loc3_);
            }
         };
         Key.addListener(this);
         break;
      case "default":
      default:
         Key.removeListener(this);
   }
};
var ExitMode = function(theMode)
{
   switch(theMode)
   {
      case "stack":
         this.unitStack.ExitPanel();
         break;
      case "options":
      case "default":
   }
   Key.removeListener(this);
};
onLoad = function()
{
   var _loc2_ = "options";
   this.EnterMode("options");
};
