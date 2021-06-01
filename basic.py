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

def geti(list, index, default_value):
    try:
        return list[index]
        
    except:
        return default_value

def dd_rec():
    return defaultdict(dd_rec)

def defaultify(d):
    if not isinstance(d, dict):
        return d
    return defaultdict(dd_rec, {k: defaultify(v) for k, v in d.items()})

def dictify(d):
    if isinstance(d, defaultdict):
        d = {k: dictify(v) for k, v in d.items()}
    return d
                
def set_nested_item(dataDict, mapList, val):
    """Set item in nested dictionary"""
    reduce(getitem, mapList[:-1], dataDict)[mapList[-1]] = val
    return dataDict
                
def load(a):
    with open(a["file"]) as f:
            return json.load(f)

def loadCreature(a):
    creatureJson = load(a)
    global cacheTable
    cacheTable["monsters"][creatureJson["index"]] = creatureJson
 
cacheTable = defaultify(load({"file":"data.json"}))
battleTable = defaultify(load({"file":"battle.json"}))
global battleInfo
battleInfo = defaultify(load({"file":"battle_info.json"}))
battleOrder = []

def getJsonFromApi(steps,save=True):
        api_base = "https://www.dnd5eapi.co/api/"
        print(steps)
        for x in steps:
            api_base += x + "/"
        print(api_base)
        package = requests.get(api_base)
        response = package.json()
        if response.get("error"):
            print("Content not in api nor cache", steps)
            return False

        if save:
            with open('data.json') as f:
                global cacheTable
                cacheTable = set_nested_item(cacheTable,steps,response)
            
            with open('data.json', 'w') as f:
                json.dump(dictify(cacheTable),f)

        return response

def saveBattle():
        with open('battle.json', 'w') as f:
            json.dump(dictify(battleTable),f)       
        with open('battle_info.json', 'w') as f:
            json.dump(dictify(battleInfo),f)

def printJson(json):
    pprint.pprint(dictify(json), sort_dicts=False)
                
def getJson(steps):
        global cacheTable
        cache = cacheTable
        
        for i,x in enumerate(steps):
                cache = cache[x]
                if cache == {} and i > 0:
                        print("Not cached, trying api")
                        return getJsonFromApi(steps)
        return cache.copy()
        
def getState():
        print("initiative name type hp/max_hp")
        state_result = []
        for i, nick in enumerate(battleOrder):
            x = battleTable[nick]
            turn = ""
            if x.get("my_turn"):
                turn = "<-----------------| My Turn"
            print(x["initiative"],nick,x["index"],str(x["current_hp"])+"/"+str(x["max_hp"])+turn)
            state_result.append(str(x["initiative"]) + ' ' + nick + ' ' + str(x["index"]) + ' ' + str(x["current_hp"]) + "/" + str(x["max_hp"]))
        return state_result

def rolld20(advantage = 0):
    d20 = 0
    if advantage == 0:
        d20 = roll("1d20")
    elif advantage == 1:
        d20 = max(roll("1d20"),roll("1d20"))
    elif advantage == -1:
        d20 = min(roll("1d20"),roll("1d20"))
    else:
        print("invalid advantage type", advantage)
        action_result += '\n' + advantage + ' is an invalid advantage type.'
        d20 = roll("1d20")
    return d20

def roll(dice_string):
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
    print(dice_string)
    dsplit = dice_string.split("d")
    usesDice = len(dsplit)>1
    sum = 0
    diceMod = 0
    if usesDice:
        remaining = dsplit[1].split("+")
        if "+" in dice_string:
            diceMod = float(remaining[1])
        diceCount = int(dsplit[0])
        diceType = float(remaining[0])
        for x in range(diceCount):
            sum += math.ceil(diceType*random.random())
    else:
        sum = int(dice_string)
    
    return int(sum + diceMod)

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
        print("Hmm is a monster really this high level? Proficiency issue")
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
    cr = combatant.get("challenge_rating")
    if proficiency:
        return proficiency
    elif cr:
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

