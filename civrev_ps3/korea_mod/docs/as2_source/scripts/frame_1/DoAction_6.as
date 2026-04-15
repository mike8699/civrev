function PlayScroll(theMovieClip, isForward, isVertical, theDuration, theEaseType)
{
   theDuration = 15;
   if(isVertical)
   {
      var _loc4_ = theMovieClip._y;
   }
   else
   {
      _loc4_ = theMovieClip._x;
   }
   if(isForward == 1)
   {
      if(isVertical)
      {
         var _loc5_ = theMovieClip._y + theMovieClip._height;
      }
      else
      {
         _loc5_ = theMovieClip._x + theMovieClip._width;
      }
   }
   if(isForward == 0)
   {
      if(isVertical)
      {
         _loc5_ = theMovieClip._y - theMovieClip._height;
      }
      else
      {
         _loc5_ = theMovieClip._x - theMovieClip._width;
      }
   }
   var _loc3_ = theDuration;
   switch(theEaseType)
   {
      case 0:
         var _loc6_ = mx.transitions.easing.None.easeOut;
         break;
      case 1:
         _loc6_ = mx.transitions.easing.Regular.easeOut;
         break;
      case 2:
         _loc6_ = mx.transitions.easing.Bounce.easeOut;
         break;
      case 3:
         _loc6_ = mx.transitions.easing.Strong.easeOut;
         break;
      case 4:
         _loc6_ = mx.transitions.easing.Back.easeOut;
         break;
      case 5:
         _loc6_ = mx.transitions.easing.Elastic.easeOut;
   }
   if(isVertical)
   {
      scrollTween = new mx.transitions.Tween(theMovieClip,"_y",_loc6_,_loc4_,_loc5_,_loc3_);
   }
   else
   {
      scrollTween = new mx.transitions.Tween(theMovieClip,"_x",_loc6_,_loc4_,_loc5_,_loc3_);
   }
   scrollTween.onMotionFinished = function()
   {
      _global.isScrolling = false;
      resetOptionsHeight();
   };
}
