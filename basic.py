import sys
import requests
import json
from fractions import Fraction
from operator import itemgetter
import math
import random
import traceback
from functools import reduce
from operator import getitem
from collections import defaultdict
from collections import defaultdict
import pprint
import tkinter as tk
import argparse
import re
import shlex
import copy
from itertools import takewhile

command_descriptions_dict = {
"do" : '''Run a custom attack this can be used for environmental factors or items that have yet to be added.
Other functions will wrap around this:
do --target climber --landFudge 1d20+4$ --check 10 --weaponFudge 1d8@bludgeoning 1d4@piercing --blockMult 0.5 --save
healing potion
do -t person --weaponFudge 2d4+2@heal
greatsword
do -s person -t enemy --landFudge 1d20+str+martial --check ac --weaponFudge 2d6+str@slashing
firebolt
do -s person -t enemy --landFudge 1d20+spellhit --check ac --weaponFudge 1d10@fire
fireball
do -s person -t enemies --landFudge 1d20+dex --check spelldc --weaponFudge 8d6@fire --save
''',

"use" : '''Do a generic action weapon or cast:
use --do greatsword --sender groovyBoy --target druid#3 --times 1 --advantage 1
''',

"action" : '''Do a generic action:
action --do Multiattack --sender sahuagin#2 --target druid#3 --times 1 --advantage 1
''',

"weapon" : '''Use a weapon:
weapon --do greatsword --sender sahuagin#2 --target druid#3 --times 3 --advantage -1
''',

"cast" : '''Cast a spell:
cast --sender druid#3 --target sahuagin#2 --times 2 --do fire-bolt --level 4 --advantage 0
''',

"remove" : '''Remove an item:
remove --target sahuagin#2
''',

"request" : '''Make a request:
request --path monsters sahuagin
''',

"set" : '''Set some aspect of the character or other item:
set --target sahuagin# --path initiative --change 18
''',

"mod" : '''Modify a stat on a creature:
mod --target sahuagin#2 --path initiative --change -5
''',

"list" : '''List the features of a creature:
list --target sahuagin#2 --path actions
''',

"add" : '''Add a creature:
add --target sahuagin --times 2 --identity Aqua-Soldier
''',

"init" : '''Roll for initiative:
initiative --target sahuagin#2
''',

"load" : '''Load a content by file name:
load --category monsters --file new_creature.json
load --category equipment --file new_weapon.json
load --category spells --file new_spell.json
''',

"turn" : '''Increments turn:
turn
''',

"put" : '''Put a full or partial command into either a global or creature:
put --target sahuagin --commandString "action --target party!random --sender sahuagin --do multiattack"
''',

"group" : '''Set a group for use in targetting. Will be resolved to listed targets:
group --member sahuagin sahuagin#2 --group sahuagang
''',

"info" : '''Shows all info for reference:
info --info groups
''',

"roll" : '''Roll dice:
roll --dice 1d20+2
''',

"store" : '''Store a command for use later:
store --commandString "add -t sahuagin -n 2" --path encounter#2 --append
''',

"shortrest" : '''Auto heal from short rest:
shortrest -t party 
''',

"longrest" : '''AutoHeal from long rest:
longrest -t party 
''',

"jump" : '''This persons turn: jump -t goblin#2
''',

"skip" : '''Do nothing:
skip
''',

"pause" : '''Forces a pause when the targets turn is there without removing his auto commands:
pause -t thinker
''',

"resume" : '''Set creature to run auto command when it is their turn:
resume -t menial-minded
''',

"enable" : '''Dont skip this persons turn:
enable -t no-longer-stunned-person
''',

"disable" : '''Skip this persons turn and try running the auto command for the next person:
disable -t not-yet-in-combat
''',

"addAuto" : '''Adds a creature and sets up a basic attack and target for it. In the case of monsters this is action #0:
addAuto --target giant-rat
addAuto --target npc-helper --do dagger --identity greg --method order --party
''',

"delete" : '''Delete a command or information entry such as a group:
delete -p commands loadParty 1
''',

"help" : '''Display this message:
help
''',

}


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def geti(list, index, default_value):
    try:
        return list[index]
    except:
        return default_value

def ddel(context,path):
    deep = pathing(path[:-1],context)
    if isinstance(deep, list):
        deep.pop(int(path[-1]))
    else:
        deep.pop(path[-1],None)

def dset(context, path, value):
    if not isinstance(path,list):
        path = [path]
    for key in path[:-1]:
        context = context.setdefault(key, {})
    context[path[-1]] = value

def dmod(context, path, value):
    if not isinstance(path,list):
        path = [path]
    for key in path[:-1]:
        context = context.setdefault(key, {})
    if dget(context,path[-1],None) == None:
        context[path[-1]] = int(value)
    else:
        context[path[-1]] = context[path[-1]] + int(value)

def dget(context, path, default=None):
    try:
        if not isinstance(path,list):
            path = [path]
        internal_dict_value = context
        for k in path:
            if isinstance(internal_dict_value,list):
                internal_dict_value = geti(context, int(k), default)
            else:
                internal_dict_value = internal_dict_value.get(k, default)
            if internal_dict_value is default:
                return default
        return internal_dict_value
    except:
        return default

def weedNones(dictionary):
    return {k:v for k,v in dictionary.items() if ((v is not None) and (v != [None])) and v != []}
                
def load(a):
    with open(a["file"]) as f:
            return json.load(f)

def callLoad(a):
    global cacheTable
    directory = ""
    if a.get("directory"):
        directory = a["directory"]
    for newFile in a["file"]:
        creatureJson = load({"file": directory+"/"+newFile})
        hasCategory = cacheTable.get(a["category"])
        if hasCategory:
            cacheTable[a["category"]][creatureJson["index"]] = creatureJson
        else:
            printw("Invalid category to load into")
 
cacheTable = load({"file":"data.json"})
battleTable = load({"file":"battle.json"})
battleInfo = load({"file":"battle_info.json"})
battleOrder = []
command_out = []
firstCommand = True

def getJsonFromApi(steps,save=True):
        api_base = "https://www.dnd5eapi.co/api/"
        for x in steps:
            api_base += x + "/"
        try:
            package = requests.get(api_base)
        except:
            printw("Api not reachable",api_base)
            return False
        response = package.json()
        if response.get("error"):
            #printw("Content not in api nor cache", steps)
            return False

        if save:
            with open('data.json') as f:
                global cacheTable
                dset(cacheTable,steps,response)
            
            with open('data.json', 'w') as f:
                json.dump(cacheTable,f)

        return response

def saveBattle():
        with open('battle.json', 'w') as f:
            json.dump(battleTable,f)       
        with open('battle_info.json', 'w') as f:
            json.dump(battleInfo,f)
        with open('data.json', 'w') as f:
            json.dump(cacheTable,f)

def printBattleKeys():
    printw(battleTable.keys())
                
def getJson(steps):
        global cacheTable
        cache = cacheTable
        
        for i,x in enumerate(steps):
                cache = dget(cache,x)
                if cache == None and i > 0:
                        #printw("Not cached, trying api")
                        return getJsonFromApi(steps)
        return cache.copy()

def getState():
        printw("index name type hp/max_hp")
        state_result = []
        for i, nick in enumerate(battleOrder):
            x = battleTable[nick]
            turn = ""
            if x.get("my_turn"):
                turn = "<-----------------| My Turn"
            temphp = 0
            if x.get("temp_hp"):
                temphp = x.get("temp_hp")
            string = printToString(i,nick,x["index"],str(int(x["current_hp"])+int(temphp))+"/"+str(x["max_hp"])+turn)
            printw(string)
            state_result.append(string)
        return state_result


def getCommandOut():
    global command_out
    global firstCommand
    if firstCommand:
        getState()
        firstCommand = False
    return command_out

def rollString(a):
    for dice in a["dice"]:
        roll(dice)

def crToProf(cr):
    crVal = float(sum(Fraction(s) for s in str(cr).split()))
    if cr < 5:
        return 2
    if cr <9:
        return 3
    if cr<13:
        return 4
    elif cr<17:
        return 5
    elif cr<21:
        return 6
    elif cr<25:
        return 7
    elif cr <29:
        return 8
    elif cr < 31:
        return 9
    else:
        printw("Hmm is a monster really this high level? Proficiency issue")
        return 10

def expandStatWord(stat):
    if stat == "wis":
        return "wisdom"
    elif stat == "str":
        return "strength"
    elif stat == "dex":
        return "dexterity"
    elif stat == "con":
        return "constitution"
    elif stat == "cha":
        return "charisma"
    elif stat == "int":
        return "intelligence"
    else:
        raise Exception("not a valid stat word", stat)

def getProf(combatant):
    proficiency = combatant.get("proficiency_bonus")
    if proficiency:
        return proficiency
    elif "challenge_rating" in combatant:
        cr = combatant.get("challenge_rating")
        newProficiency = crToProf(cr)
        combatant["proficiency_bonus"] = newProficiency
        return newProficiency
    else:
        raise Exception("This combatant has neither a proficiency_bonus nor a CR", combatant)

def canCast(combatantJson):
    for ability in combatantJson["special_abilities"]:
        spellcasting = ability.get("spellcasting")
        if spellcasting:
            return spellcasting
    return False

def applyDamage(targetJson,damage):
    heal = False
    if damage < 0:
        heal = True

    if targetJson.get("temp_hp") and (not heal):
        damage = damage - int(targetJson.get("temp_hp"))
    if damage > 0 or heal:
        if not heal:
            targetJson["temp_hp"] = 0
        targetJson["current_hp"] =  int(targetJson["current_hp"]) - math.floor(damage)
        targetJson["current_hp"] = max(targetJson["current_hp"],0)
    elif damage < 0:
        targetJson["temp_hp"] = -1*damage

