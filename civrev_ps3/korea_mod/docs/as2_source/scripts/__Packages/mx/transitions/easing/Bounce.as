class mx.transitions.easing.Bounce
{
   static var version = "1.1.0.52";
   function Bounce()
   {
   }
   static function easeOut(t, b, c, d)
   {
      if((t /= d) < 0.36363636363636365)
      {
         return c * (7.5625 * t * t) + b;
      }
      if(t < 0.7272727272727273)
      {
         return c * (7.5625 * (t -= 0.5454545454545454) * t + 0.75) + b;
      }
      if(t < 0.9090909090909091)
      {
         return c * (7.5625 * (t -= 0.8181818181818182) * t + 0.9375) + b;
      }
      return c * (7.5625 * (t -= 0.9545454545454546) * t + 0.984375) + b;
   }
   static function easeIn(t, b, c, d)
   {
      return c - mx.transitions.easing.Bounce.easeOut(d - t,0,c,d) + b;
   }
   static function easeInOut(t, b, c, d)
   {
      if(t < d / 2)
      {
         return mx.transitions.easing.Bounce.easeIn(t * 2,0,c,d) * 0.5 + b;
      }
      return mx.transitions.easing.Bounce.easeOut(t * 2 - d,0,c,d) * 0.5 + c * 0.5 + b;
   }
}