def applyDamage(targetJson,damage,dmgType):
    immunities = targetJson.get("damage_immunities")
    vulnerabilities = targetJson.get("damage_vulnerabilities")
    resistances = targetJson.get("damage_resistances")

    damageDealt = damage
    damageType = dmgType["index"]
    searching = True
    if immunities and searching:
        for method in immunities:
            if method == damageType:
                damageDealt = 0
                searching = False
    if vulnerabilities and searching:
        for method in vulnerabilities:
            if method == damageType:
                damageDealt *= 2 
                searching = False
    if resistances and searching:
        for method in resistances:
            if method == damageType:
                damageDealt *= 0.5

    targetJson["current_hp"] -= math.floor(damageDealt)

        
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
                modSum += statMod(combatantJson[expandStatWord(attackJson["dc"]["dc_type"]["index"])])

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

def applyAction(a):
    actionKey = a["do"]
    sender = a["sender"]
    target = a["target"]
    advantage = a["advantage"]
    senderJson = battleTable[sender]
    targetJson = battleTable[target]
    actions = senderJson.get("actions")

    action = False
    action_result = ''
    for act in actions:
        if act["name"] == actionKey:
            action = act
    if action:
        mod = getMod("actionHit",action,senderJson)
        threshold = targetJson["armor_class"]
        
        if checkHit(mod,threshold,advantage):
            for damage in action["damage"]:         
                if damage.get("choose"):
                    for actions in range(int(damage["choose"])):
                        chosenAction = random.choice(damage["from"])
                        applyDamage(targetJson,roll(chosenAction["damage_dice"]),chosenAction["damage_type"])
                else:   
                    applyDamage(targetJson,roll(damage["damage_dice"]),damage["damage_type"])
    else:
        print('Invalid action for this combatant')
        action_result = 'Invalid action for this combatant'

    action_result = '' # This will be returned at the end
    return action_result

def command_parse(input_command_string):
    if input_command_string == "vomit":
        print ("ewwwww")
        
def applyInit(participant):
    who = participant["target"]
    combatant = geti(battleTable,who,False)
    if combatant:
        combatant["initiative"] = statMod(combatant["dexterity"]) + roll("1d20")
    else:
        print("I'm sorry I couldn't find that combatant to apply init to.")

def setBattleOrder():
    initiativeOrder = sorted(battleTable.items(), key=lambda x: x[1]["initiative"], reverse=True)
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

def callWeapon(a):
    attackPath = a["do"].lower()
    sender = a["sender"]
    target = a["target"]
    advantage = a["advantage"]
    attackJson = getJson(["equipment",attackPath])
    targetJson = battleTable[target]
    senderJson = battleTable[sender]
    if attackJson:
        hit = rolld20("1d20",advantage)
        mod = getMod("hit",attackJson,senderJson)
        threshold = targetJson["armor_class"]

        if checkHit(mod,threshold,advantage):
            hurt = roll(attackJson["damage"]["damage_dice"]+"+"+str(getMod("dmg",attackJson,senderJson)))
            applyDamage(targetJson,hurt,attackJson["damage"]["damage_type"])

def checkHit(mod,threshold,advantage=0,save=False):
    d20 = rolld20(advantage)
    success = not (mod + d20 > threshold and save)
    print("Hit?", success)
    return success

def callCast(a):
    attackPath = a["do"].lower()
    sender = a["sender"]
    target = a["target"]
    level = a["level"]
    advantage = a["advantage"]
    attackJson = getJson(["spells",attackPath])
    targetJson = battleTable.get(target)
    senderJson = battleTable.get(sender)
    if not targetJson or not senderJson:
        print("target or sender no longer exists")
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
        print("Defaulting cast to lowest level",lowestLevel)

    if attackJson:
        saveMult = 0
        mod = 0;
        threshold = 0;
        
        dc = attackJson.get("dc")
        if dc:
            mod = getMod("saveDc", attackJson, targetJson)
            if cantrip:
                level = 0
            threshold = getMod("spellDc",attackJson,senderJson,int(level))

            if dc["dc_success"] == "half":
                saveMult = 0.5
        else:
            mod = getMod("spellHit",attackJson,senderJson)
            threshold = targetJson["armor_class"]

        if checkHit(mod,threshold,advantage,dc):
            applyDamage(targetJson,roll(dmgString),attackJson["damage"]["damage_type"])
        elif saveMult != 0:
            applyDamage(targetJson,saveMult*roll(dmgString),attackJson["damage"]["damage_type"])