def getAffinityMod(targetJson,damageType):
    immunities = targetJson.get("damage_immunities")
    vulnerabilities = targetJson.get("damage_vulnerabilities")
    resistances = targetJson.get("damage_resistances")

    if immunities:
        for affinity in immunities:
            if affinity == damageType:
                return 0
    if vulnerabilities:
        for affinity in vulnerabilities:
            if affinity == damageType:
                return 2 
    if resistances:
        for affinity in resistances:
            if affinity == damageType:
                return 0.5
    if damageType == "heal":
        return -1
    if damageType in ["temp","temp_hp","temphp"]:
        return "temphp"
    return 1

classSavesDict = {
"barbarian" : ["str","con"],
"bard" : ["dex","cha"],
"cleric" : ["wis","cha"],
"druid" : ["int","wis"],
"fighter" : ["str","con"],
"monk" : ["str","dex"],
"paladin" : ["wis","cha"],
"ranger" : ["str","dex"],
"rogue" : ["dex","int"],
"sorcerer" : ["con","cha"],
"warlock" : ["wis","cha"],
"wizard" : ["int","wis"],
}
        
def getMod(modType, attackJson, combatantJson, additional = 0):
        modSum = 0
        if modType == "actionHit" and attackJson.get("attack_bonus"):
            modSum += attackJson.get("attack_bonus")
        else:
            if modType == "hit" or modType == "dmg":
                finesse = False
                properties = attackJson.get("properties")
                if properties:
                    for x in properties:
                        if x["index"] == "finesse":
                            finesse = True
                if finesse:
                    modSum += max(statMod(int(combatantJson["strength"])),statMod(int(combatantJson["dexterity"])))
                else:
                    modSum += statMod(int(combatantJson["strength"]))

            if modType == "hit":
                if combatantJson.get("weapon_proficiencies"):
                    if attackJson["weapon_category"] in combatantJson["weapon_proficiencies"]:
                        modSum += getProf(combatantJson)

            if modType == "spellHit" or modType == "spellDc":
                modSum += getProf(combatantJson)

            if modType == "saveDc":
                saveType = attackJson["dc"]["dc_type"]["index"]
                modSum += statMod(combatantJson[expandStatWord(saveType)])
                saveProficiencies = geti(classSavesDict,combatantJson.get("class"),[])
                if saveType in saveProficiencies:
                    modSum += getProf(combatantJson)
            if modType == "spellHit" or modType == "spellDc":
                special_abilities = combatantJson.get("special_abilities")
                if special_abilities:
                    spellcasting = canCast(combatantJson)
                    if spellcasting:
                        if modType == "spellHit" or modType == "spellDc":
                            modSum += statMod(combatantJson[expandStatWord(spellcasting["ability"]["index"])])

                        if modType == "spellDc":
                            modSum += additional + 8 #In this case additional should be level of spell
                    else:
                        raise Exception("Attempted to have a non spellcaster cast a spell")
        return modSum

def statMod(stat):
        return math.floor((stat-10)/2)

def printUse(a):
    runAction = a["do"]
    if a["do"].isnumeric():
        sender = a["sender"]
        senderJson = battleTable[sender]
        actions = senderJson.get("actions")
        runAction = dget(actions,[int(a["do"]),"name"],False)
    printw("\n"+a["sender"].upper(), "uses", runAction, "on", a["target"])

def applyAction(a):
    actionKey = a["do"]
    sender = a["sender"]
    target = a["target"]
    landFudge = a.get("landFudge")
    weaponFudge = a.get("weaponFudge")
    advantageIn = int(a["advantage"])
    senderJson = battleTable[sender]
    targetJson = battleTable[target]
    actions = senderJson.get("actions")
    specialAbilities = senderJson.get("special_abilities")

    action = False
    action_result = ''
    if actions:
        for act in actions:
            if act["name"] == actionKey:
                action = act
    if specialAbilities:
        for special in specialAbilities:
            if special["name"] == actionKey:
                action = special
    if action:
        threshold = int(targetJson["armor_class"])

        advMod = 0 
        dc = action.get("dc")

        blockMult = 0
        mod = 0
        if dc:
            threshold = int(dc.get("dc_value"))
            if not threshold:
                printw("Has a dc for this action but no dc_value. Defaulting to 10")
                threshold = 10

            if dc.get("dc_success") == "half" or dc.get("success_type") == "half":
                blockMult = 0.5
            advMod = int(targetJson["save_advantage"])
            mod = getMod("saveDc", action, targetJson)
        else:
            mod = getMod("actionHit",action,senderJson)
            advMod = int(senderJson["advantage"])
            advMod += int(dget(targetJson,"incoming_advantage",0))
        advNum = advantageIn + advMod

        advantage = ""
        if advNum > 0:
           advantage = "advantage" 
        elif advNum < 0:
           advantage = "disadvantage" 
        if action.get("damage"):
            for damage in action["damage"]:         
                if damage.get("choose"):
                    for actions in range(int(damage["choose"])):
                        chosenAction = random.choice(damage["from"])
                        damageType = chosenAction["damage_type"]["index"]
                        hurtString = chosenAction["damage_dice"]+"@"+damageType

                        landString = "1d20+"+str(mod)

                        if advantage:
                            landString = landString + "!" + advantage

                        save = dc
                        if not landFudge:
                            landFudge = []
                        if not weaponFudge:
                            weaponFudge = []
                        a.update({"save" : save, "blockMult" : blockMult, "weaponFudge" : [hurtString]+weaponFudge, "landFudge" : [landString]+landFudge, "defense" : threshold, "multiCrit" : ["20"]})
                        callDo(a)

                else:   
                    damageType = damage["damage_type"]["index"]
                    hurtString = damage["damage_dice"] + "@" + damageType
                    landString = "1d20+"+str(mod)

                    if advantage:
                        landString = landString + "!" + advantage

                    save = dc
                    if not landFudge:
                        landFudge = []
                    if not weaponFudge:
                        weaponFudge = []
                    a.update({"save" : save, "blockMult" : blockMult, "weaponFudge" : [hurtString]+weaponFudge, "landFudge" : [landString]+landFudge, "defense" : threshold, "multiCrit" : ["20"]})
                    callDo(a)
    else:
        printw('Invalid action for this combatant')
        action_result = 'Invalid action for this combatant'

    action_result = '' # This will be returned at the end
    return action_result

def command_parse(input_command_string):
    if input_command_string == "vomit":
        printw ("ewwwww")
        
def applyInit(participant):
    who = participant["target"]
    combatant = geti(battleTable,who,False)
    if combatant:
        combatant["initiative"] = roll("1d20+" + str(statMod(combatant["dexterity"])))["roll"]
    else:
        printw("I'm sorry I couldn't find that combatant to apply init to.")

def setBattleOrder():
    initiativeOrder = sorted(battleTable.items(), key=lambda x: int(x[1]["initiative"]), reverse=True)
    tempOrder = []
    for keyPair in initiativeOrder:
        tempOrder.append(keyPair[0])
    global battleOrder
    battleOrder = tempOrder
    
def spellType(attackJson):
    if attackJson["damage"].get("damage_at_character_level"):
        return "damage_at_character_level"
    elif attackJson["damage"].get("damage_at_slot_level"):
        return "damage_at_slot_level"
    else:
        raise Exception("Oops this is not a spell")

def isCantrip(attackJson):
    if attackJson["damage"].get("damage_at_character_level"):
        return True
    elif attackJson["damage"].get("damage_at_slot_level"):
        return False
    else:
        raise Exception("Oops this is not a spell", attackJson)

def getStringMethodType(fudge):
    fudgeString = ""
    method = ""
    damage = ""
    
    if "!" in fudge:
        methodSplit = fudge.split("!")
        methodDirty = methodSplit[len(methodSplit)-1]
        method = "".join(takewhile(lambda x: (not x.isnumeric() and x != "@"), methodDirty))

    if "@" in fudge:
        damageSplit = fudge.split("@")
        damageDirty = damageSplit[len(damageSplit)-1]
        damage = "".join(takewhile(lambda x: (not x.isnumeric() and x != "!"),damageDirty))

    fudgeString = "".join(takewhile(lambda x: (not (x in ["@","!"] )),fudge))

    return [fudgeString,method,damage]

def getStringMethodTypeOrig(fudge):
    fudgeString = ""
    method = ""
    damage = ""

    valueMethod = fudge.split("!")
    methodTypeRaw = geti(valueMethod,1,False)
    if methodTypeRaw:
        fudgeString = valueMethod[0]
        methodType = methodTypeRaw.split("@")
        method = geti(methodType,0,False)
        damage = geti(methodType,1,"")
    else:
        valueDamage = valueMethod[0].split("@")
        fudgeString = valueDamage[0]
        method = False
        damage = geti(valueDamage,1,"")

    return [fudgeString,method,damage]

def callWeapon(a):
    attackPath = a["do"].lower()
    attackJson = getJson(["equipment",attackPath])
    landFudge = a.get("landFudge")
    weaponFudge = a.get("weaponFudge")
    if attackJson:
        #printUse(a)
        sender = a["sender"]
        target = a["target"]
        targetJson = battleTable[target]
        senderJson = battleTable[sender]
        mod = getMod("hit",attackJson,senderJson)
        threshold = int(targetJson["armor_class"])

        advMod = int(senderJson["advantage"])
        advMod += int(dget(targetJson,"incoming_advantage",0))
        advNum = int(a["advantage"]) + advMod

        advantage = ""
        if advNum > 0:
           advantage = "advantage" 
        elif advNum < 0:
           advantage = "disadvantage" 

        landString = "1d20+"+str(mod)

        if advantage:
            landString = landString + "!" + advantage

        damageType = attackJson["damage"]["damage_type"]["index"]
        hurtString = attackJson["damage"]["damage_dice"]+"+"+str(getMod("dmg",attackJson,senderJson)) + "@" + damageType
        blockMult = 0
        save = False
        if not landFudge:
            landFudge = []
        if not weaponFudge:
            weaponFudge = []
        a.update({"save" : save, "blockMult" : blockMult, "weaponFudge" : [hurtString]+weaponFudge, "landFudge" : [landString]+landFudge, "defense" : threshold, "multiCrit" : ["20"]})
        callDo(a)
    else:
        return False
    return True

