var myBitmapData;
var myPortrait = "";
var container;
var targetX = 0;
var targetY = 0;
var myMCL = new MovieClipLoader();
myMCL.onLoadInit = function(targetMC)
{
   trace("Movie clip:" + targetMC + " is now initialized");
   SetImageSize(targetMC);
};
var SetImageSize = function(targetMC)
{
   trace("************** SIZING!");
   theEdgeBuffer = 1.5;
   targetSize = 270;
   trace("targetMC._width " + targetMC._width);
   targetMC._x = targetX - 539;
   targetMC._y = targetY - 98.5;
};
myMCL.onLoadError = function(targetMC, errorCode)
{
   trace("ERRORCODE:" + errorCode);
   trace(targetMC + "Failed to load its content");
};
var portImageLargeSUB;
var SetPortrait = function(nationName, largeSize)
{
   trace("SetPortrait: " + nationName);
   myPortrait = nationName;
   if(nationName != "blank")
   {
      theImage = GetImageName(nationName);
      if(largeSize != undefined)
      {
         theImage = largeSize + theImage;
      }
      trace("theImage: " + theImage);
      diffX = -539 + targetX;
      diffY = -98.5 + targetY;
      trace("x,y " + diffX + ", " + diffY);
      this.createEmptyMovieClip("portImageLarge",5,{_x:targetX,_y:targetY});
      myMCL.loadClip("LDR_" + theImage + ".dds",portImageLarge);
      portImageLarge._alpha = 100;
   }
};
var ClearBitmaps = function()
{
   portImageLarge._alpha = 0;
};
var GetImageName = function(theString)
{
   var _loc1_ = undefined;
   theName = theString.toLowerCase();
   switch(theName)
   {
      case "0":
      case "rome":
      case "roman":
      case "ceasar":
         _loc1_ = "rome";
         targetX = 504;
         targetY = 51;
         break;
      case "1":
      case "egypt":
      case "egyptian":
      case "egyptc":
      case "cleopatra":
         _loc1_ = "egypt";
         targetX = 504;
         targetY = 67;
         break;
      case "2":
      case "greek":
      case "greece":
      case "alexander":
         _loc1_ = "greece";
         targetX = 449;
         targetY = 47;
         break;
      case "3":
      case "spain":
      case "spanish":
      case "isabella":
         _loc1_ = "spain";
         targetX = 506;
         targetY = 19;
         break;
      case "4":
      case "german":
      case "germany":
      case "bismarck":
         _loc1_ = "germany";
         targetX = 412;
         targetY = 39;
         break;
      case "5":
      case "russia":
      case "russian":
      case "catherine":
         _loc1_ = "russia";
         targetX = 539;
         targetY = 59;
         break;
      case "6":
      case "china":
      case "chinese":
      case "mao":
         _loc1_ = "china";
         targetX = 506;
         targetY = 63;
         break;
      case "7":
      case "american":
      case "america":
      case "lincoln":
         _loc1_ = "america";
         targetX = 489;
         targetY = 55;
         break;
      case "8":
      case "japanese":
      case "japan":
      case "tokugawa":
         _loc1_ = "japan";
         targetX = 481;
         targetY = 7;
         break;
      case "9":
      case "french":
      case "france":
      case "napoleon":
         _loc1_ = "france";
         targetX = 510;
         targetY = 103;
         break;
      case "10":
      case "indian":
      case "india":
      case "gandhi":
         _loc1_ = "india";
         targetX = 553;
         targetY = 87;
         break;
      case "11":
      case "arab":
      case "arabian":
      case "saladin":
         _loc1_ = "arabia";
         targetX = 484;
         targetY = 0;
         break;
      case "12":
      case "aztec":
      case "montezuma":
         _loc1_ = "aztecs";
         targetX = 483;
         targetY = 2;
         break;
      case "13":
      case "african":
      case "africa":
      case "shakazulu":
         _loc1_ = "africa";
         targetX = 469;
         targetY = 0;
         break;
      case "14":
      case "mongolian":
      case "mongolia":
      case "genghiskahn":
         _loc1_ = "mongol";
         targetX = 466;
         targetY = 0;
         break;
      case "15":
      case "english":
      case "england":
      case "elizabeth":
         _loc1_ = "england";
         targetX = 380;
         targetY = 3;
         break;
      case "16":
      case "barbarian":
         _loc1_ = "barbarian";
         break;
      case "-1":
      case "17":
      default:
         _loc1_ = "default";
         targetX = 449;
         targetY = 47;
   }
   return _loc1_;
};
var myPortrait = "";
var portNum = 0;
var SetPortraitInfo = function(theString)
{
   trace("+++++++++++++++++SetPortrait: " + theString);
   trace("showPortrait: " + showPortrait);
   if(showPortrait == true)
   {
      portraitImage._alpha = 100;
      if(myPortrait == "")
      {
         myPortrait = theString;
      }
      if(theString == "reset")
      {
         theString = myPortrait;
      }
      SetPortrait(theString,"Lrg_");
   }
   if(theString == -1)
   {
      this.theTextClip.theCivSymbol._alpha = 0;
      this.theTextClip.theCivSymbol2._alpha = 0;
   }
   else
   {
      this.theTextClip.theCivSymbol._alpha = 100;
      this.theTextClip.theCivSymbol.SetIcon(theString);
      this.theTextClip.theCivSymbol2._alpha = 100;
      this.theTextClip.theCivSymbol2.SetIcon(theString);
   }
};
