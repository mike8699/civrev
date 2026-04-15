var LoadOptions = function()
{
   if(_root.testingMode == 1)
   {
      numLoaded = _parent.numOptions - 1;
   }
   else
   {
      numLoaded = 0;
   }
   if(_parent.numOptions > 0)
   {
      i = 0;
      while(i < _parent.numOptions)
      {
         this.attachMovie("ChooseCivLeader",this["option_" + i],this.getNextHighestDepth(),{_name:["option_" + i],_x:parseInt(xloc),_y:parseInt(yloc)});
         i++;
      }
   }
   else
   {
      trace("PROBLEM LOADING: numOptions = " + numOptions);
   }
};
