var myPortrait = "";
var SetPortrait = function(theString)
{
   if(myPortrait == "")
   {
      myPortrait = theString;
   }
   if(theString == "reset")
   {
      theString = myPortrait;
   }
   if(theString == -1)
   {
      this.thePanel.diploDisplay._alpha = 0;
   }
   else
   {
      SetPortraitImage(theString);
      this.thePanel.theCivSymbol.SetIcon(theString);
   }
};
var myMCL = new MovieClipLoader();
myMCL.onLoadInit = function(targetMC)
{
   SetImageSize(targetMC);
};
var SetImageSize = function(targetMC)
{
   theEdgeBuffer = 1.5;
   targetSize = 80;
   targetMC._height = targetSize;
   targetMC._width = targetSize;
   targetMC._x = this.thePanel.diploDisplay.bg._x - 0.4 * targetSize;
   targetMC._y = this.thePanel.diploDisplay.bg._y - 0.5 * targetSize;
   trace(this.thePanel.diploDisplay.bg._x);
};
myMCL.onLoadError = function(targetMC, errorCode)
{
   trace("ERRORCODE:" + errorCode);
   trace(targetMC + "Failed to load its content");
};
var SetPortraitImage = function(nationName, largeSize)
{
   theImage = GetImageName(nationName);
   trace("theImage: " + theImage);
   if(_root.testingMode == true)
   {
      myMCL.loadClip("../ObjectIcons/LDR_" + theImage + ".dds",this.thePanel.diploDisplay.portraitImage);
   }
   else
   {
      myMCL.loadClip("LDR_" + theImage + ".dds",this.thePanel.diploDisplay.portraitImage);
   }
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
         break;
      case "1":
      case "egypt":
      case "egyptian":
      case "egyptc":
      case "cleopatra":
         _loc1_ = "egypt";
         break;
      case "2":
      case "greek":
      case "greece":
      case "alexander":
         _loc1_ = "greece";
         break;
      case "3":
      case "spain":
      case "spanish":
      case "isabella":
         _loc1_ = "spain";
         break;
      case "4":
      case "german":
      case "germany":
      case "bismarck":
         _loc1_ = "germany";
         break;
      case "5":
      case "russia":
      case "russian":
      case "catherine":
         _loc1_ = "russia";
         break;
      case "6":
      case "china":
      case "chinese":
      case "mao":
         _loc1_ = "china";
         break;
      case "7":
      case "american":
      case "america":
      case "lincoln":
         _loc1_ = "america";
         break;
      case "8":
      case "japanese":
      case "japan":
      case "tokugawa":
         _loc1_ = "japan";
         break;
      case "9":
      case "french":
      case "france":
      case "napoleon":
         _loc1_ = "france";
         break;
      case "10":
      case "indian":
      case "india":
      case "gandhi":
         _loc1_ = "india";
         break;
      case "11":
      case "arab":
      case "arabian":
      case "saladin":
         _loc1_ = "arabia";
         break;
      case "12":
      case "aztec":
      case "aztecs":
      case "montezuma":
         _loc1_ = "aztecs";
         break;
      case "13":
      case "african":
      case "africa":
      case "shakazulu":
         _loc1_ = "africa";
         break;
      case "14":
      case "mongolian":
      case "mongolia":
      case "genghiskahn":
         _loc1_ = "mongol";
         break;
      case "15":
      case "english":
      case "england":
      case "elizabeth":
         _loc1_ = "england";
         break;
      case "16":
      case "barbarian":
         _loc1_ = "barbarian";
         break;
      case "-1":
      case "17":
      default:
         _loc1_ = "default";
   }
   return _loc1_;
};