def removeDown(a=''):
    for nick, combatant in battleTable.copy().items():
        if combatant["current_hp"] <= 0:
            remove({"target": nick})

def callRequest(a):
    steps = a["path"]
    print(steps)
    pprint.pprint(dictify(getJsonFromApi(steps,False)), sort_dicts=False)

def remove(a):
    nick = a["target"]
    if battleTable.get(nick)["my_turn"]:
        callTurn({})
    battleTable.pop(nick)
    battleOrder.remove(nick)
    return "removed " + nick

def callAction(a):
    a["do"] = a["do"].title()
    actionKey = a["do"]
    sender = a["sender"]
    senderJson = battleTable[sender]
    actions = senderJson.get("actions")
    action_result = ''
    if actions:
        if actionKey == "Multiattack":
            canMultiAttack = False
            multiAction = {}
            for act in actions:
                if act["name"] == actionKey:
                    multiAction = act
                    canMultiAttack = True
            if canMultiAttack:
                for i in range(int(multiAction["options"]["choose"])):
                    for action in random.choice(multiAction["options"]["from"]):
                        a["do"] = action["name"]
                        applyAction(a)
            else:
                print("This combatant cannot multiattack")
                action_result = 'This combatant cannot use ' + actionKey
        else:
            applyAction(a)
    return action_result

def followPath(a):
    steps = a["path"]
    diff = a.get("change")
    command = a["command"]
    target = a["target"]
    battle = battleTable
    
    finalStep = False
    if steps:
        finalStep = geti(steps,len(steps)-1,False)

    if not finalStep:
        finalStep = target
    else:
        battle = battle[target]
        for i,key in enumerate(steps):
            if i < len(steps)-1:
                if key.isnumeric():
                    battle = battle[int(key)]
                else:
                    battle = battle[key]

    if finalStep.isnumeric():
        finalStep = int(finalStep)

    if command == "mod":
        battle[finalStep] += int(diff)
    elif command == "set":
        battle[finalStep] = int(diff)
    elif command == "list":
        pprint.pprint(dictify(battle[finalStep]), sort_dicts=False)
    elif command == "listkeys":
        string = ""
        if isinstance(battle[finalStep],list):
            print("Can't list the keys of a list. Try `list` instead of `listkeys`")
        else:
            for key, val in battle[finalStep].items():
                string += key + ","
            string[:-1]
            print(string)

def addCreature(a):
    name = a["target"]
    combatant = getJson(["monsters",name])

    nick = a["identity"]
    if nick == "":
        nick = combatant["index"]

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
    
    if combatant:
        hitDice = combatant.get("hit_dice")
        hitPoints = combatant.get("hit_points")
        if hitDice:
            hp = roll(hitDice)
            combatant["max_hp"] = hp
            combatant["current_hp"] = hp
            
        elif hitPoints:
            combatant["max_hp"] = hitPoints
            combatant["current_hp"] = hitPoints
    
        battleTable[nick] = combatant
        applyInit({"target" : nick})

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
    monsterCache["max_hp"] = int(input("Max Hp?"))
    monsterCache["current_hp"] = int(monsterCache["max_hp"])
    monsterCache["armor_class"] = int(input("Armor Class?"))
    spellcasting = canCast(monsterCache)
    level = int(input("Level?"))
    spellcasting["level"] = level
    monsterCache["proficiency_bonus"] = crToProf(level)
    
    with open('data.json', 'w') as f:
        json.dump(dictify(cacheTable),f)