def callCast(a):
    attackPath = a["do"].lower()
    attackJson = getJson(["spells",attackPath])
    landFudge = a.get("landFudge")
    weaponFudge = a.get("weaponFudge")
    if attackJson:
        sender = a["sender"]
        target = a["target"]
        level = a["level"]
        advantage = int(a["advantage"])
        targetJson = battleTable.get(target)
        senderJson = battleTable.get(sender)
        if not targetJson or not senderJson:
            printw("target or sender no longer exists")
            return

        dmgAtKey = spellType(attackJson)
        cantrip = isCantrip(attackJson)
        dmgString = ""

        spellcasting = canCast(senderJson)

        if cantrip:
            level = geti(spellcasting, "level", -1)

        lowestLevel = "1000000"
        for levelKey, damage in attackJson["damage"][dmgAtKey].items():
            if int(levelKey) < int(lowestLevel):
                lowestLevel = levelKey
            if int(level) >= int(levelKey):
                dmgString = attackJson["damage"][dmgAtKey][levelKey]
        if dmgString == "":
            dmgString = attackJson["damage"][dmgAtKey][lowestLevel]
            printw("Defaulting cast to lowest level",lowestLevel)

        blockMult = 0
        mod = 0;
        threshold = 0;
        
        dc = attackJson.get("dc")
        advMod = 0
        if dc:
            mod = getMod("saveDc", attackJson, targetJson)
            if cantrip:
                level = 0
            threshold = getMod("spellDc",attackJson,senderJson,int(level))

            if dc.get("dc_success") == "half" or dc.get("success_type") == "half":
                blockMult = 0.5
            advMod = int(targetJson["save_advantage"])
        else:
            mod = getMod("spellHit",attackJson,senderJson)
            threshold = int(targetJson["armor_class"])
            advMod = int(senderJson["advantage"])
            advMod += int(dget(targetJson,"incoming_advantage",0))
        
        #printUse(a)

        damageType = attackJson["damage"]["damage_type"]["index"]
        hurtString = dmgString + "@" + damageType

        advNum = int(a["advantage"]) + advMod

        advantage = ""
        if advNum > 0:
           advantage = "advantage" 
        elif advNum < 0:
           advantage = "disadvantage" 

        landString = "1d20+"+str(mod)

        if advantage:
            landString = landString + "!" + advantage

        save = dc
        if not landFudge:
            landFudge = []
        if not weaponFudge:
            weaponFudge = []
        a.update({"save" : save, "blockMult" : blockMult, "weaponFudge" : [hurtString]+weaponFudge, "landFudge" : [landString]+landFudge, "defense" : threshold, "multiCrit" : ["20"]})
        callDo(a)
    else:
        return False
    return True

def removeDown(a=''):
    for nick, combatant in battleTable.copy().items():
        hp = dget(combatant,"current_hp",None)
        if hp != None:
            hp = int(hp)
            if hp <= 0:
                if not (combatant.get("downable") == "True"):
                    remove({"target": nick})
                else:
                    combatant["current_hp"] = 0
            elif hp > int(combatant["max_hp"]):
                combatant["current_hp"] = combatant["max_hp"]
        else:
            printw("Invalid combatant referenced by removeDown", nick)
            printJson(combatant)

def callRequest(a):
    steps = a["path"]
    result = getJson(steps)
    printJson(getJson(steps))

    directory = ""
    if a.get("directory"):
        directory = a["directory"]
    if a.get("file"):
        for output in a.get("file"):
            if directory:
                with open(directory+"/"+output, 'w') as f:
                    json.dump(result,f,indent=4)       
            else:
                with open(output, 'w') as f:
                    json.dump(result,f,indent=4)       

def callDump(a):
    target = a["target"]

    result = copy.deepcopy(battleTable.get(target))
    pluckKeys = ["current_hp","initiative","disabled","paused","identity","advantage","save_advantage","nick","name","senses","url"]

    for key in pluckKeys:
        result.pop(key,None)

    if a["identity"] == None:
        a["identity"] = result["identity"]

    result["index"] = a["identity"].lower()

    printJson(result)
    directory = ""
    if a.get("directory"):
        directory = a["directory"]
    if a.get("file"):
        for output in a.get("file"):
            if directory:
                with open(directory+"/"+output, 'w') as f:
                    json.dump(result,f,indent=4)       
            else:
                with open(output, 'w') as f:
                    json.dump(result,f,indent=4)       

def remove(a):
    nick = a["target"]
    if battleTable.get(nick):
        myTurn = battleTable.get(nick).get("my_turn")
        nickNext = whoTurnNext()
        battleTable.pop(nick)
        battleOrder.remove(nick)
        groups = battleInfo["groups"]

        for group, members in groups.copy().items():
            if nick in members:
                members.remove(nick)

        for group in list(groups):
            if len(battleInfo["groups"][group]) == 0:
                ddel(battleInfo,["groups",group])

        if myTurn and nickNext and len(battleOrder)>0:
            callJump({"target":nickNext})
    return "removed " + nick

def callAction(a):
    a["do"] = a["do"].title()
    actionKey = a["do"]
    sender = a["sender"]
    senderJson = battleTable[sender]
    actions = senderJson.get("actions")
    specialAbilities = senderJson.get("special_abilities")
    action_result = ''
    runAction = False
    if actionKey.isnumeric():
        runAction = geti(actions,int(actionKey),False)
    else:
        if actions:
            for action in actions:
                if action["name"] == actionKey:
                    runAction = action
        if specialAbilities:
            for special in specialAbilities:
                if special.get("name") == actionKey:
                    runAction = special
    if runAction:
        a["do"] = runAction["name"]
        if a["do"] == "Multiattack":
            for i in range(int(runAction["options"]["choose"])):
                for action in random.choice(runAction["options"]["from"]):
                    a["do"] = action["name"]
                    applyAction(a)
            else:
                printw("This combatant cannot multiattack")
                action_result = 'This combatant cannot use ' + actionKey
        else:
            applyAction(a)
    else:
        return False
    return True

def callSet(a):
    path = a["path"]
    diff = a.get("change")
    command = a["command"]
    target = a["target"]
    targetJson = battleTable[target]

    context = battleTable
    if target:
        if path:
            path = [target]+path
        else:
            path = [target]
    dset(context,path,diff)


def callMod(a):
    path = a["path"]
    diff = a.get("change")
    command = a["command"]
    target = a["target"]
    effect = a["effect"]
    targetJson = battleTable[target]
    context = battleTable

    if effect:
        dget(context,path)
        dset(targetJson,["effects",effect],{"path":path,"diff":diff})

    if target:
        if path:
            path = [target]+path
        else:
            path = [target]
    dmod(context,path,diff)

def callDispell(a):
    command = a["command"]
    target = a["target"]
    effectName = a["effect"]
    targetJson = battleTable[target]
    context = battleTable
    effect = dget(targetJson,["effects",effectName],None)
    if effect != None:
        path = effect["path"]
        diff = effect["diff"]
        dmod(targetJson,path,-int(diff))
        ddel(targetJson,["effects",effectName])

def callList(a):
    path = a["path"]
    diff = a.get("change")
    command = a["command"]
    target = a["target"]
    if target:
        if path:
            path = [target]+path
        else:
            path = [target]
    context = battleTable
    printJson(dget(context,path,"invalid"))

def printJson(json):
    prettyString = pprint.pformat(json, sort_dicts=False)
    printw(prettyString)

def printw(*args):
    out = printToString(*args)
    print(out)
    global command_out
    command_out.append(out)

def say(string):
    printJson(string)

def printToString(*args):
    string = ""
    first = True
    for arg in args:
        space = " "
        if first:
            space = ""
        string = string + space + str(arg)
        first = False
    return string
        

#This is a pretty meta command that simply speeds up functionality
def callAddAuto(a):
    target = a["target"] 
    identity = a["identity"]
    do = a["do"]
    party = a["party"]
    method = a["method"]

    if not method:
        method = "random"

    if do == None:
        do = "0"

    opponent = ""
    if party:
        party = "party" 
        opponent = "enemies"
    else:
        party = "enemies"
        opponent = "party"

    if identity:
        parseAndRun("add -t "+target+" -i "+identity+" -g "+identity+"s "+party+" --append") 
        parseAndRun("put -t "+identity+"s -c 'use -d "+do+" -t "+opponent+"!"+method+"'") 
    else:
        parseAndRun("add -t "+target+" -g "+target+"s "+party+" --append") 
        parseAndRun("put -t "+target+"s -c 'use -d "+do+" -t "+opponent+"!"+method+"'") 

def findAvailableNick(nick):
    nickPair = nick.split("#")
    nickName = geti(nickPair,0,"")
    nickNumber = int(geti(nickPair,1,2))
    findingAvailableNick = True
    while findingAvailableNick:
        findingAvailableNick = False
        for existingNick,existingCombatant in battleTable.items():
            if existingNick == nick:
                nick = nickName + "#" + str(nickNumber)
                nickNumber += 1 
                findingAvailableNick = True
    return nick


