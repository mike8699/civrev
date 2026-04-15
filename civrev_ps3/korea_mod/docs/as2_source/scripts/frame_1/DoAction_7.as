var goLeft = function()
{
   theSelectedOption -= 1;
   if(theSelectedOption < 0)
   {
      theSelectedOption = 0;
   }
   else
   {
      theOptionArray[theSelectedOption + 1].ScootRight();
      theOptionArray[theSelectedOption].ShowHighlight();
      UpdatePrimaryDisplay();
      theMainPanel.AnimatePortraitFromLeft();
      theOptionArray[theSelectedOption].swapDepths(options_mov.getNextHighestDepth());
      theOptionArray[theSelectedOption + 1].HideHighlight();
      if(theOptionArray[theSelectedOption]._visible == false)
      {
         newTarget = options_mov._y + options_mov["optionText_" + theSelectedOption].bgH_s;
         scrollTween = new mx.transitions.Tween(options_mov,"_y",mx.transitions.easing.Regular.easeOut,options_mov._y,newTarget,0.3,true);
         theOptionArray[theSelectedOption]._visible = true;
         theOptionArray[theSelectedOption + numOptionsToShow]._visible = false;
         if(theSelectedOption == 0)
         {
            arrow_mov.gotoAndStop("4");
         }
         else
         {
            arrow_mov.gotoAndStop("2");
         }
      }
   }
   SlideTheBoxContainer();
   UpdateArrows();
   trace("fscommand(\"OnOption\", " + theSelectedOption + ");");
   fscommand("OnOption",theSelectedOption);
};
var goRight = function()
{
   theSelectedOption += 1;
   if(theSelectedOption > numOptions - 1)
   {
      theSelectedOption = numOptions - 1;
   }
   else
   {
      theOptionArray[theSelectedOption].swapDepths(options_mov.getNextHighestDepth());
      theOptionArray[theSelectedOption].ShowHighlight();
      UpdatePrimaryDisplay();
      theMainPanel.AnimatePortraitFromRight();
      theOptionArray[theSelectedOption - 1].ScootLeft();
      theOptionArray[theSelectedOption - 1].HideHighlight();
      if(theOptionArray[theSelectedOption]._visible == false)
      {
         newTarget = options_mov._y - options_mov["optionText_" + theSelectedOption].bgH_s;
         scrollTween = new mx.transitions.Tween(options_mov,"_y",mx.transitions.easing.Regular.easeOut,options_mov._y,newTarget,0.3,true);
         trace("should show: " + theOptionArray[theSelectedOption]);
         theOptionArray[theSelectedOption]._visible = true;
         theOptionArray[theSelectedOption - numOptionsToShow]._visible = false;
         arrow_mov.gotoAndStop("2");
      }
   }
   if(numOptions > numOptionsToShow and theSelectedOption == numOptions - 1)
   {
      arrow_mov.gotoAndStop("3");
   }
   SlideTheBoxContainer();
   UpdateArrows();
   trace("fscommand(\"OnOption\", " + theSelectedOption + ");");
   fscommand("OnOption",theSelectedOption);
};
var SelectText = function(theTextField)
{
   theTextField.textColor = 16777215;
};
var DeselectText = function(theTextField)
{
   theTextField.textColor = 7905013;
};