def populateParserArguments(command,parser,has):
    if has.get("times"):
        parser.add_argument("--times", "-n", help='How many times to run the command',type=int, default=1)

    if has.get("sender"):
        parser.add_argument("--sender", "-s", required=True, help='sender/s for command', nargs='+')
        parser.add_argument("--do", "-d", required=True, help='What the sender is using on the target')

    if has.get("path"):
        parser.add_argument("--path", "-p", nargs='+',help='Path for json or api parsing with command. Space seperated')
        if has.get("change"):
            parser.add_argument("--change", "-c", required=True, help='What you would like to set or modify a number by')

    if has.get("level"):
        parser.add_argument("--level", "-l", type=int, help='Level to cast a spell at')

    if has.get("target"):
        if has.get("identity") or has.get("file"):
            parser.add_argument("--target", "-t", required=True, help='Target/s creature types to fetch from the cache the api or a file', nargs='+')
        else:
            parser.add_argument("--target", "-t", required=True, help='Target/s for command', nargs='+')

    if has.get("command"):
        parser.add_argument("--command", "-c", help='A command to be run')

    if has.get("identity"):
        parser.add_argument("--identity", "-i", help='Identities for added monsters', nargs='+')

    if has.get("advantage"):
        parser.add_argument("--advantage", "-a", type=int, help='Advantage for attacks', nargs='+')

    if has.get("file"):
        parser.add_argument("--file", "-f", help='The file you would like to interact with')

def helpMessage(a):
    for key, value in a["commandDescriptions"].items():
        print(key, ":", value)
    print("For more detailed help on a given *commandName* run:\n commandName --help")

def callAuto(a):
    target = a["target"]
    targetJson = battleTable[target]
    command = a["command"]
    targetJson["autoCommand"] = command

def callTurn(a):
    foundActive = -1
    for i, nick in enumerate(battleOrder):
        x = battleTable[nick]
        if x["my_turn"]:
            foundActive = i

    if battleOrder[foundActive]:
        nickCurrent = battleOrder[foundActive]
        battleTable[nickCurrent]["my_turn"] = False
        if battleTable[nickCurrent].get("autoCommand"):
            parse_command(battleTable[nickCurrent]["autoCommand"])

    nickNext = battleOrder[(foundActive+1) % len(battleOrder)]
    battleTable[nickNext]["my_turn"] = True
    if battleTable[nickNext].get("autoCommand"):
        callTurn({})

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(self.format_help())
        self.exit(2, '%s: error: %s\n' % (self.prog,message))
    def print_help(self, file=None):
        print(self.format_help())