def addCreature(a):
    name = a["target"]
    combatant = getJson(["monsters",name])

    nick = a["identity"]
    if nick == "":
        nick = combatant["index"]

    nick = findAvailableNick(nick)
    
    if combatant:
        hitDice = combatant.get("hit_dice")
        hitPoints = combatant.get("hit_points")
        if hitDice:
            hp = roll(hitDice)["roll"]
            combatant["max_hp"] = hp
            combatant["current_hp"] = hp
        elif hitPoints:
            combatant["max_hp"] = hitPoints
            combatant["current_hp"] = hitPoints

        myClass = combatant.get("class")
        if myClass:
            combatant["rest_dice"] = int(combatant["level"])
            
        combatant["disabled"] = False
        combatant["paused"] = False
        combatant["identity"] = nick
        combatant["advantage"] = 0
        combatant["save_advantage"] = 0
        combatant["incoming_advantage"] = 0
    
        combatant["nick"] = nick
        battleTable[nick] = combatant
        a["target"] = nick
        if a.get("group"):
            a["append"] = True
            a["member"] = [nick]
            callGroup(a)
        applyInit(a)

def legacyCreateCharacter(a):
    name = input("Name?")
    monsterCache = cacheTable["monsters"][name]
    monsterCache["index"] = name
    monsterCache["strength"] = int(input("str?"))
    monsterCache["dexterity"] = int(input("dex?"))
    monsterCache["constitution"] = int(input("con?"))
    monsterCache["intelligence"] = int(input("int?"))
    monsterCache["wisdom"] = int(input("wis?"))
    monsterCache["charisma"] = int(input("cha?"))
    monsterCache["special_abilities"] = []
    monsterCache["special_abilities"].append({"spellcasting": {"ability": {"index" : input("caster stat? (eg. int)")}}})
    monsterCache["weapon_proficiencies"] = input("Weapon proficiencies? (eg simple,martial)")
    monsterCache["hit_points"] = int(input("Max Hp?"))
    monsterCache["armor_class"] = int(input("Armor Class?"))
    spellcasting = canCast(monsterCache)
    level = int(input("Level?"))
    spellcasting["level"] = level
    monsterCache["proficiency_bonus"] = crToProf(level)
    
    with open('data.json', 'w') as f:
        json.dump(cacheTable,f)

def showInfo(a):
    if a.get("info") == "all" or (not a.get("info")):
        printJson(battleInfo)
    else:
        printJson(battleInfo[a["info"]])

def callUse(a):
    do = a["do"]

    senderJson = battleTable[a["sender"]]
    arsenalList = senderJson.get("arsenal")
    doables = False

    printUse(a)

    recurSection = ""
    if not a.get("antiRecursion"):
        a["antiRecursion"] = {}
    if arsenalList:
        doables = arsenalList.get(do)
        recurSection = "arsenal"
    if not doables:
        doables = dget(copy.deepcopy(battleInfo),["commands",do])
        recurSection = "battleInfo"

    if doables and not dget(a,["antiRecursion",recurSection,do]):
        for doableRef in doables:
            doable = copy.deepcopy(doableRef)

            a["command"] = None
            a["sender"] = [a["sender"]]
            a["target"] = [a["target"]]
            if a["landFudge"] and doable["landFudge"]:
                a["landFudge"] = a["landFudge"] + doable["landFudge"]
            if a["weaponFudge"] and doable["weaponFudge"]:
                a["weaponFudge"] = a["weaponFudge"] + doable["weaponFudge"]
            dset(a,["antiRecursion",recurSection,do],True)
            a["do"] = None
            argDict = weedNones(a)
            doable.update(argDict)
            parse_command_dict(doable)
        return True

    if callAction(a):
        return True
    if callWeapon(a):
        return True
    if callCast(a):
        return True
    printw("Trying to use/do something that is not a weapon nor a spell nor an action. It also does not exist as a global function nor an arsenal entry for this sender")
    printw(a)


def handleFudgeInput(fudge):
    fudgeNext = ""
    if fudge and ("$" in fudge):
        fudge = fudge.replace("$","")
        override = input("`enter`->"+ fudge +". `skip`->nothing Override?->")

        if override == "skip":
            fudge = ""
        elif len(override) != 0:
            if override == "$":
                fudgeNext = fudge + "$"
            else:
                fudgeNext = override
                fudge = override.replace("$","")
    return [fudge,fudgeNext]


def handleThreshold(a):
    resultDict = {}
    threshold = a["threshold"]
    target = a["target"]
    targetJson = battleTable[target]

    if threshold.isnumeric():
        resultDict = {"threshold":int(threshold),"save":False}
    elif threshold == "ac":
        threshold = targetJson["armor_class"]
        resultDict = {"threshold":int(threshold),"save":True}

    a.update(resultDict)

def callDo(a):
    target = a["target"]
    sender = a["sender"]
    commandStrings = dget(a,"commandString",None)
    targetJson = battleTable.get(target)
    senderJson = battleTable.get(sender)
    threshold = dget(a,"defense")
    landStrings = dget(a,"landFudge")
    hurtStrings = dget(a,"weaponFudge")
    blockMult = dget(a,"blockMult")
    critValues = dget(a,"multiCrit")
    save = bool(a.get("save"))

    if not landStrings:
        landStrings = ["100"]
    if not threshold:
        if target:
            threshold = "ac"
        else:
            threshold = "-100"

    threshold = handleCheckAliases(threshold,senderJson,targetJson)

    if not blockMult:
        blockMult = 0

    if not save and not critValues:
        critValues = ["20"]

    if not critValues:
        critValues = []

    hitCrit = {"roll":0,"critHit":False}
    for landString in landStrings:
        hitCrit = rollFudge(senderJson,targetJson,hitCrit,landString,1,False,critValues,"hit")
    hit = hitCrit["roll"]
    critHit = hitCrit["critHit"] 

    hasDamage = 0
    success = False
    if critHit:
        hasDamage = 1
        success = True
    elif not ((hit >= int(threshold)) == save):
        hasDamage = 1
        success = True
    elif blockMult:
        success = False
        hasDamage = blockMult

    printw("Hit or failed save?", str(success)+".", " Is", hit, ">=",threshold, "Crit?",critHit)

    if hasDamage:
        damage = {"roll":0,"critHit":False} #This may show critHit false but we pass into the critDmg variable below so it's ok.
        for hurtString in hurtStrings:
            damage = rollFudge(senderJson,targetJson,damage,hurtString,hasDamage,critHit,[], "dmg")
        if targetJson:
            applyDamage(targetJson,damage["roll"])
        if commandStrings:
            for commandString in commandStrings:
                commandDict = parse_command_string(commandString,"do",False)
                dset(commandDict,"target", target)
                dset(commandDict,"sender", sender)
                parse_command_dict(commandDict)

def handleHitModAliases(rollString,senderJson,targetJson, isSave=False):
    proficiency = 0
    saveProficiency = 0
    finesseMod = 0
    martialMod = 0
    simpleMod = 0
    spellHit = 0
    Json = {}
    if (senderJson and not isSave) or (targetJson and isSave):
        if isSave:
            if targetJson:
                Json = targetJson
                proficiency = getProf(Json)
                saveProficiencies = geti(classSavesDict,Json.get("class"),[])
                if saveType in saveProficiencies:
                    saveProficiency = proficiency
        else:
            if senderJson:
                Json = senderJson
                proficiency = getProf(Json)
                if "finesse" in rollString:
                    finesseMod = max(statMod(int(Json["strength"])),statMod(int(Json["dexterity"])))
                else:
                    finesseMod = statMod(int(Json["strength"]))

                if "martial" in dget(Json,"weapon_proficiencies",[]):
                    martialMod = proficiency

                if "simple" in dget(Json,"weapon_proficiencies",[]):
                    simpleMod = proficiency

                if "spellhit" in rollString:
                    spellcasting = canCast(Json)
                    spellHit = statMod(Json[expandStatWord(spellcasting["ability"]["index"])]) + getProf(Json)
        
        if not isSave:
            rollString = rollString.replace("normal",str(statMod(int(Json["strength"]))))
            rollString = rollString.replace("finesse",str(finesseMod))

            rollString = rollString.replace("martial",str(martialMod))
            rollString = rollString.replace("simple",str(simpleMod))

    rollString = rollString.replace("any",str(proficiency))
    rollString = rollString.replace("proficiency",str(proficiency))
    rollString = rollString.replace("prof",str(proficiency))

    rollString = rollString.replace("spellhit",str(statMod(int(dget(Json,"charisma",10))+saveProficiency)))
    rollString = rollString.replace("str",str(statMod(int(dget(Json,"strength",10))+saveProficiency)))
    rollString = rollString.replace("dex",str(statMod(int(dget(Json,"dexterity",10))+saveProficiency)))
    rollString = rollString.replace("con",str(statMod(int(dget(Json,"constitution",10))+saveProficiency)))
    rollString = rollString.replace("int",str(statMod(int(dget(Json,"intelligence",10))+saveProficiency)))
    rollString = rollString.replace("wis",str(statMod(int(dget(Json,"wisdom",10))+saveProficiency)))
    rollString = rollString.replace("cha",str(statMod(int(dget(Json,"charisma",10))+saveProficiency)))
    rollString = rollString.replace("spellhit",str(spellHit))
    rollString = rollString.replace(".","1d20")

    return rollString

