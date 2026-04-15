var myMCL = new MovieClipLoader();
var checkLoaded = function()
{
   targetMC.myPos = numLoaded;
   if(_root.testingMode == 1)
   {
      numLoaded--;
      if(numLoaded < 0)
      {
         _parent.ContinueBuilding();
      }
   }
   else
   {
      numLoaded++;
      if(numLoaded == _parent.numOptions)
      {
         _parent.ContinueBuilding();
      }
   }
};
myMCL.onLoadError = function(targetMC, errorCode)
{
   trace("ERRORCODE:" + errorCode);
   trace(targetMC + "Failed to load its content");
};