def parse_command(command_string_to_parse):
    args = command_string_to_parse.split(" ")
    command = args[0]

    command_descriptions_dict = {
    "action" : 'Do a generic action. Like:\n\taction --do Multiattack --sender sahuagin#2 --target druid#3 --times 1 --advantage 1\n',
    "weapon" : 'Use a weapon. Like:\n\t weapon --do greatsword --sender sahuagin#2 --target druid#3 --times 3 --advantage -1\n',
    "cast" : 'Cast a spell. Like:\n\t cast --sender druid#3 --target sahuagin#2 --times 2 --do fire-bolt --level 4 --advantage 0\n',
    "remove" : 'Remove an item. Like:\n\t remove --target sahuagin#2\n',
    "request" : 'Make a request. Like:\n\t request --path monsters sahuagin\n',
    "set" : 'Set some aspect of the character or other item. Like:\n\t set --target sahuagin# --path initiative --change 18\n',
    "mod" : 'Modify a stat on a creature. Like:\n\t mod --target sahuagin#2 --path initiative --change -5\n',
    "list" : 'List the features of a creature. Like:\n\t list --target sahuagin#2 --path actions\n',
    "listkeys" : 'List the keys for an item. Like:\n\t listkeys --target sahuagin#2 --path actions\n',
    "add" : 'Add a creature. Like:\n\t add --target sahuagin --times 2 --identity Aqua-Soldier\n',
    "init" : 'Roll for initiative. Like:\n\t initiative --target sahuagin#2\n',
    "initiative" : 'Roll for initiative. Like:\n\t initiative --target sahuagin#2\n',
    "load" : 'Load a creature by file name. Like:\n\t load --file new_creature.json\n',
    "help" : 'Display this message. Like:\n\t help\n',
    "turn" : 'Increments turn. Like:\n\t help\n',
    "auto" : 'Set an automated command. Like:\n\t auto --target sahuagin --command "action --target goblin --sender sahuagin --do multiattack"\n',
    }

    funcDict = {
    "action" : callAction,
    "weapon" : callWeapon,
    "cast" : callCast,
    "remove" : remove,
    "request" : callRequest,
    "set" : followPath,
    "mod" : followPath,
    "list" : followPath,
    "listkeys" : followPath,
    "add" : addCreature,
    "init" : applyInit,
    "initiative" : applyInit,
    "load" : loadCreature,
    "help" : helpMessage,
    "turn" : callTurn,
    "auto" : callAuto,
    }

    has = {
    "sender" : ["action","weapon","cast"],
    "path" : ["request","mod","set","list","listkeys"],
    "target" : ["init","initiative","remove","mod","set","list","listkeys","add","auto"],
    "change" : ["mod","set"],
    "level" : ["cast"],
    "identity" : ["add"],
    "advantage" : [],
    "sort" : ["add","init","initiative"],
    "file" : ["load"],
    "times" : ["mod", "add"],
    "command" : ["auto"],
    }

    has["target"] = has["target"] + has["sender"]
    has["advantage"] = has["advantage"] + has["sender"]
    has["times"] = has["times"] + has["sender"]
    
    parser = ArgumentParser(
            prog=command,
            description=geti(command_descriptions_dict,command,'Dnd DM Assistant Command Updates Game State'),
            formatter_class=argparse.RawTextHelpFormatter
            )


    for key, hasList in has.items():
        if hasList.count(command) > 0:
            has[key] = True
        else:
            has[key] = False

    populateParserArguments(command,parser,has)
    entryString = " ".join(args[1:])
    entries = shlex.split(entryString)
    #parameters
    a = parser.parse_args(entries)

    command_result = ''

    times = 1;

    if has["times"]:
        times = a.times

    if not has["sender"]:
        a.sender = ["none"]

    if not has["target"]:
        a.target = ["none"]

    if a.target[0] == "all":
        a.target = []
        for nick, combatant in battleTable.items():
            a.target.append(nick)

    if command == "help":
        a.commandDescriptions = command_descriptions_dict

    argDictMain = vars(a)
    argDictMain["command"] = command
    argDictCopy = argDictMain.copy()

    if command == "save":
        saveBattle()
        return True
        
    if command == "exit":
        saveBattle()
        return "EXIT"

    if command == "abort":
        return "EXIT"

    for time in range(times):
        for sender in argDictMain["sender"]:
            argDictCopy["sender"] = sender
            for number,target in enumerate(argDictMain["target"]):
                argDictCopy["target"] = target

                if has["identity"]:
                    argDictCopy["identity"] = geti(argDictMain["identity"],number,argDictCopy["target"])
                if has["advantage"]:
                    argDictCopy["advantage"] = geti(argDictMain["advantage"],number,0)

                if command in funcDict:
                    if battleTable.get(target) or not has["target"] or command == "add" or command == "load":
                        command_result += str(funcDict[command](argDictCopy))
                    else:
                        command_result += "ignored an invalid target"
                        print('ignored an invalid target')
                else:
                    print('incorrect command')
                    command_result += 'incorrect command was entered. Try again?'
    if has["sort"]:
        setBattleOrder()

    return command_result

def run_assistant():
    result = ""
    error_count = 0 # Detect error spam
    setBattleOrder()
    while result != "EXIT":
        try:
            removeDown()
            getState()
            command_input_string = input("Command?")
            result = parse_command(command_input_string)
        except SystemExit:
            print("")#This catches argParses attempts to exit.

        except Exception:
            print("oneechan makes awkward-sounding noises at you, enter the 'exit' command to exit.")
            traceback.print_exc()
            result = ""

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