def handleDmgModAliases(rollString,senderJson):
    if senderJson:
        rollString = rollString.replace("str",str(statMod(int(senderJson["strength"]))))
        rollString = rollString.replace("dex",str(statMod(int(senderJson["dexterity"]))))
        rollString = rollString.replace("con",str(statMod(int(senderJson["constitution"]))))
        rollString = rollString.replace("int",str(statMod(int(senderJson["intelligence"]))))
        rollString = rollString.replace("wis",str(statMod(int(senderJson["wisdom"]))))
        rollString = rollString.replace("cha",str(statMod(int(senderJson["charisma"]))))
        rollString = rollString.replace("normal",str(statMod(int(senderJson["strength"]))))
        proficiency = getProf(senderJson)
        rollString = rollString.replace("any",str(proficiency))
        rollString = rollString.replace("proficiency",str(proficiency))
        rollString = rollString.replace("prof",str(proficiency))
        if "finesse" in rollString:
            rollString = rollString.replace("finesse",str(0))
    else:
        rollString = rollString.replace("str","0")
        rollString = rollString.replace("dex","0")
        rollString = rollString.replace("con","0")
        rollString = rollString.replace("int","0")
        rollString = rollString.replace("wis","0")
        rollString = rollString.replace("cha","0")
        rollString = rollString.replace("normal","0")
        proficiency = 0
        rollString = rollString.replace("any",str(proficiency))
        rollString = rollString.replace("proficiency",str(proficiency))
        rollString = rollString.replace("prof",str(proficiency))
        finesseMod = 0
        if "finesse" in rollString:
            rollString = rollString.replace("finesse",str(0))

    return rollString

def handleCheckAliases(checkString,senderJson,targetJson):
    checkString = str(checkString).lower()
    if targetJson:
        checkString = checkString.replace("ac",str(targetJson["armor_class"]))
    if senderJson and "spelldc" in checkString:
        getProf(senderJson)
        spellcasting = canCast(senderJson)
        threshold = 8 + statMod(senderJson[expandStatWord(spellcasting["ability"]["index"])]) + getProf(senderJson)
        checkString = checkString.replace("spelldc",str(threshold))
    return checkString

def getModAlt(modType, attackJson, combatantJson, additional = 0):
        modSum = 0
        if modType == "actionHit" and attackJson.get("attack_bonus"):
            modSum += attackJson.get("attack_bonus")
        else:
            if modType == "hit" or modType == "dmg":
                finesse = False
                properties = attackJson.get("properties")
                if properties:
                    for x in properties:
                        if x["index"] == "finesse":
                            finesse = True
                if finesse:
                    modSum += max(statMod(int(combatantJson["strength"])),statMod(int(combatantJson["dexterity"])))
                else:
                    modSum += statMod(int(combatantJson["strength"]))

            if modType == "hit":
                if combatantJson.get("weapon_proficiencies"):
                    if attackJson["weapon_category"] in combatantJson["weapon_proficiencies"]:
                        modSum += getProf(combatantJson)

            if modType == "spellHit" or modType == "spellDc":
                modSum += getProf(combatantJson)

            if modType == "saveDc":
                saveType = attackJson["dc"]["dc_type"]["index"]
                modSum += statMod(combatantJson[expandStatWord(saveType)])
                saveProficiencies = geti(classSavesDict,combatantJson.get("class"),[])
                if saveType in saveProficiencies:
                    modSum += getProf(combatantJson)
            if modType == "spellHit" or modType == "spellDc":
                special_abilities = combatantJson.get("special_abilities")
                if special_abilities:
                    spellcasting = canCast(combatantJson)
                    if spellcasting:
                        if modType == "spellHit" or modType == "spellDc":
                            modSum += statMod(combatantJson[expandStatWord(spellcasting["ability"]["index"])])

                        if modType == "spellDc":
                            modSum += 8 
                    else:
                        raise Exception("Attempted to have a non spellcaster cast a spell")
        return modSum

def rollFudge(senderJson, targetJson, priorDict, fudge, successLevelMult=1, critDmg=False, critValues=[],rollType="hit"):
    if fudge:
        fudgePlusNext = handleFudgeInput(fudge)
        fudge = fudgePlusNext[0]
        fudgeNext = fudgePlusNext[1]

        stringMethodType = getStringMethodType(fudge)
        fudgeString = stringMethodType[0]
        if rollType == "hit":
            fudgeString = handleHitModAliases(fudgeString,senderJson,targetJson)
        elif rollType == "dmg":
            fudgeString = handleDmgModAliases(fudgeString,senderJson)

        method = stringMethodType[1]
        damageType = stringMethodType[2]
        affinityMod = 1
        if targetJson:
            affinityMod = getAffinityMod(targetJson,damageType)
        fudgeDict = handleFudge(fudgeString,method,priorDict,affinityMod,successLevelMult,critDmg,critValues,targetJson)
        return rollFudge(senderJson,targetJson,fudgeDict,fudgeNext,successLevelMult,critDmg,critValues,rollType)
    else:
        return priorDict

def handleFudge(fudgeString,method,currentDict,affinityMult=1,successLevelMult=1,critDmg=False,critValues=[],targetJson="only for temp hp"):
    result = 0
    temphp = affinityMult == "temphp"
    if temphp:
        affinityMult = 1
    fudgeCrit = {}
    if fudgeString == 100 or fudgeString == "100":
        fudgeCrit = {"roll":100,"critHit":False}
    else:
        fudgeCrit = roll(fudgeString,critDmg,affinityMult,successLevelMult,critValues)

    fudge = fudgeCrit["roll"]
    critHit = fudgeCrit["critHit"]

    fudgeCrit2 = {}
    fudge2 = "1"
    critHit2 = False
    if method in ["a","advantage","d","disadvantage"]:
        fudgeCrit2 = roll(fudgeString,critDmg,affinityMult,successLevelMult,critValues)
        fudge2 = fudgeCrit2["roll"]
        critHit2 = fudgeCrit2["critHit"]

    currentVal = currentDict["roll"]
    currentCritHit = currentDict["critHit"]
    if temphp:
        result = 0
        if method in ["a","advantage"]:
            result = max(fudge2,fudge)
        elif method in ["d","disadvantage"]:
            result = min(fudge2,fudge)
        else:
            result = fudge

        if targetJson.get("temp_hp"):
            targetJson["temp_hp"] = int(targetJson["temp_hp"]) + int(result)
        else:
            targetJson["temp_hp"] = result
        return currentDict

    if not method:
        method = "mod"
    if method in ["mod","m"]:
        critHit = critHit or currentCritHit
        result = currentVal + fudge
    #These refer to previous summed value
    if method in ["greater","g"]:
        critHit = currentCritHit or critHit
        result = max(currentVal,fudge)
    if method in ["lesser","l"]:
        critHit = currentCritHit and critHit
        result = min(currentVal,fudge)
    #These refer to a best of 2 rolls
    if method in ["advantage","a"]:
        critHit = critHit2 or critHit
        result = max(fudge2,fudge)
    if method in ["disadvantage","d"]:
        fudge2 = roll(fudgeString,critDmg,affinityMult,successLevelMult,critValues)["roll"]
        critHit2 = roll(fudgeString,critDmg,affinityMult,successLevelMult,critValues)["critHit"]
        critHit = critHit2 and critHit
        result = min(fudge2,fudge)
    if method in ["reroll","r"]:
        result = fudge

    return {"roll":result,"critHit":critHit}

def roll(dice_strings,critDmg=False,affinityMod=1,saveMult=1,critValues=[]):
    '''
    # PRECONDITIONS #
    Input: String with dice number, type, and modifier, e.g. 3d20+1

    Example Input: '1d20'
    Another Example Input: '1d4+2'
    Side Effects/State: None

    # POSTCONDITIONS #
    Return: Integer returned, representing the dice roll result
    Side Effects/State: None
    '''
    #diceStrings = dice_strings.split(",")
    total = 0
    critHit = False

    diceStrings = re.split('(\+|\-)',dice_strings)
    if diceStrings[0] != "-":
        diceStrings = ["+"] + diceStrings
    first = True
    for operator, value in zip(diceStrings[::2],diceStrings[1::2]): 
        rolledValue = value
        if "d" in value:
            dsplit = value.split("d")
            dCount = int(dsplit[0])
            dType = int(dsplit[1])

            if critDmg:
                dCount = dCount*2

            for x in range(dCount):
                rolled = math.ceil(dType*random.random())
                if dType == 20 and (str(rolled) in critValues):
                    critHit = True
                total += int(operator + str(rolled))
        else:
            if value:
                total += int(operator + str(value))
        first = False

    total = math.floor(int(total) * affinityMod * float(saveMult))

    message = dice_strings.replace(","," + ")
    if critDmg:
        message = "CRIT! Double dice count for "+message
    if affinityMod != 1:
        message = "AFFINITY! " + str(affinityMod) +"*("+ message +")"
    if saveMult != 1:
        message = "SAVE! " + str(saveMult) +"*("+ message +")"

    printw("roll",message,"=",total)
    
    return {"roll":int(total), "critHit":critHit}

def helpMessage(a):
    for key, value in a["commandDescriptions"].items():
        printw(key, ":", value)
    printw("For more detailed help on a given *commandName* run:\n commandName --help")

def whoTurn():
    for i, nick in enumerate(battleOrder):
        x = battleTable[nick]
        if x.get("my_turn"):
            return battleOrder[i]

    return geti(battleOrder,0,False) 

def whoTurnNext():
    turn = 0 
    for i, nick in enumerate(battleOrder):
        x = battleTable[nick]
        if x.get("my_turn"):
            turn = i
    return geti(battleOrder,(turn+1) % len(battleOrder),False)

def validateCommand(commandDict):
    a = commandDict
    a = handleAllAliases(a)
    has = hasParse(a["command"])
    
    if has.get("target"):
        targets = onlyAlive(a["target"])
        oneTarget = geti(targets,0,False)
        if not oneTarget:
            return False

    if has.get("sender"):
        senders = onlyAlive(a["sender"])
        oneSender = geti(senders,0,False)
        if not oneSender:
            return False
    #Maybe some day add validation here that checks api and cache to see if a["do"] is a spell, action, or weapon that exists. For now I don't see a way to do it that isn't very slow due to calling the api far more than needed.

    return True

