class mx.transitions.easing.Elastic
{
   static var version = "1.1.0.52";
   function Elastic()
   {
   }
   static function easeIn(t, b, c, d, a, p)
   {
      if(t == 0)
      {
         return b;
      }
      if((t /= d) == 1)
      {
         return b + c;
      }
      if(!p)
      {
         p = d * 0.3;
      }
      if(!a || a < Math.abs(c))
      {
         a = c;
         var _loc7_ = p / 4;
      }
      else
      {
         _loc7_ = p / 6.283185307179586 * Math.asin(c / a);
      }
      return - a * Math.pow(2,10 * (t -= 1)) * Math.sin((t * d - _loc7_) * 6.283185307179586 / p) + b;
   }
   static function easeOut(t, b, c, d, a, p)
   {
      if(t == 0)
      {
         return b;
      }
      if((t /= d) == 1)
      {
         return b + c;
      }
      if(!p)
      {
         p = d * 0.3;
      }
      if(!a || a < Math.abs(c))
      {
         a = c;
         var _loc7_ = p / 4;
      }
      else
      {
         _loc7_ = p / 6.283185307179586 * Math.asin(c / a);
      }
      return a * Math.pow(2,-10 * t) * Math.sin((t * d - _loc7_) * 6.283185307179586 / p) + c + b;
   }
   static function easeInOut(t, b, c, d, a, p)
   {
      if(t == 0)
      {
         return b;
      }
      if((t /= d / 2) == 2)
      {
         return b + c;
      }
      if(!p)
      {
         p = d * 0.44999999999999996;
      }
      if(!a || a < Math.abs(c))
      {
         a = c;
         var _loc7_ = p / 4;
      }
      else
      {
         _loc7_ = p / 6.283185307179586 * Math.asin(c / a);
      }
      if(t < 1)
      {
         return -0.5 * (a * Math.pow(2,10 * (t -= 1)) * Math.sin((t * d - _loc7_) * 6.283185307179586 / p)) + b;
      }
      return a * Math.pow(2,-10 * (t -= 1)) * Math.sin((t * d - _loc7_) * 6.283185307179586 / p) * 0.5 + c + b;
   }
}
