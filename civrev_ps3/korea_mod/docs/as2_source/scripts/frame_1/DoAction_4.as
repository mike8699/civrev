_global.gfxExtensions = true;
theSelectedOption = 0;
numOptions = 6;
theOptionArray = [];
theBuffer = 20;
theAutoSaveText = "";
var SetTitle = function(theString)
{
   this.theTopBar.Title_txt.text = theString;
};
var StartBuilding = function()
{
   trace("StartBuilding");
   this.options_mov.LoadOptions();
};
var ContinueBuilding = function()
{
   trace("starting ContinueBuilding()...");
   trace("theColorArray: " + theColorArray);
   if(theInitialSelection == -1)
   {
      theInitialSelection = Math.floor(Math.random() * (numOptions - 1));
   }
   if(_root.demoMode == true)
   {
   }
   trace("theInitialSelection: " + theInitialSelection);
   fscommand("theInitialSelection",theInitialSelection);
   i = 0;
   while(i < numOptions)
   {
      var _loc3_ = Object(["option_" + i]);
      theOptionArray.push(options_mov[_loc3_]);
      theOptionArray[i].ScootRight();
      i++;
   }
   SetUpUnits();
   this.theMainPortrait.SetAutoSaveText(theAutoSaveText);
   i = 0;
   while(i < theInitialSelection)
   {
      theOptionArray[i].ScootLeft();
      i++;
   }
   theSelectedOption = theInitialSelection;
   theOptionArray[theSelectedOption].ShowHighlight();
   UpdatePrimaryDisplay();
   theOptionArray[theSelectedOption].ScootCenter();
   options_mov._x = CalculateTargetXLoc(theInitialSelection);
   UpdateArrows();
   AnimateEnter();
   if(_root.testingMode == true)
   {
      i = 0;
      while(i < 17)
      {
         CalculateTargetXLoc(i);
         i++;
      }
   }
};
var SetUpUnits = function()
{
   trace("***SetUpUnits()***");
   j = 0;
   while(j < numOptions)
   {
      myDataArray = this["slotData" + j];
      var _loc2_ = theOptionArray[j];
      _loc2_._x = j * (_loc2_._width + theBuffer);
      _loc2_.SetPortrait(myDataArray[0]);
      _loc2_.SetColor(theColorArray[j]);
      _loc2_.SetText(0,myDataArray[1] + "\n" + myDataArray[2]);
      if(theActiveArray[j] == "0")
      {
         _loc2_.ShowLock();
      }
      j++;
   }
};
var HideObject = function(theMovieClip)
{
   this[theMovieClip]._visible = false;
   this[theMovieClip].enabled = false;
};
var ShowObject = function(theMovieClip)
{
   this[theMovieClip]._visible = true;
   this[theMovieClip].enabled = true;
};
var UpdatePrimaryDisplay = function()
{
   trace("UpdatePrimaryDisplay()");
   myDataArray = this["slotData" + theSelectedOption];
   var _loc2_ = theMainPanel;
   if(_loc2_.showPortrait == true)
   {
      portEntranceTween = new mx.transitions.Tween(_loc2_.portraitImage,"_alpha",mx.transitions.easing.Strong.easeOut,0,100,0.5,true);
   }
   _loc2_.SetPortraitInfo(myDataArray[0]);
   _loc2_.SetColor(theColorArray[theSelectedOption]);
   _loc2_.SetText(0,myDataArray[1] + "\n" + myDataArray[2]);
   _loc2_.SetText(1,myDataArray[3]);
   _loc2_.SetText(2,myDataArray[4]);
   _loc2_.SetText(3,myDataArray[5]);
   _loc2_.SetText(4,myDataArray[6]);
   _loc2_.SetText(5,myDataArray[7]);
   _loc2_.SetText(6,myDataArray[8]);
   _loc2_.ShowHighlight();
   SetCoins(myDataArray[9],myDataArray[10],myDataArray[11],myDataArray[12],myDataArray[13],myDataArray[14],myDataArray[15],myDataArray[16]);
   if(theActiveArray[theSelectedOption] == "0")
   {
      _loc2_.ShowLock();
   }
   else
   {
      _loc2_.HideLock();
   }
};
var s0;
var s1;
var s2;
var s3;
var SetCoins = function(icon0, state0, icon1, state1, icon2, state2, icon3, state3)
{
   s0 = state0;
   s1 = state1;
   s2 = state2;
   s3 = state3;
   i0 = icon0;
   i1 = icon1;
   i2 = icon2;
   i3 = icon3;
   i = 0;
   while(i < 4)
   {
      this.theMainPanel["coin" + i].gotoAndPlay("icon" + this["i" + i] + "_" + this["s" + i]);
      i++;
   }
};
var UpdateArrows = function()
{
   trace("UpdateArrows");
   this.theMainPanel.arrowLeft._alpha = 100;
   this.theMainPanel.arrowRight._alpha = 100;
   if(theSelectedOption == 0)
   {
      this.theMainPanel.arrowLeft._alpha = 0;
   }
   else if(theSelectedOption == numOptions - 1)
   {
      this.theMainPanel.arrowRight._alpha = 0;
   }
};