def validateCommands(combatantJson):
    commands = dget(combatantJson, ["arsenal","autoDict"])
    if commands:
        for commandDict in commands:
            if validateCommand(commandDict.copy()):
                return True
    return False

def turnTo(nickNext):
    callJump({"target": nickNext})
    callTurn({"target": nickNext},False)

def callTurn(a,directCommand=True):
    if len(battleOrder) != 0:
        nickCurrent = a["target"]
        if directCommand:
            callJump({"target" : nickCurrent})
        if whoTurn() == nickCurrent:
            nickNext = whoTurnNext()

            combatantJson = battleTable[nickCurrent]
            isValidCommand = validateCommands(combatantJson)
            if isValidCommand and ((not combatantJson["paused"]) or directCommand):
                if not combatantJson["disabled"]:
                    runAuto(combatantJson)
                if whoTurn() == nickCurrent:
                    nickNext = whoTurnNext() #In case the next person died
                else:
                    nickNext = whoTurn() #If we died during the action, remove set the next turn to current
                turnTo(nickNext)
            elif directCommand:
                turnTo(nickNext)
            else:
                #"Paused due to no target for auto commands or no commands or you simply marked this creature for pausing"
                printw("Paused --> Needs commands?", not dget(combatantJson,["arsenal","autoDict"]), ". Paused set?",combatantJson["paused"], ". No targets or senders?", (not isValidCommand) and bool(dget(combatantJson,["arsenal","autoDict"])))
        else:
            printw("Bounced an invalid turn attempt trying to callturn on someone who's turn it is not")
    else:
        printw("Hmm, nobodies home to do a turn")

def callJump(a):
    nickCurrent = whoTurn()
    if whoTurn:
        battleTable[nickCurrent]["my_turn"] = False
    battleTable[a["target"]]["my_turn"] = True

def callSkip(a):
    do=0

def callPause(a):
    target = a["target"]
    combatantJson = battleTable[target]
    combatantJson["paused"] = True 
def callResume(a):
    target = a["target"]
    combatantJson = battleTable[target]
    combatantJson["paused"] = False 
def callEnable(a):
    target = a["target"]
    combatantJson = battleTable[target]
    combatantJson["disabled"] = False 
def callDisable(a):
    target = a["target"]
    combatantJson = battleTable[target]
    combatantJson["disabled"] = True

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        printw(self.format_help())
        self.exit(2, '%s: error: %s\n' % (self.prog,message))
    def print_help(self, file=None):
        printw(self.format_help())

def hasParse(command):
    attributeDict = {}
    attributeList = hasDict.get(command)
    if attributeList:
        for attribute in attributeList:
            attributeDict[attribute] = True
    return attributeDict

def hasAttribute(attribute,command):
    if attribute in hasDict.get(command):
        return True
    else:
        return False

def onlyAlive(combatants):
    aliveCombatants = []
    for combatant in combatants:
        if battleTable.get(combatant) or combatant == "?" or combatant == None:
            aliveCombatants.append(combatant)
        elif battleInfo.get("groups").get(combatant):
            aliveCombatants = aliveCombatants + battleInfo.get("groups").get(combatant)
    return aliveCombatants

def handleStar(starString):
    combatantList = []
    parts = starString.split("*")
    for combatant in battleOrder:
        addCombatant = True
        for part in parts:
            if not (part in combatant):
                addCombatant = False
        if addCombatant:
            combatantList.append(combatant)
    return combatantList

def getHps(combatantList,ascending=True):
    hps = [] 
    for combatant in combatantList:
        hps.append([combatant,int(battleTable[combatant]["current_hp"])])
        hps = sorted(hps, key=lambda x: int(x[1]), reverse=(not ascending))
    return hps

def handleAliases(combatantLists,resolve=True,doAll=False):
    result = []
    for combatantListAliased in combatantLists:
        listMethod = combatantListAliased.split("!")
        combatantListAliased = listMethod[0].split(",")
        combatantList = []

        for index,combatant in enumerate(combatantListAliased):
            if combatant.isnumeric():
                comb = geti(battleOrder,int(combatant),False)
                if comb:
                    combatantList.append(comb)
            
            if resolve:
                if combatant in battleInfo["groups"].keys():
                    combatantList = onlyAlive(combatantList + battleInfo["groups"][combatant])
                elif combatant == "all":
                    combatantList = combatantList + battleOrder
                elif combatant == "me":
                    combatantList.append(whoTurn())
                elif combatant == "?":
                    combatantList.append("?")
                elif "*" in combatant:
                    combatantList = combatantList + handleStar(combatant)

            if not combatantList:
                combatantList.append(combatant)

            if resolve:
                #should be no group names in here at this point so let's thin out the non existent names
                combatantList = onlyAlive(combatantList)

        method = geti(listMethod,1,"simultaneous")
        livingCount = len(combatantList)
        if resolve:
            if combatantList:
                if method == "order" or method == "o":
                    result.append(combatantList[0])
                elif method == "random" or method == "r":
                    randomCombatant = combatantList[math.floor(livingCount*random.random())]
                    result.append(randomCombatant)
                elif method == "simultaneous" or method == "s":
                    result = result + combatantList
                elif "hpup" in method or "hu" in method:
                    hps = getHps(combatantList,True)
                    affected = []
                    remainingHp = roll(method.replace("hpup","").replace("hu",""))["roll"]
                    for hpPair in hps:
                        combatantHp = hpPair[1]
                        if combatantHp <= remainingHp:
                            remainingHp = remainingHp - combatantHp
                            affected.append(hpPair[0])
                        else:
                            break;

                    result = result + affected
                elif method == "hpdown" or method == "hd":
                    result = result + combatantList
                else:
                   printw("Invalid method for targetting") 
        else:
            resultString = ""
            for i ,combatant in enumerate(combatantList):
                comma = ","
                if i == 0:
                    comma = ""
                resultString = resultString + comma + combatant 
            resultString = resultString + "!" + method
            result.append(resultString)

        if result and not doAll:
            break

    return result

def handleNumerics(combatantList):
    result = []
    for combatant in combatantList:
        if combatant != None and combatant.isnumeric():
            comb = geti(battleOrder,int(combatant),False)
            if comb:
                result.append(comb)
        else: 
            result.append(combatant)
    return result

def handleAllAliases(toDict,resolve=True):
    mustIterate(toDict,["sender","target","do"])
    command = toDict["command"]
    has = hasParse(command)

    #sender is optional some times
    if (not has.get("no-alias")) and (dget(toDict,"sender",[None]) != [None]):
        toDict["sender"] = handleAliases(toDict["sender"],resolve,True)

    if (not has.get("no-alias")) and (dget(toDict,"target",[None]) != [None]):
        if not toDict.get("target-unresolved"):
            toDict["target-unresolved"] = handleAliases(toDict["target"],False,has.get("target-all"))
            toDict["target"] = handleAliases(toDict["target"],resolve,has.get("target-all"))
        else:
            toDict["target"] = handleAliases(toDict["target-unresolved"],resolve,has.get("target-all"))

    if toDict.get("group") and command != "add":
        toDict["member"] = handleAliases(toDict["member"],resolve,True)

    if has.get("target-single-optional") and resolve:
        if dget(toDict,"target",[None]) == [None]:
            if command == "turn":
                toDict["target"] = [whoTurn()]
            else:
                toDict["target"] = [whoTurnNext()]
        toDict["target"] = handleNumerics(toDict["target"])
        
    return toDict

def runAuto(combatantJson, target=""):
    autoDicts = dget(combatantJson,["arsenal","autoDict"])
    for commandDict in autoDicts:
        if target:
            commandDict["target"] = [target]
        parse_command_dict(commandDict)

def callAuto(a):
    sender = a["sender"]
    target = a["target"]
    senderJson = battleTable[sender]
    runAuto(senderJson,target)

def callPut(a):
    mode = a["mode"]
    combatant = a["target"]
    combatantJson = battleTable.get(combatant)
    context = battleInfo
    startIndex = a["index"]
    if combatantJson:
        context = combatantJson

    path = a["path"]
    if path:
        if combatantJson:
            path = ["arsenal"] + path
        else:
            path = ["commands"] + path
    else:
        if combatantJson:
            path = ["arsenal","autoDict"]
        else:
            path = ["commands","genericCommand"]
            printw("failed to enter a path for command. Placing it in genericCommand")

    commandDicts = processCommandStrings(a,context,path)

    if commandDicts:
        if mode == "mod":
            commandDicts = modInfo(path,commandDicts,context,startIndex)

        for commandDict in commandDicts:
            if combatantJson:
                command = commandDict["command"]
                has = hasParse(command)
                if dget(commandDict,"sender",None) == None:
                    commandDict["sender"] = [combatant]
                if dget(commandDict,"target",None) == None:
                    commandDict["target"] = [combatant]
            if mode == "append" or mode == "set":
                dset(context,path+[index+startIndex],commandDict)

def processCommandStrings(a,context={},path=[]):
    commandDicts = []
    startIndex = geti(a,"index",0)

    for index,commandString in enumerate(a["commandString"]):
        if commandString == "delete":
            dget(context,path[:-1]).pop(path[-1])
            return False

        if (not (a.get("method") in ["append","a"])):
            commandString = getBaseCommand(startIndex+index, commandString, context, path)
            
        argDictTemp = parse_command_string(commandString,a.get("command"),a.get("verify"))
        commandDicts.append(handleAllAliases(argDictTemp,a["resolve"]))
    return commandDicts

