_root.testingMode = false;
var theInitialSelection = -1;
_root.demoMode = false;
_root.theActiveArray = new Array();
i = 0;
while(i <= 17)
{
   i++;
}
var thisIsATest = function()
{
   _root.testingMode = true;
   _root.demoMode = true;
   this.EnterMode("options");
   theInitialSelection = 0;
   theActiveArray[2] = "0";
   theActiveArray[4] = "0";
   numOptions = 17;
   SetTitle("CHOOSE YOUR CIV");
   theTopBar.buttonHelpL.SetText("Return");
   theTopBar.buttonHelpL.SetIcon("PS3X");
   theTopBar.buttonHelpR.SetText("Accept");
   theTopBar.buttonHelpR.SetIcon("A");
   theColorArray = new Array(12931043,16777011,8569580,15644211,13270027,6083151,16777011,8569580,16777071,13270027,12931043,16777011,8569580,16777071,13270027,13270027,16711935);
   slotData0 = new Array("14","Caesar","Romans","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Romans begin the game with knowledge of the Republic.","Legion","19","dim","20","gold","17","regular","18","regular");
   slotData1 = new Array("1","Cleoptra","Egyptians","1/2 Price Buildings","1/2 Price Rush","More Famous People","New Cities have 3 Population","The Egyptians begin the game with knowledge of the Great Pyramids.","Rifleman\nArtillery","19","dim","blank","blank","blank","blank","18","regular");
   slotData2 = new Array("2","Alexander","Greece","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The French begin the game with knowledge of the Republic.","Catapult");
   slotData3 = new Array("3","Isabella","Spanish","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Egyptians begin the game with knowledge of the Great Pyramids.","Legion\nArcher");
   slotData4 = new Array("4","Catherine","Russian","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Romans begin the game with knowledge of the Republic.","Legion");
   slotData5 = new Array("5","Caesar","Romans","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Romans begin the game with knowledge of the Republic.","Legion");
   slotData6 = new Array("6","Mao","China","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Romans begin the game with knowledge of the Republic.","Legion");
   slotData7 = new Array("7","Napolean","France","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Romans begin the game with knowledge of the Republic.","Legion");
   slotData8 = new Array("8","Tokagawa","Japan","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Romans begin the game with knowledge of the Republic.","Legion");
   slotData9 = new Array("9","Napolean","France","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Romans begin the game with knowledge of the Republic.","Legion");
   slotData10 = new Array("10","Caesar","Romans","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Romans begin the game with knowledge of the Republic.","Legion");
   slotData11 = new Array("11","Cleoptra","Egyptians","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Romans begin the game with knowledge of the Republic.","Legion");
   slotData12 = new Array("12","Napolean","France","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Romans begin the game with knowledge of the Republic.","Legion");
   slotData13 = new Array("13","Tokagawa","Japan","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Romans begin the game with knowledge of the Republic.","Legion");
   slotData14 = new Array("14","Mao","China","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Romans begin the game with knowledge of the Republic.","Legion");
   slotData15 = new Array("15","FINAL SAVE","Egyptians","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Romans begin the game with knowledge of the Republic.","Legion");
   slotData16 = new Array("17","RANDOM","Romans","1/2 Price Roads","1/2 Cost Wonders","More Famous People","New Cities have 3 Population","The Romans begin the game with knowledge of the Republic.","Legion");
   OnInitComplete();
};
