var myMCL = new MovieClipLoader();
var myIcon = "";
myMCL.onLoadInit = function(targetMC)
{
   targetMC.SetIcon(myIcon);
   targetMC.SetTeamColor(0,16711935);
   targetMC._x = theIconDim._x;
   targetMC._y = theIconDim._y;
   targetMC._width = theIconDim._width;
   targetMC._height = theIconDim._height;
};
myMCL.onLoadError = function(targetMC, errorCode)
{
   trace("ERRORCODE:" + errorCode);
   trace(targetMC + "Failed to load its content");
};
var SetIcon = function(theString)
{
   myIcon = theString;
   myMCL.loadClip("GFX_CivIcon.swf","iconTarget");
};