def getBaseCommand(index,commandString,context,path):
    baseDicts = dget(context,path)
    resolvedCommandString = resolveCommandAlias(commandString,context,path[:-1])
    if not resolvedCommandString:
        if baseDicts:
            subCommand = baseDicts[index]["command"]
            return subCommand +" "+ commandString
        else:
            printw("No base command found, using do")
            return "do " + commandString
    else:
        return resolvedCommandString

    return commandString

def resolveCommandAlias(commandString,context,path):
    contextCopy = copy.deepcopy(context)
    args = commandString.split(" ")
    command = args[0]
    entryString = " ".join(args[1:])
    resolvedCommand = resolveCommandAliasWorker(command,contextCopy,path)
    if resolvedCommand:
        return resolvedCommand + " " +entryString 
    else:
        return False

def resolveCommandAliasWorker(command,context,path):
    if command in funcDict:
        return command
    comList = dget(context,path+[command])
    comDict = geti(comList, 0, False)
    com = False
    if comDict:
        com = comDict.get("command")
    if com:
        return resolveCommandAliasWorker(com,context,path)
    else:
        return False

def getInfo(path):
    return dget(battleInfo,path)

#add a mode which allows for the use of append_value instead of update so you could bless someone with two different options
def modInfo(path,modDictionaries,context,startPosition=0):
    existingDictionaries = dget(context,path)
    if existingDictionaries:
        for index, modDictionary in enumerate(modDictionaries):
            existingDictionary = geti(existingDictionaries,index+startPosition,False)
            if existingDictionary:
                modDictionary = weedNones(modDictionary)
                existingDictionary.update(modDictionary)
            else:
                dset(context, path+[index+startPosition], modDictionary)
    else:
        dset(context, path, modDictionaries)
    return dget(context,path)

def append_value(dict_obj, key, value):
    if key in dict_obj:
        if not isinstance(dict_obj[key], list):
            dict_obj[key] = [dict_obj[key]]
        dict_obj[key].append(value)
    else:
        dict_obj[key] = value

        
def storeInfo(path,value,append,infoDict):
    global battleInfo
    if append:
        appendTo = dget(infoDict,path)
        if appendTo:
            dset(infoDict, path, appendTo + value)
        else:
            dset(infoDict, path, value)
    else:
        dset(infoDict, path, value)

def callGroup(a):
    members = a["member"] 
    groups = a["group"]
    append = a["append"]
    remove = a.get("remove")
    for group in groups:
        if remove:
            for member in members:
                if member in battleInfo["groups"][group]:
                    battleInfo["groups"][group].remove(member)
                if len(battleInfo["groups"][group]) == 0:
                    callDelete({"path":["groups",group]})
        else:
            storeInfo(["groups",group],list(set(members)),append,battleInfo)

def pathing(steps,dictionary):
    for step in steps:
        if step.isnumeric():
            dictionary = dictionary.get(int(step))
        else:
            dictionary = dictionary.get(step)
    return dictionary

def callDelete(a):
    combatant = dget(a,"target",None)
    combatantJson = battleTable.get(combatant)
    context = battleInfo
    if combatantJson:
        context = combatantJson

    path = a["path"]
    if path:
        if combatantJson:
            path = ["arsenal"] + path
        else:
            path = ["commands"] + path
    else:
        if combatantJson:
            path = ["arsenal","autoDict"]
        else:
            path = ["commands","genericCommand"]
            printw("failed to enter a path for command. Placing it in genericCommand")

    deep = pathing(path[:-1],battleInfo)
    ddel(context,path)

def callShortRest(a):
    combatant = a["target"]
    combatantJson = battleTable[combatant]
    if combatantJson.get("rest_dice"):
        if int(combatantJson["rest_dice"]) > 0 and int(combatantJson["current_hp"]) < int(combatantJson["max_hp"]):
            combatantJson["current_hp"] = int(combatantJson["current_hp"]) + roll(hitDieFromClass(combatantJson["class"])+"+"+str(statMod(int(combatantJson["constitution"]))))["roll"]
            combatantJson["rest_dice"] = int(combatantJson["rest_dice"]) - 1

def callLongRest(a):
    combatant = a["target"]
    combatantJson = battleTable[combatant]
    if combatantJson.get("rest_dice"):
        combatantJson["rest_dice"] = int(combatantJson["level"])
        combatantJson["current_hp"] = combatantJson["max_hp"]

def hitDieFromClass(myClass):
    d6 = ["sorcerer","wizard"]
    d8 = ["artificer","bard","cleric","druid","monk","rogue","warlock"]
    d10 = ["fighter","paladin","ranger"]
    d12 = ["barbarian"]
    dice = "1d8"
    if myClass.lower() in d6:
        dice = "1d6"
    if myClass.lower() in d8:
        dice = "1d8"
    if myClass.lower() in d10:
        dice = "1d10"
    if myClass.lower() in d12:
        dice = "1d12"
    return dice

def dictToCommandString(dictionary):
    commandString = dictionary["command"]
    for key, value in dictionary.items():
        valueString = ""
        if key == "commandString":
            for string in value:
                    valueString = valueString + " '" + string + "'" 
            commandString = commandString +" --"+ key + valueString

        elif key != "command" and key != "has":
            if isinstance(value,list):
                for val in value:
                    valueString = valueString + " " + str(val)
            else:
                if isinstance(value, bool):
                    valueString = ""
                else:
                    valueString = " " + str(value)

            if bool(value) and (not (key == "times" and value == 1)):
                commandString = commandString +" --"+ key + valueString
    return commandString

def populateParserArguments(parser,has,metaHas,verify=True):
    if has.get("fudge"):
        parser.add_argument("--landFudge", "-l", help='A dice string to be used for fudging a hit',nargs='+',default=[])
        parser.add_argument("--weaponFudge", "-w", help='A dice string to be used for fudging damage',nargs='+',default=[])

    if has.get("times"):
        parser.add_argument("--times", "-n", help='How many times to run the command')

    if has.get("sender"):
        parser.add_argument("--sender", "-s", required=(not metaHas.get("optionalSenderAndTarget")) and not has.get("optionalSenderAndTarget") and verify and not has.get("optionalTarget"), help='sender/s for command', nargs='+')

    if has.get("must-do"):
        parser.add_argument("--do", "-d", required=(True and verify), help='What the sender is using on the target', nargs='+')

    if has.get("do"):
        parser.add_argument("--do", "-d", help='What the sender is using on the target', nargs='+')

    if has.get("path"):
        parser.add_argument("--path", "-p", required=(not has.get("optionalPath")) and verify, nargs='+',help='Path for json or api parsing with command. Space seperated')
        if has.get("change"):
            parser.add_argument("--change", "-c", required=True and verify, help='What you would like to set or modify a number by')
            parser.add_argument("--roll", "-r", help='Whether or not the change indicated is a dice change', dest='roll', action='store_true')
            parser.set_defaults(roll=False)

    if has.get("level"):
        parser.add_argument("--level", help='Level to cast a spell at')

    if has.get("target"):
        if (has.get("identity") or has.get("file")):
            parser.add_argument("--target", "-t", required=True and verify, help='Target/s creature types to fetch from the cache the api or a file', nargs='+')
        else:
            parser.add_argument("--target", "-t", required=((not metaHas.get("optionalSenderAndTarget")) and (not has.get("optionalTarget")) and verify and (not has.get("optionalSenderAndTarget"))), help='Target/s for command', nargs='+')

    if has.get("target-single-optional"):
        parser.add_argument("--target", "-t", help='Target for command')

    if has.get("group"):
        req = True and verify
        if has.get("no-alias"):
            req = False
        else:
            parser.add_argument("--member", "-m", help='members to be placed into a group', required=req, nargs='+')
        parser.add_argument("--group", "-g", help='A group which will be reduced to a target list', required=req, nargs='+')

    if has.get("category"):
        parser.add_argument("--category", "-c", choices=['monsters','equipment','spells'], help='A category for content',required=True and verify)

    if has.get("commandString"):
        parser.add_argument("--commandString", "-c", help='A command string to be run', nargs='+',required=True and verify and (not has.get("optionalCommand")))
        parser.add_argument("--resolve", "-r", help='Whether or not to resolve aliases inside command string. party -> guy1 guy2 girl', dest='resolve', action='store_true')
        parser.set_defaults(resolve=False)

    if has.get("arbitraryString"):
        parser.add_argument("--string", "-s", help='A string to run from the very top level with no processing when saved', nargs='+',required=True and verify)

    if has.get("allowIncomplete"):
        parser.add_argument("--verify", "-v", help='Whether or not what is being stored is an incomplete command', dest='verify', action='store_true')

    if has.get("identity"):
        parser.add_argument("--identity", "-i", help='Identities for added monsters', nargs='+')

    if has.get("info"):
        parser.add_argument("--info", "-i", help='Info category to interact with')

    if has.get("index"):
        parser.add_argument("--index", "-i", help='Might be combined with a path',default=0)

    if has.get("advantage"):
        parser.add_argument("--advantage", "-a", choices=["1","0","-1","?"], help='Advantage for attacks', nargs='+')

    if has.get("file"):
        parser.add_argument("--file", "-f", help='The file you would like to interact with', nargs='+')
        parser.add_argument("--directory", "-d", help='The directory path you would like to interact with')
        
    if has.get("mode"):
        parser.add_argument("--mode", "-m", choices=["set","append","mod","?"],help='How does this information fit with the previous existing information?')
        parser.set_defaults(mode="mod")

    if has.get("append"):
        parser.add_argument("--append", "-a", help='Whether this command should replace the existing set or be added on', dest='append', action='store_true')
        parser.set_defaults(append=False)

    if has.get("effect"):
        parser.add_argument("--effect", "-e", help='Name of the effect being applied')

    if has.get("defense"):
        parser.add_argument("--blockMult", "-b", help='How much damage remains when blocked?')
        parser.add_argument("--defense", "-d", help='What the threshold is for blocking. To include level of spell simply do spelldc+3. If it is a third level spell')
        parser.add_argument("--save", help='Is this a save threshold?', dest='save', action='store_true')
        parser.set_defaults(save=False)
        parser.add_argument("--multiCrit", "-m", help='values which constitute a critical', nargs='+')

    if has.get("party"):
        parser.add_argument("--party", "-p", help='Should this be automated as a member of the party instead of as an enemy?', dest='party', action='store_true')
        parser.set_defaults(party=False)

    if has.get("method"):
        parser.add_argument("--method", "-m", help='How to target enemies', choices=["r","s","o","simultaneous","random","order"])

    if has.get("remove"):
        parser.add_argument("--remove", "-r", help='Whether this command should replace the existing set or be added on', dest='remove', action='store_true')
        parser.set_defaults(remove=False)

    if has.get("dice"):
        parser.add_argument("--dice", "-d", help='A dice string to be used',required=True and verify, nargs='+')

funcDict = {
"do" : callDo,
"use" : callUse,
"action" : callAction,
"weapon" : callWeapon,
"cast" : callCast,
"remove" : remove,
"request" : callRequest,
"set" : callSet,
"mod" : callMod,
"dispell" : callDispell,
"list" : callList,
"add" : addCreature,
"init" : applyInit,
"load" : callLoad,
"dump" : callDump,
"help" : helpMessage,
"turn" : callTurn,
"put" : callPut,
"group" : callGroup,
"info" : showInfo,
"roll" : rollString,
"shortrest" : callShortRest,
"longrest" : callLongRest,
"jump" : callJump,
"skip" : callSkip,
"callAuto" : callAuto,
"pause" : callPause,
"resume" : callResume,
"enable" : callEnable,
"disable" : callDisable,
"save" : "",
"exit" : "",
"abort" : "",
"addAuto": callAddAuto,
"delete": callDelete,
}

senderList = ["sender","target","advantage","times","fudge","must-do"]
storeList = ["path", "commandString", "mode", "allowIncomplete"]
hasDict = {
"action": senderList,
"weapon": senderList,
"cast": senderList + ["level"],
"use": senderList + ["level","optionalTarget"],
"request": ["path","file"],
"dump": ["file","identity","target"],
"mod": ["path", "target", "change", "times", "target-all","sort","effect"],
"set": ["path", "target", "change", "target-all","sort","effect"],
"dispell": ["target", "target-all","sort","effect"],
"list": ["path", "target", "target-all", "optionalPath"],
"store": storeList,
"doable": storeList,
"arsenal": storeList + ["target","target-all","index"],
"init": ["target", "sort", "target-all"],
"remove": ["target", "target-all"],
"put": ["target", "commandString", "mode", "target-all", "optionalSenderAndTarget","allowIncomplete","index","path","optionalPath"],
"add": ["target", "identity", "sort", "times", "group", "append", "no-alias", "target-all"],
"longrest": ["target", "times", "target-all"],
"shortrest": ["target", "times", "target-all"],
"callAuto": ["target","times", "target-all","sender","optionalTarget"],
"enable": ["target", "target-all"],
"disable": ["target", "target-all"],
"pause": ["target", "target-all"],
"resume": ["target", "target-all"],
"load": ["file", "category"],
"roll": ["times", "dice"],
"turn": ["times", "target-single-optional"],
"group": ["group", "append","remove"],
"info": ["info"],
"jump": ["target-single-optional"],
"addAuto": ["target", "identity", "sort", "times", "no-alias", "target-all","do","party","method"],
"delete": ["target", "optionalTarget","path","optionalPath"],
"do": ["target", "fudge", "defense","sender","optionalSenderAndTarget","commandString","optionalCommand"],
}

def parseOnly(command_string_to_parse,metaCommand="",verify=True):
    args = command_string_to_parse.split(" ")
    command = args[0]

    entryString = ""
    desc = "Dnd DM Assistant"
    if "-" in command and not verify:
        command = ""
        entryString = command_string_to_parse
    else:
        entryString = " ".join(args[1:])
    desc = geti(command_descriptions_dict,command,'Dnd DM Assistant')

    has = hasParse(command)
    metaHas = hasParse(metaCommand)
    parser = ArgumentParser(
            prog=command,
            description=desc,
            formatter_class=argparse.RawTextHelpFormatter
            )
    populateParserArguments(parser,has,metaHas,verify)
    entries = shlex.split(entryString)
    #parameters
    a = parser.parse_args(entries)
    argDictMain = vars(a)
    argDictMain["command"] = command

    return argDictMain

def replaceWithInput(value,key):
    replacing = True
    result = value
    while replacing:
        if "?" in result:
            result = result.replace("?",input("What is the "+str(key)+"?"),1)
        else:
            replacing = False
    return result

def parseQuestions(a):
    dictionary = a
    for key, value in dictionary.items():
        if key != "commandString":
            if isinstance(value,list):
                dictionary[key] = []
                for val in value:
                    result = replaceWithInput(val,key)
                    dictionary[key].append(result)
            elif value and (not isinstance(value, bool)):
                result = replaceWithInput(value,key)
                dictionary[key] = result

def parse_command_string(command_string_to_parse,metaCommand="",verify=True):
    args = command_string_to_parse.split(" ")
    command = args[0]
    argDictMain = {} 

    if not(command in funcDict):
        commandDict = battleInfo["commands"].get(command)
        if commandDict:
            if len(args) > 1:
                resolvedCommand = resolveCommandAlias(command_string_to_parse,battleInfo,["commands"])
                if resolvedCommand:
                    if len(commandDict) == 1:
                        aliasDict = parseOnly(resolvedCommand,metaCommand,False)
                        aliasDict = weedNones(aliasDict)
                        copyDict = copy.deepcopy(commandDict[0])
                        copyDict.update(aliasDict)
                        argDictMain = copyDict
                    else:
                        printw("Can't fill alias arguments for aliases that map to multiple commands")
                else:
                    printw("Here would be some arbitrary command handling that does it's best to get args without command context", command_string_to_parse)
            else:
                argDictMain = copy.deepcopy(commandDict[0])
        else:
            printw("Invalid command. None specified or not an alias nor built in command", commandDict, command)
    else:
        argDictMain = parseOnly(command_string_to_parse,metaCommand,verify)

    if "?" in command_string_to_parse:
        printw("Evaluating manual input for:\n"+command_string_to_parse)
        parseQuestions(argDictMain)

    return argDictMain

def parseWrapper(command_string_to_run):
    global command_out
    command_out = []
    result = parseAndRun(command_string_to_run)
    getState()
    return result

def parseAndRun(command_string_to_run):
    command_string_to_run = command_string_to_run.replace("\"-","\" -")#Ugh arg parse can't handle: auto -t guy -c "-t guy"
    command_string_to_run = command_string_to_run.replace("\'-","\' -")#Ugh arg parse can't handle: auto -t guy -c '-t guy'
    if command_string_to_run == "---":
        return "No Command"
    else:
        return parse_command_dict(parse_command_string(command_string_to_run))

def mustIterate(a,keys):
    for key in keys:
        val = dget(a,key,None)
        if val == None:
            a[key] = [None]
        elif not isinstance(val, list):
            a[key] = [val]

def parse_command_dict(argDictToParse):
    argDictMain = copy.deepcopy(argDictToParse)
    command = argDictMain["command"]
    has = hasParse(command)

    command_result = ''

    times = argDictMain.get("times")
    if not times:
        times = "1";

    mustIterate(argDictMain,["sender","target","do"])

    if command == "help":
        argDictMain["commandDescriptions"] = command_descriptions_dict

    if argDictMain.get("roll"):
        argDictMain["change"] = roll(argDictMain["change"])["roll"]

    if command == "save":
        saveBattle()
        return True
        
    if command == "exit":
        saveBattle()
        return "EXIT"

    if command == "abort":
        return "EXIT"

    for time in range(int(times)):
        for do in argDictMain["do"]:
            argDictCopy = handleAllAliases(copy.deepcopy(argDictMain))
            argDictSingle = copy.deepcopy(argDictCopy)
            argDictSingle["do"] = do
            for sender in argDictCopy["sender"]:
                argDictSingle["sender"] = sender
                for number,target in enumerate(argDictCopy["target"]):
                    argDictSingle["target"] = target
                    if has.get("identity"):
                        argDictSingle["identity"] = geti(argDictCopy["identity"],number,target)
                    if has.get("advantage"):
                        argDictSingle["advantage"] = geti(argDictCopy["advantage"],number,0)

                    command_result += str(funcDict[command](copy.deepcopy(argDictSingle)))
                    removeDown()

    if has.get("sort"):
        setBattleOrder()

    return command_result

def run_assistant():
    result = "" 
    error_count = 0 # Detect error spam
    setBattleOrder()
    getState()
    while not("EXIT" == result):
        try:
            command_input_string = input("Command?")
            result = parseWrapper(command_input_string)
        except SystemExit:
            printw("")#This catches argParses attempts to exit.

        except Exception:
            printw("ERROR, enter the 'exit' command to exit.")
            traceback.print_exc()

            # Error Spam Prevention #
            error_count = error_count + 1
            if error_count >= 10:
                error_spam_prompt = input('Error count has reached 10. \n Program will now exit. \n But you can enter "continue" if you still \n want to keep this up? ->')
                if error_spam_prompt.lower() != 'continue':
                    result = "EXIT" # Brute force error spam prevention
                    sys.exit('Exit due to error Spam')
                else:
                    error_count = 0

if __name__ == "__main__":
    run_assistant()
